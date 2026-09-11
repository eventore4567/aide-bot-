import asyncio

from aidebot.integrity_db import IntegrityDatabase
from aidebot.reminder_delivery import claim_due_reminders
from aidebot.reminder_schedule import cancel_reminder_schedule_atomic, schedule_reminder_atomic


async def _request(db, guild_id: int = 1, user_id: int = 10) -> int:
    return await db.create_request(
        guild_id=guild_id,
        user_id=user_id,
        training_key="discord",
        status="open",
        total_steps=2,
        payment_status="not_required",
    )


def test_schedule_sets_request_and_replaces_pending_reminder_atomically():
    async def run():
        db = IntegrityDatabase(":memory:")
        await db.connect()
        try:
            request_id = await _request(db)
            first = await schedule_reminder_atomic(
                db,
                guild_id=1,
                request_id=request_id,
                channel_id=20,
                user_id=10,
                trainer_id=99,
                remind_at=100,
            )
            second = await schedule_reminder_atomic(
                db,
                guild_id=1,
                request_id=request_id,
                channel_id=20,
                user_id=10,
                trainer_id=99,
                remind_at=200,
            )
            assert first.reminder_id is not None
            assert second.reminder_id is not None
            assert second.reminder_id != first.reminder_id

            cur = await db._db().execute("SELECT state,remind_at FROM reminders ORDER BY id")
            rows = await cur.fetchall()
            assert [(row["state"], row["remind_at"]) for row in rows] == [("cancelled", 100), ("pending", 200)]

            req = await db.request_by_id(request_id)
            assert req["scheduled_for"] == "<t:200:F>"
        finally:
            await db.close()

    asyncio.run(run())


def test_cancel_clears_pending_reminder_and_schedule():
    async def run():
        db = IntegrityDatabase(":memory:")
        await db.connect()
        try:
            request_id = await _request(db)
            await schedule_reminder_atomic(
                db,
                guild_id=1,
                request_id=request_id,
                channel_id=20,
                user_id=10,
                trainer_id=99,
                remind_at=100,
            )
            result = await cancel_reminder_schedule_atomic(db, guild_id=1, request_id=request_id)
            assert result.cancelled == 1
            assert result.delivery_in_progress is False
            req = await db.request_by_id(request_id)
            assert req["scheduled_for"] is None
        finally:
            await db.close()

    asyncio.run(run())


def test_reschedule_and_cancel_fail_closed_while_delivery_is_processing():
    async def run():
        db = IntegrityDatabase(":memory:")
        await db.connect()
        try:
            request_id = await _request(db)
            scheduled = await schedule_reminder_atomic(
                db,
                guild_id=1,
                request_id=request_id,
                channel_id=20,
                user_id=10,
                trainer_id=99,
                remind_at=100,
            )
            assert scheduled.reminder_id is not None
            claimed = await claim_due_reminders(db._db(), 100, 10)
            assert len(claimed) == 1

            reschedule = await schedule_reminder_atomic(
                db,
                guild_id=1,
                request_id=request_id,
                channel_id=20,
                user_id=10,
                trainer_id=99,
                remind_at=200,
            )
            assert reschedule.reminder_id is None
            assert reschedule.reason == "delivery_in_progress"

            cancelled = await cancel_reminder_schedule_atomic(db, guild_id=1, request_id=request_id)
            assert cancelled.delivery_in_progress is True
            req = await db.request_by_id(request_id)
            assert req["scheduled_for"] == "<t:100:F>"
        finally:
            await db.close()

    asyncio.run(run())


def test_inactive_request_cannot_schedule_reminder():
    async def run():
        db = IntegrityDatabase(":memory:")
        await db.connect()
        try:
            request_id = await _request(db)
            await db.update_request(request_id, status="completed")
            result = await schedule_reminder_atomic(
                db,
                guild_id=1,
                request_id=request_id,
                channel_id=20,
                user_id=10,
                trainer_id=99,
                remind_at=100,
            )
            assert result.reminder_id is None
            assert result.reason == "inactive_request"
        finally:
            await db.close()

    asyncio.run(run())
