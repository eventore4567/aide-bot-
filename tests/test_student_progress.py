import asyncio

from aidebot.app_db import AideBotDatabase


def test_student_progress_is_derived_from_completed_requests(tmp_path):
    async def scenario() -> None:
        db = AideBotDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            completed = await db.create_request(
                guild_id=1,
                user_id=10,
                training_key="discord",
                total_steps=6,
                status="open",
                payment_status="not_required",
                invite_used=False,
            )
            active = await db.create_request(
                guild_id=1,
                user_id=10,
                training_key="serveur",
                total_steps=7,
                status="open",
                payment_status="not_required",
                invite_used=False,
            )
            community = await db.create_request(
                guild_id=1,
                user_id=10,
                training_key="community_help",
                total_steps=1,
                status="open",
                payment_status="not_required",
                invite_used=False,
            )

            await db.update_request(completed, status="completed", progress=6)
            await db.update_request(community, status="completed", progress=1)

            assert await db.student_training_count(1, 10) == 1

            rows = await db.active_requests_for_user(1, 10)
            assert [row["id"] for row in rows] == [active]
        finally:
            await db.close()

    asyncio.run(scenario())


def test_trainer_counter_does_not_change_student_training_count(tmp_path):
    async def scenario() -> None:
        db = AideBotDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            await db.complete_for_trainer(1, 99, community_help=False)
            trainer = await db.profile(1, 99)
            assert trainer["trainings_completed"] == 1
            assert await db.student_training_count(1, 99) == 0
        finally:
            await db.close()

    asyncio.run(scenario())
