from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aidebot.transaction_guard import guarded_connection


ACTIVE_REQUEST_STATUSES = {"open", "assigned", "in_progress", "payment_pending"}


@dataclass(frozen=True)
class ReminderScheduleResult:
    reminder_id: int | None
    reason: str | None = None


@dataclass(frozen=True)
class ReminderCancelResult:
    cancelled: int
    delivery_in_progress: bool = False


async def schedule_reminder_atomic(
    db: Any,
    *,
    guild_id: int,
    request_id: int,
    channel_id: int,
    user_id: int,
    trainer_id: int | None,
    remind_at: int,
) -> ReminderScheduleResult:
    """Replace the pending reminder and request schedule in one transaction."""
    conn = db._db()
    async with guarded_connection(conn):
        await conn.execute("BEGIN IMMEDIATE")
        try:
            cur = await conn.execute(
                "SELECT status FROM requests WHERE id=? AND guild_id=?",
                (int(request_id), int(guild_id)),
            )
            row = await cur.fetchone()
            if row is None or str(row["status"]) not in ACTIVE_REQUEST_STATUSES:
                await conn.rollback()
                return ReminderScheduleResult(None, "inactive_request")

            cur = await conn.execute(
                "SELECT COUNT(*) AS n FROM reminders WHERE request_id=? AND state='processing'",
                (int(request_id),),
            )
            in_flight = await cur.fetchone()
            if in_flight and int(in_flight["n"]) > 0:
                await conn.rollback()
                return ReminderScheduleResult(None, "delivery_in_progress")

            await conn.execute(
                "UPDATE reminders SET state='cancelled' WHERE request_id=? AND state='pending'",
                (int(request_id),),
            )
            created = await conn.execute(
                """INSERT INTO reminders(
                       guild_id,request_id,channel_id,user_id,trainer_id,remind_at,created_at
                   ) VALUES (?,?,?,?,?,?,strftime('%s','now'))""",
                (
                    int(guild_id),
                    int(request_id),
                    int(channel_id),
                    int(user_id),
                    int(trainer_id) if trainer_id else None,
                    int(remind_at),
                ),
            )
            await conn.execute(
                "UPDATE requests SET scheduled_for=? WHERE id=? AND guild_id=?",
                (f"<t:{int(remind_at)}:F>", int(request_id), int(guild_id)),
            )
            await conn.commit()
            return ReminderScheduleResult(int(created.lastrowid), None)
        except Exception:
            await conn.rollback()
            raise


async def cancel_reminder_schedule_atomic(db: Any, *, guild_id: int, request_id: int) -> ReminderCancelResult:
    """Cancel pending reminders and clear the displayed schedule atomically.

    A reminder already in ``processing`` is intentionally not cancelled because
    Discord delivery may already have happened. The caller gets an explicit
    signal instead of a misleading success response.
    """
    conn = db._db()
    async with guarded_connection(conn):
        await conn.execute("BEGIN IMMEDIATE")
        try:
            cur = await conn.execute(
                "SELECT COUNT(*) AS n FROM reminders WHERE request_id=? AND state='processing'",
                (int(request_id),),
            )
            row = await cur.fetchone()
            if row and int(row["n"]) > 0:
                await conn.rollback()
                return ReminderCancelResult(0, True)

            changed = await conn.execute(
                "UPDATE reminders SET state='cancelled' WHERE request_id=? AND state='pending'",
                (int(request_id),),
            )
            await conn.execute(
                "UPDATE requests SET scheduled_for=NULL WHERE id=? AND guild_id=?",
                (int(request_id), int(guild_id)),
            )
            await conn.commit()
            return ReminderCancelResult(int(changed.rowcount), False)
        except Exception:
            await conn.rollback()
            raise
