from __future__ import annotations

import time

import aiosqlite

from aidebot.app_db import AideBotDatabase as BaseAideBotDatabase


class IntegrityDatabase(BaseAideBotDatabase):
    """Production database boundary for workflows that must stay atomic."""

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
