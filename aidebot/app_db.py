from __future__ import annotations

import aiosqlite

from aidebot.db import Database


class AideBotDatabase(Database):
    """Application-level read models built on top of the core SQLite store.

    The historical `profiles.trainings_completed` counter tracks trainings
    completed *as trainer*. Student progress is derived from requests so the
    member-facing profile does not confuse trainings followed with trainings
    delivered.
    """

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
