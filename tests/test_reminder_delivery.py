import asyncio

from aidebot.integrity_db import IntegrityDatabase
from aidebot.reminder_delivery import (
    claim_due_reminders,
    delivery_marker,
    finish_processing_reminder,
    processing_reminders,
    release_processing_reminder,
)
from aidebot.reminder_schedule import schedule_reminder_atomic


def test_delivery_marker_is_stable():
    assert delivery_marker(42) == "AideBot • rappel #42"


def test_due_reminder_is_claimed_once_under_concurrency():
    async def run():
        db = IntegrityDatabase(":memory:")
        await db.connect()
        try:
            reminder_id = await db.create_reminder(1, 10, 20, 30, 40, 100)
            first, second = await asyncio.gather(
                claim_due_reminders(db._db(), 100, 10),
                claim_due_reminders(db._db(), 100, 10),
            )
            claimed = [row for batch in (first, second) for row in batch]
            assert [int(row["id"]) for row in claimed] == [reminder_id]

            rows = await processing_reminders(db._db())
            assert [int(row["id"]) for row in rows] == [reminder_id]
        finally:
            await db.close()

    asyncio.run(run())


def test_processing_reminder_can_be_released_then_finalized_without_replay():
    async def run():
        db = IntegrityDatabase(":memory:")
        await db.connect()
        try:
            reminder_id = await db.create_reminder(1, 10, 20, 30, None, 100)
            claimed = await claim_due_reminders(db._db(), 100, 10)
            assert len(claimed) == 1

            assert await release_processing_reminder(db._db(), reminder_id) is True
            claimed_again = await claim_due_reminders(db._db(), 100, 10)
            assert len(claimed_again) == 1
            assert int(claimed_again[0]["id"]) == reminder_id

            assert await finish_processing_reminder(db._db(), reminder_id, "sent") is True
            assert await finish_processing_reminder(db._db(), reminder_id, "sent") is False
            assert await claim_due_reminders(db._db(), 100, 10) == []
        finally:
            await db.close()

    asyncio.run(run())


def test_terminal_delivery_clears_schedule_but_release_keeps_it():
    async def run():
        db = IntegrityDatabase(":memory:")
        await db.connect()
        try:
            request_id = await db.create_request(
                guild_id=1,
                user_id=30,
                training_key="discord",
                status="open",
                payment_status="not_required",
                total_steps=2,
                invite_used=False,
            )
            scheduled = await schedule_reminder_atomic(
                db,
                guild_id=1,
                request_id=request_id,
                channel_id=20,
                user_id=30,
                trainer_id=40,
                remind_at=100,
            )
            assert scheduled.reminder_id is not None

            claimed = await claim_due_reminders(db._db(), 100, 10)
            assert len(claimed) == 1
            reminder_id = int(claimed[0]["id"])

            req = await db.request_by_id(request_id)
            assert req is not None
            assert req["scheduled_for"] == "<t:100:F>"

            assert await release_processing_reminder(db._db(), reminder_id) is True
            req = await db.request_by_id(request_id)
            assert req is not None
            assert req["scheduled_for"] == "<t:100:F>"

            claimed_again = await claim_due_reminders(db._db(), 100, 10)
            assert len(claimed_again) == 1
            assert await finish_processing_reminder(db._db(), reminder_id, "sent") is True

            req = await db.request_by_id(request_id)
            assert req is not None
            assert req["scheduled_for"] is None
        finally:
            await db.close()

    asyncio.run(run())


def test_terminal_delivery_keeps_schedule_when_another_active_reminder_exists():
    async def run():
        db = IntegrityDatabase(":memory:")
        await db.connect()
        try:
            request_id = await db.create_request(
                guild_id=1,
                user_id=30,
                training_key="discord",
                status="open",
                payment_status="not_required",
                total_steps=2,
                invite_used=False,
            )
            await db.update_request(request_id, scheduled_for="<t:200:F>")
            processing_id = await db.create_reminder(1, request_id, 20, 30, 40, 100)
            await db._db().execute(
                "UPDATE reminders SET state='processing' WHERE id=?",
                (processing_id,),
            )
            await db._db().execute(
                """INSERT INTO reminders(
                       guild_id,request_id,channel_id,user_id,trainer_id,remind_at,state,created_at
                   ) VALUES (1,?,20,30,40,200,'pending',1)""",
                (request_id,),
            )
            await db._db().commit()

            assert await finish_processing_reminder(db._db(), processing_id, "sent") is True
            req = await db.request_by_id(request_id)
            assert req is not None
            assert req["scheduled_for"] == "<t:200:F>"
        finally:
            await db.close()

    asyncio.run(run())


def test_non_due_reminder_is_not_claimed():
    async def run():
        db = IntegrityDatabase(":memory:")
        await db.connect()
        try:
            await db.create_reminder(1, 10, 20, 30, None, 200)
            assert await claim_due_reminders(db._db(), 199, 10) == []
        finally:
            await db.close()

    asyncio.run(run())
