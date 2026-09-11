from __future__ import annotations

from typing import Any

from aidebot.transaction_guard import guarded_connection


VALID_TERMINAL_STATES = {"sent", "failed", "cancelled"}


def delivery_marker(reminder_id: int) -> str:
    return f"AideBot • rappel #{int(reminder_id)}"


async def claim_due_reminders(conn: Any, now: int, limit: int = 50) -> list[Any]:
    """Atomically claim due reminders so one loop cannot send them twice.

    A reminder moves from ``pending`` to ``processing`` before any Discord side
    effect. If the process dies after the Discord message was sent but before
    the DB is finalized, startup reconciliation can identify the message using
    the deterministic embed footer marker.
    """
    async with guarded_connection(conn):
        await conn.execute("BEGIN IMMEDIATE")
        try:
            cur = await conn.execute(
                """SELECT * FROM reminders
                   WHERE state='pending' AND remind_at<=?
                   ORDER BY remind_at ASC, id ASC
                   LIMIT ?""",
                (int(now), int(limit)),
            )
            rows = list(await cur.fetchall())
            if not rows:
                await conn.rollback()
                return []

            ids = [int(row["id"]) for row in rows]
            placeholders = ",".join("?" for _ in ids)
            await conn.execute(
                f"UPDATE reminders SET state='processing' WHERE state='pending' AND id IN ({placeholders})",
                ids,
            )
            await conn.commit()
            return rows
        except Exception:
            await conn.rollback()
            raise


async def processing_reminders(conn: Any, limit: int = 100) -> list[Any]:
    cur = await conn.execute(
        "SELECT * FROM reminders WHERE state='processing' ORDER BY remind_at ASC, id ASC LIMIT ?",
        (int(limit),),
    )
    return list(await cur.fetchall())


async def finish_processing_reminder(conn: Any, reminder_id: int, state: str) -> bool:
    if state not in VALID_TERMINAL_STATES:
        raise ValueError("Invalid terminal reminder state")
    async with guarded_connection(conn):
        cur = await conn.execute(
            "UPDATE reminders SET state=? WHERE id=? AND state='processing'",
            (state, int(reminder_id)),
        )
        await conn.commit()
        return cur.rowcount == 1


async def release_processing_reminder(conn: Any, reminder_id: int) -> bool:
    """Return an un-delivered claimed reminder to the queue."""
    async with guarded_connection(conn):
        cur = await conn.execute(
            "UPDATE reminders SET state='pending' WHERE id=? AND state='processing'",
            (int(reminder_id),),
        )
        await conn.commit()
        return cur.rowcount == 1
