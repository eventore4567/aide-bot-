from __future__ import annotations

import asyncio
import time
from typing import Any

import aiosqlite

from aidebot.app_db import AideBotDatabase as BaseAideBotDatabase
from aidebot.transaction_guard import register_connection_lock, unregister_connection_lock


class IntegrityDatabase(BaseAideBotDatabase):
    """Production database boundary for workflows that must stay atomic."""

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.transaction_lock = asyncio.Lock()

    async def connect(self) -> None:
        await super().connect()
        register_connection_lock(self._db(), self.transaction_lock)

    async def close(self) -> None:
        if self.conn is not None:
            unregister_connection_lock(self.conn)
        await super().close()

    async def create_request_guarded(self, **values: Any):
        async with self.transaction_lock:
            return await super().create_request_guarded(**values)

    async def advance_request(self, request_id: int):
        async with self.transaction_lock:
            return await super().advance_request(request_id)

    async def complete_request_once(self, request_id: int):
        async with self.transaction_lock:
            return await super().complete_request_once(request_id)

    async def transition_payment(self, request_id: int, target: str):
        async with self.transaction_lock:
            return await super().transition_payment(request_id, target)

    async def consume_invite_credit(self, guild_id: int, user_id: int) -> bool:
        """Consume at most one invite credit with rollback-safe serialization."""
        async with self.transaction_lock:
            db = self._db()
            await db.execute("BEGIN IMMEDIATE")
            try:
                cur = await db.execute(
                    "SELECT credits FROM invite_credits WHERE guild_id=? AND user_id=?",
                    (guild_id, user_id),
                )
                row = await cur.fetchone()
                if not row or int(row["credits"]) <= 0:
                    await db.rollback()
                    return False
                changed = await db.execute(
                    """UPDATE invite_credits
                       SET credits=credits-1
                       WHERE guild_id=? AND user_id=? AND credits>0""",
                    (guild_id, user_id),
                )
                if changed.rowcount != 1:
                    await db.rollback()
                    return False
                await db.commit()
                return True
            except Exception:
                await db.rollback()
                raise

    async def create_mentorship(self, guild_id: int, student_id: int, topic: str) -> int | None:
        """Create at most one open/active mentorship per student and guild."""
        async with self.transaction_lock:
            db = self._db()
            await db.execute("BEGIN IMMEDIATE")
            try:
                cur = await db.execute(
                    """SELECT id FROM mentorships
                       WHERE guild_id=? AND student_id=? AND status IN ('open','active')
                       ORDER BY id DESC LIMIT 1""",
                    (guild_id, student_id),
                )
                if await cur.fetchone():
                    await db.rollback()
                    return None
                created = await db.execute(
                    "INSERT INTO mentorships(guild_id,student_id,topic,created_at) VALUES (?,?,?,?)",
                    (guild_id, student_id, topic, int(time.time())),
                )
                await db.commit()
                return int(created.lastrowid)
            except Exception:
                await db.rollback()
                raise

    async def add_review(
        self,
        guild_id: int,
        request_id: int,
        author_id: int,
        target_id: int,
        rating: int,
        comment: str,
    ) -> bool:
        """Create one review and update aggregate rating counters atomically.

        The request itself is revalidated inside the transaction so a caller
        cannot rate the wrong trainer, another member's request, or an active
        request. Duplicate reviews remain rejected by the database unique key.
        """
        if rating < 1 or rating > 5:
            return False

        async with self.transaction_lock:
            db = self._db()
            await db.execute("BEGIN IMMEDIATE")
            try:
                cur = await db.execute(
                    """SELECT user_id,trainer_id,status
                       FROM requests
                       WHERE id=? AND guild_id=?""",
                    (request_id, guild_id),
                )
                request = await cur.fetchone()
                if (
                    request is None
                    or int(request["user_id"]) != author_id
                    or request["trainer_id"] is None
                    or int(request["trainer_id"]) != target_id
                    or request["status"] not in {"completed", "closed"}
                ):
                    await db.rollback()
                    return False

                await db.execute(
                    """INSERT INTO reviews(
                           guild_id,request_id,author_id,target_id,rating,comment,created_at
                       ) VALUES (?,?,?,?,?,?,?)""",
                    (
                        guild_id,
                        request_id,
                        author_id,
                        target_id,
                        rating,
                        comment[:800],
                        int(time.time()),
                    ),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO profiles(guild_id,user_id) VALUES (?,?)",
                    (guild_id, target_id),
                )
                await db.execute(
                    """UPDATE profiles
                       SET reviews_count=reviews_count+1, rating_sum=rating_sum+?
                       WHERE guild_id=? AND user_id=?""",
                    (rating, guild_id, target_id),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                await db.rollback()
                return False
            except Exception:
                await db.rollback()
                raise
