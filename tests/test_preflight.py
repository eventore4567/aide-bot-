import asyncio

from aidebot.app_db import AideBotDatabase
from aidebot.preflight import database_integrity_counts, summarize_preflight


def test_clean_database_is_ready_from_integrity_perspective():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            counts = await database_integrity_counts(db._db())
            assert all(value == 0 for value in counts.values())
            summary = summarize_preflight(hard_blockers=0, integrity_counts=counts)
            assert summary.ready is True
            assert summary.blocking_count == 0
        finally:
            await db.close()

    asyncio.run(run())


def test_preflight_detects_duplicate_active_requests_and_missing_channels():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            for _ in range(2):
                await db._db().execute(
                    """INSERT INTO requests(guild_id,user_id,training_key,status,total_steps,payment_status,created_at)
                       VALUES (1,10,'discord','open',3,'not_required',1)"""
                )
            await db._db().commit()
            counts = await database_integrity_counts(db._db())
            assert counts["duplicate_active_requests"] == 1
            assert counts["active_without_channel"] == 2
            summary = summarize_preflight(hard_blockers=0, integrity_counts=counts)
            assert summary.ready is False
            assert summary.blocking_count >= 3
        finally:
            await db.close()

    asyncio.run(run())


def test_preflight_detects_payment_and_progress_corruption():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            await db._db().execute(
                """INSERT INTO requests(
                       guild_id,user_id,training_key,status,progress,total_steps,channel_id,payment_status,created_at
                   ) VALUES (1,11,'vip','open',5,2,123,'pending',1)"""
            )
            await db._db().commit()
            counts = await database_integrity_counts(db._db())
            assert counts["invalid_progress"] == 1
            assert counts["payment_status_mismatch"] == 1
        finally:
            await db.close()

    asyncio.run(run())


def test_pending_reminder_on_completed_request_is_warning_not_blocker():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            cur = await db._db().execute(
                """INSERT INTO requests(
                       guild_id,user_id,training_key,status,trainer_id,progress,total_steps,channel_id,payment_status,created_at
                   ) VALUES (1,12,'discord','completed',99,2,2,456,'not_required',1)"""
            )
            request_id = int(cur.lastrowid)
            await db._db().execute(
                """INSERT INTO reminders(guild_id,request_id,channel_id,user_id,trainer_id,remind_at,state,created_at)
                   VALUES (1,?,456,12,99,9999999999,'pending',1)""",
                (request_id,),
            )
            await db._db().commit()
            counts = await database_integrity_counts(db._db())
            assert counts["terminal_pending_reminders"] == 1
            summary = summarize_preflight(hard_blockers=0, integrity_counts=counts)
            assert summary.ready is True
            assert summary.warning_count == 1
        finally:
            await db.close()

    asyncio.run(run())


def test_application_states_match_database_workflow():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            for status in ("pending", "processing", "accepted", "rejected"):
                await db._db().execute(
                    """INSERT INTO applications(
                           guild_id,user_id,target_role,status,created_at
                       ) VALUES (1,?,?,?,1)""",
                    (100 + len(status), "helper", status),
                )
            await db._db().commit()
            counts = await database_integrity_counts(db._db())
            assert counts["invalid_applications"] == 0
            assert counts["processing_applications"] == 1
            summary = summarize_preflight(hard_blockers=0, integrity_counts=counts)
            assert summary.ready is True
            assert summary.warning_count == 1

            await db._db().execute(
                """INSERT INTO applications(
                       guild_id,user_id,target_role,status,created_at
                   ) VALUES (1,999,'trainer','refused',1)"""
            )
            await db._db().commit()
            counts = await database_integrity_counts(db._db())
            assert counts["invalid_applications"] == 1
        finally:
            await db.close()

    asyncio.run(run())
