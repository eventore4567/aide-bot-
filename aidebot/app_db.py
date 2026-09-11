from __future__ import annotations

import time
from typing import Any

import aiosqlite

from aidebot.db import Database
from aidebot.payments import PAYMENT_STATES, can_transition_payment, request_status_after_payment


ACTIVE_REQUEST_STATUSES = ("open", "assigned", "in_progress", "payment_pending")


class AideBotDatabase(Database):
    """Application-level read models and atomic workflow operations."""

    async def connect(self) -> None:
        await super().connect()
        await self._db().executescript(
            """
            CREATE TABLE IF NOT EXISTS learning_progress (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                path_key TEXT NOT NULL,
                max_lesson INTEGER NOT NULL DEFAULT 0,
                quiz_attempts INTEGER NOT NULL DEFAULT 0,
                quiz_correct INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, path_key)
            );
            CREATE INDEX IF NOT EXISTS learning_progress_user_idx
                ON learning_progress(guild_id, user_id, updated_at DESC);
            """
        )
        await self._db().commit()

    async def student_training_count(self, guild_id: int, user_id: int) -> int:
        cur = await self._db().execute(
            """SELECT COUNT(*) AS n
               FROM requests
               WHERE guild_id=?
                 AND user_id=?
                 AND training_key!='community_help'
                 AND status IN ('completed','closed')""",
            (guild_id, user_id),
        )
        row = await cur.fetchone()
        return int(row["n"]) if row else 0

    async def active_requests_for_user(self, guild_id: int, user_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        cur = await self._db().execute(
            """SELECT * FROM requests
               WHERE guild_id=?
                 AND user_id=?
                 AND status IN ('open','assigned','in_progress','payment_pending')
               ORDER BY created_at DESC
               LIMIT ?""",
            (guild_id, user_id, limit),
        )
        return list(await cur.fetchall())

    async def active_request_for_training(self, guild_id: int, user_id: int, training_key: str) -> aiosqlite.Row | None:
        cur = await self._db().execute(
            """SELECT * FROM requests
               WHERE guild_id=? AND user_id=? AND training_key=?
                 AND status IN ('open','assigned','in_progress','payment_pending')
               ORDER BY id DESC LIMIT 1""",
            (guild_id, user_id, training_key),
        )
        return await cur.fetchone()

    async def create_request_guarded(self, **values: Any) -> tuple[int | None, aiosqlite.Row | None]:
        """Create one active request per member/training, serialized in SQLite.

        Returns ``(new_id, None)`` when created or ``(None, existing_row)`` when
        an active request already exists.
        """
        db = self._db()
        await db.execute("BEGIN IMMEDIATE")
        try:
            cur = await db.execute(
                """SELECT * FROM requests
                   WHERE guild_id=? AND user_id=? AND training_key=?
                     AND status IN ('open','assigned','in_progress','payment_pending')
                   ORDER BY id DESC LIMIT 1""",
                (values["guild_id"], values["user_id"], values["training_key"]),
            )
            existing = await cur.fetchone()
            if existing:
                await db.rollback()
                return None, existing

            cur = await db.execute(
                """INSERT INTO requests(
                       guild_id,user_id,training_key,level,objective,availability,budget,
                       status,total_steps,payment_status,invite_used,created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    values["guild_id"], values["user_id"], values["training_key"], values.get("level", ""),
                    values.get("objective", ""), values.get("availability", ""), values.get("budget", ""),
                    values.get("status", "open"), values.get("total_steps", 1), values.get("payment_status", "not_required"),
                    1 if values.get("invite_used") else 0, int(time.time()),
                ),
            )
            await db.commit()
            return int(cur.lastrowid), None
        except Exception:
            await db.rollback()
            raise

    async def cancel_request_creation(self, request_id: int) -> bool:
        cur = await self._db().execute(
            """UPDATE requests SET status='cancelled'
               WHERE id=? AND channel_id IS NULL
                 AND status IN ('open','assigned','in_progress','payment_pending')""",
            (request_id,),
        )
        await self._db().commit()
        return cur.rowcount > 0

    async def claim_request(self, request_id: int, trainer_id: int) -> bool:
        cur = await self._db().execute(
            """UPDATE requests SET trainer_id=?, status='assigned'
               WHERE id=? AND trainer_id IS NULL
                 AND payment_status!='pending'
                 AND status IN ('open','assigned','in_progress')""",
            (trainer_id, request_id),
        )
        await self._db().commit()
        if cur.rowcount > 0:
            return True
        row = await self.request_by_id(request_id)
        return bool(row and row["trainer_id"] == trainer_id and row["status"] in {"assigned", "in_progress"})

    async def advance_request(self, request_id: int) -> tuple[int, int] | None:
        db = self._db()
        await db.execute("BEGIN IMMEDIATE")
        try:
            cur = await db.execute("SELECT progress,total_steps,status,trainer_id FROM requests WHERE id=?", (request_id,))
            row = await cur.fetchone()
            if not row or not row["trainer_id"] or row["status"] not in {"open", "assigned", "in_progress"}:
                await db.rollback()
                return None
            progress = min(int(row["progress"]) + 1, int(row["total_steps"]))
            await db.execute("UPDATE requests SET progress=?, status='in_progress' WHERE id=?", (progress, request_id))
            await db.commit()
            return progress, int(row["total_steps"])
        except Exception:
            await db.rollback()
            raise

    async def complete_request_once(self, request_id: int) -> aiosqlite.Row | None:
        db = self._db()
        await db.execute("BEGIN IMMEDIATE")
        try:
            cur = await db.execute("SELECT * FROM requests WHERE id=?", (request_id,))
            row = await cur.fetchone()
            if not row or not row["trainer_id"] or row["status"] not in {"open", "assigned", "in_progress"}:
                await db.rollback()
                return None
            await db.execute(
                "UPDATE requests SET status='completed', progress=total_steps WHERE id=?",
                (request_id,),
            )
            await db.commit()
            return row
        except Exception:
            await db.rollback()
            raise

    async def close_request_once(self, request_id: int) -> bool:
        cur = await self._db().execute(
            "UPDATE requests SET status='closed' WHERE id=? AND status='completed'",
            (request_id,),
        )
        await self._db().commit()
        return cur.rowcount > 0

    async def active_requests_for_guild(self, guild_id: int, limit: int = 200) -> list[aiosqlite.Row]:
        cur = await self._db().execute(
            """SELECT * FROM requests
               WHERE guild_id=? AND status IN ('open','assigned','in_progress','payment_pending')
               ORDER BY created_at ASC LIMIT ?""",
            (guild_id, limit),
        )
        return list(await cur.fetchall())

    async def cancel_orphan_request(self, request_id: int) -> bool:
        cur = await self._db().execute(
            """UPDATE requests SET status='cancelled'
               WHERE id=? AND status IN ('open','assigned','in_progress','payment_pending')""",
            (request_id,),
        )
        await self._db().commit()
        if cur.rowcount:
            await self.cancel_reminders_for_request(request_id)
            return True
        return False

    async def mark_lesson_seen(self, guild_id: int, user_id: int, path_key: str, lesson_number: int) -> None:
        now = int(time.time())
        await self._db().execute(
            """INSERT INTO learning_progress(guild_id,user_id,path_key,max_lesson,updated_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(guild_id,user_id,path_key) DO UPDATE SET
                 max_lesson=MAX(learning_progress.max_lesson, excluded.max_lesson),
                 updated_at=excluded.updated_at""",
            (guild_id, user_id, path_key, lesson_number, now),
        )
        await self._db().commit()

    async def record_quiz_answer(self, guild_id: int, user_id: int, path_key: str, correct: bool) -> None:
        now = int(time.time())
        await self._db().execute(
            """INSERT INTO learning_progress(guild_id,user_id,path_key,quiz_attempts,quiz_correct,updated_at)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(guild_id,user_id,path_key) DO UPDATE SET
                 quiz_attempts=learning_progress.quiz_attempts+1,
                 quiz_correct=learning_progress.quiz_correct+excluded.quiz_correct,
                 updated_at=excluded.updated_at""",
            (guild_id, user_id, path_key, 1, 1 if correct else 0, now),
        )
        await self._db().commit()

    async def learning_progress_for_path(self, guild_id: int, user_id: int, path_key: str) -> aiosqlite.Row | None:
        cur = await self._db().execute(
            "SELECT * FROM learning_progress WHERE guild_id=? AND user_id=? AND path_key=?",
            (guild_id, user_id, path_key),
        )
        return await cur.fetchone()

    async def learning_progress(self, guild_id: int, user_id: int) -> list[aiosqlite.Row]:
        cur = await self._db().execute(
            "SELECT * FROM learning_progress WHERE guild_id=? AND user_id=? ORDER BY updated_at DESC, path_key ASC",
            (guild_id, user_id),
        )
        return list(await cur.fetchall())

    async def transition_payment(self, request_id: int, target: str) -> tuple[bool, str | None]:
        """Atomically apply a valid payment transition.

        Returns ``(changed_or_already_target, previous_state)``. Free requests
        (`not_required`) and invalid transitions are rejected without mutation.
        """
        if target not in PAYMENT_STATES:
            return False, None

        db = self._db()
        await db.execute("BEGIN IMMEDIATE")
        try:
            cur = await db.execute(
                "SELECT payment_status,status FROM requests WHERE id=?",
                (request_id,),
            )
            row = await cur.fetchone()
            if row is None:
                await db.rollback()
                return False, None

            current = str(row["payment_status"])
            if current == "not_required" or not can_transition_payment(current, target):
                await db.rollback()
                return False, current
            if current == target:
                await db.rollback()
                return True, current

            next_request_status = request_status_after_payment(str(row["status"]), target)
            await db.execute(
                "UPDATE requests SET payment_status=?, status=? WHERE id=? AND payment_status=?",
                (target, next_request_status, request_id, current),
            )
            await db.commit()
            return True, current
        except Exception:
            await db.rollback()
            raise
