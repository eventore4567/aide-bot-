import asyncio

from aidebot.integrity_db import IntegrityDatabase
from aidebot.reminder_delivery import (
    claim_due_reminders,
    delivery_marker,
    finish_processing_reminder,
    processing_reminders,
    release_processing_reminder,
)


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
