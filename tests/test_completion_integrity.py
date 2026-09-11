import asyncio

from aidebot.app_db import AideBotDatabase


def test_training_completion_credits_trainer_and_cancels_reminder_once():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            cur = await db._db().execute(
                """INSERT INTO requests(
                       guild_id,user_id,training_key,status,trainer_id,progress,total_steps,channel_id,payment_status,created_at
                   ) VALUES (1,10,'discord','in_progress',99,2,3,123,'not_required',1)"""
            )
            request_id = int(cur.lastrowid)
            await db._db().execute(
                """INSERT INTO reminders(guild_id,request_id,channel_id,user_id,trainer_id,remind_at,state,created_at)
                   VALUES (1,?,123,10,99,9999999999,'pending',1)""",
                (request_id,),
            )
            await db._db().commit()

            completed = await db.complete_request_once(request_id)
            assert completed is not None
            request = await db.request_by_id(request_id)
            assert request is not None
            assert request["status"] == "completed"
            assert int(request["progress"]) == 3

            profile = await db.profile(1, 99)
            assert int(profile["reputation"]) == 50
            assert int(profile["trainings_completed"]) == 1

            cur = await db._db().execute("SELECT state FROM reminders WHERE request_id=?", (request_id,))
            reminder = await cur.fetchone()
            assert reminder["state"] == "cancelled"

            # Existing TrainingCog compatibility call must not double-credit.
            await db.complete_for_trainer(1, 99, False)
            assert await db.complete_request_once(request_id) is None
            profile = await db.profile(1, 99)
            assert int(profile["reputation"]) == 50
            assert int(profile["trainings_completed"]) == 1
        finally:
            await db.close()

    asyncio.run(run())


def test_community_help_completion_credits_help_stats_once():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            cur = await db._db().execute(
                """INSERT INTO requests(
                       guild_id,user_id,training_key,status,trainer_id,total_steps,channel_id,payment_status,created_at
                   ) VALUES (1,11,'community_help','assigned',88,1,124,'not_required',1)"""
            )
            request_id = int(cur.lastrowid)
            await db._db().commit()

            assert await db.complete_request_once(request_id) is not None
            profile = await db.profile(1, 88)
            assert int(profile["reputation"]) == 25
            assert int(profile["helped_count"]) == 1
            assert int(profile["trainings_completed"]) == 0

            assert await db.complete_request_once(request_id) is None
            profile = await db.profile(1, 88)
            assert int(profile["reputation"]) == 25
            assert int(profile["helped_count"]) == 1
        finally:
            await db.close()

    asyncio.run(run())


def test_completion_without_assignee_makes_no_partial_changes():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            cur = await db._db().execute(
                """INSERT INTO requests(
                       guild_id,user_id,training_key,status,total_steps,channel_id,payment_status,created_at
                   ) VALUES (1,12,'discord','open',3,125,'not_required',1)"""
            )
            request_id = int(cur.lastrowid)
            await db._db().commit()

            assert await db.complete_request_once(request_id) is None
            request = await db.request_by_id(request_id)
            assert request is not None
            assert request["status"] == "open"
            assert int(request["progress"]) == 0
        finally:
            await db.close()

    asyncio.run(run())
