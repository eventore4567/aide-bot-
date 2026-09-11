from __future__ import annotations

from typing import Any


async def finalize_pending_invite(db: Any, pending_id: int, valid: bool):
    """Finalize one pending invite exactly once.

    A valid invite and its training credit are committed in the same SQLite
    transaction. Replays, overlapping validation loops and retries therefore
    cannot grant the same invite credit twice.

    Returns the finalized pending-invite row on the first successful
    transition, or ``None`` when the invite is missing/already finalized.
    """
    conn = db._db()
    await conn.execute("BEGIN IMMEDIATE")
    try:
        cur = await conn.execute(
            "SELECT * FROM pending_invites WHERE id=?",
            (pending_id,),
        )
        row = await cur.fetchone()
        if row is None or row["state"] != "pending":
            await conn.rollback()
            return None

        target_state = "valid" if valid else "invalid"
        changed = await conn.execute(
            "UPDATE pending_invites SET state=? WHERE id=? AND state='pending'",
            (target_state, pending_id),
        )
        if changed.rowcount != 1:
            await conn.rollback()
            return None

        if valid:
            await conn.execute(
                """INSERT INTO invite_credits(guild_id,user_id,credits) VALUES (?,?,1)
                   ON CONFLICT(guild_id,user_id) DO UPDATE SET credits=credits+1""",
                (row["guild_id"], row["inviter_id"]),
            )

        await conn.commit()
        return row
    except Exception:
        await conn.rollback()
        raise
