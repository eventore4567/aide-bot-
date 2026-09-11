from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from aidebot.transaction_guard import guarded_connection


ACTIVE_REQUEST_STATUSES = ("open", "assigned", "in_progress", "payment_pending")


@dataclass(frozen=True)
class RequestCreationResult:
    request_id: int | None
    existing: Any | None = None
    reason: str = "created"
    invite_used: bool = False


@dataclass(frozen=True)
class RequestCancellationResult:
    changed: bool
    refunded_invite: bool = False


async def create_request_with_entitlement_atomic(
    db: Any,
    *,
    requires_invite: bool,
    guild_id: int,
    user_id: int,
    training_key: str,
    total_steps: int,
    level: str = "",
    objective: str = "",
    availability: str = "",
    budget: str = "",
    status: str = "open",
    payment_status: str = "not_required",
) -> RequestCreationResult:
    """Create a request and consume its invite credit in one transaction.

    Duplicate detection happens before credit consumption. If the insert fails,
    SQLite rolls the credit deduction back with it. This removes the crash
    window where a member could lose a credit before the request existed.
    """
    conn = db._db()
    async with guarded_connection(conn):
        await conn.execute("BEGIN IMMEDIATE")
        try:
            placeholders = ",".join("?" for _ in ACTIVE_REQUEST_STATUSES)
            cur = await conn.execute(
                f"""SELECT * FROM requests
                    WHERE guild_id=? AND user_id=? AND training_key=?
                      AND status IN ({placeholders})
                    ORDER BY id DESC LIMIT 1""",
                (guild_id, user_id, training_key, *ACTIVE_REQUEST_STATUSES),
            )
            existing = await cur.fetchone()
            if existing is not None:
                await conn.rollback()
                return RequestCreationResult(None, existing=existing, reason="duplicate")

            if requires_invite:
                changed = await conn.execute(
                    """UPDATE invite_credits
                       SET credits=credits-1
                       WHERE guild_id=? AND user_id=? AND credits>0""",
                    (guild_id, user_id),
                )
                if changed.rowcount != 1:
                    await conn.rollback()
                    return RequestCreationResult(None, reason="insufficient_credit")

            cur = await conn.execute(
                """INSERT INTO requests(
                       guild_id,user_id,training_key,level,objective,availability,budget,
                       status,total_steps,payment_status,invite_used,created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    guild_id,
                    user_id,
                    training_key,
                    level,
                    objective,
                    availability,
                    budget,
                    status,
                    max(1, int(total_steps)),
                    payment_status,
                    1 if requires_invite else 0,
                    int(time.time()),
                ),
            )
            await conn.commit()
            return RequestCreationResult(
                int(cur.lastrowid),
                reason="created",
                invite_used=requires_invite,
            )
        except Exception:
            await conn.rollback()
            raise


async def cancel_request_atomic(
    db: Any,
    request_id: int,
    *,
    refund_invite: bool,
) -> RequestCancellationResult:
    """Cancel one active request, cancel reminders and optionally refund once."""
    conn = db._db()
    async with guarded_connection(conn):
        await conn.execute("BEGIN IMMEDIATE")
        try:
            cur = await conn.execute(
                "SELECT guild_id,user_id,status,invite_used FROM requests WHERE id=?",
                (request_id,),
            )
            row = await cur.fetchone()
            if row is None or row["status"] not in ACTIVE_REQUEST_STATUSES:
                await conn.rollback()
                return RequestCancellationResult(False, False)

            placeholders = ",".join("?" for _ in ACTIVE_REQUEST_STATUSES)
            changed = await conn.execute(
                f"""UPDATE requests SET status='cancelled'
                    WHERE id=? AND status IN ({placeholders})""",
                (request_id, *ACTIVE_REQUEST_STATUSES),
            )
            if changed.rowcount != 1:
                await conn.rollback()
                return RequestCancellationResult(False, False)

            await conn.execute(
                "UPDATE reminders SET state='cancelled' WHERE request_id=? AND state='pending'",
                (request_id,),
            )

            refunded = bool(refund_invite and row["invite_used"])
            if refunded:
                await conn.execute(
                    """INSERT INTO invite_credits(guild_id,user_id,credits) VALUES (?,?,1)
                       ON CONFLICT(guild_id,user_id) DO UPDATE SET credits=credits+1""",
                    (row["guild_id"], row["user_id"]),
                )

            await conn.commit()
            return RequestCancellationResult(True, refunded)
        except Exception:
            await conn.rollback()
            raise
