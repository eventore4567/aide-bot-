from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChallengeResolution:
    changed: bool
    user_id: int | None = None
    status: str | None = None


async def challenge_already_completed(conn: Any, guild_id: int, user_id: int, challenge_key: str) -> bool:
    cur = await conn.execute(
        """SELECT 1
           FROM challenge_submissions
           WHERE guild_id=? AND user_id=? AND challenge_key=? AND status='accepted'
           LIMIT 1""",
        (guild_id, user_id, challenge_key),
    )
    return await cur.fetchone() is not None


async def resolve_challenge_atomic(
    conn: Any,
    *,
    submission_id: int,
    guild_id: int,
    reviewer_id: int,
    accepted: bool,
    reward: int,
) -> ChallengeResolution:
    """Resolve one pending challenge and grant reputation in one DB transaction.

    This closes the crash window where a submission could be marked accepted
    but the reputation reward was never written, and prevents a second
    reviewer from granting the reward twice.
    """
    await conn.execute("BEGIN IMMEDIATE")
    try:
        cur = await conn.execute(
            """SELECT user_id,status
               FROM challenge_submissions
               WHERE id=? AND guild_id=?""",
            (submission_id, guild_id),
        )
        row = await cur.fetchone()
        if row is None or row["status"] != "pending":
            await conn.rollback()
            return ChallengeResolution(False)

        new_status = "accepted" if accepted else "rejected"
        cur = await conn.execute(
            """UPDATE challenge_submissions
               SET status=?, reviewer_id=?
               WHERE id=? AND guild_id=? AND status='pending'""",
            (new_status, reviewer_id, submission_id, guild_id),
        )
        if cur.rowcount != 1:
            await conn.rollback()
            return ChallengeResolution(False)

        user_id = int(row["user_id"])
        if accepted and reward > 0:
            await conn.execute(
                "INSERT OR IGNORE INTO profiles(guild_id,user_id) VALUES (?,?)",
                (guild_id, user_id),
            )
            await conn.execute(
                "UPDATE profiles SET reputation=reputation+? WHERE guild_id=? AND user_id=?",
                (int(reward), guild_id, user_id),
            )

        await conn.commit()
        return ChallengeResolution(True, user_id=user_id, status=new_status)
    except Exception:
        await conn.rollback()
        raise
