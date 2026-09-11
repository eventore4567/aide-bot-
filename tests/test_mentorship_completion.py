import asyncio

from aidebot.integrity_db import IntegrityDatabase


def test_mentorship_completion_rewards_once(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            mentorship_id = await db.create_mentorship(1, 10, "permissions")
            assert mentorship_id is not None
            assert await db.claim_mentorship(mentorship_id, 99) is True

            completed = await db.complete_mentorship_once(mentorship_id, 1)
            assert completed is not None
            mentor = await db.profile(1, 99)
            assert mentor["reputation"] == 30

            replay = await db.complete_mentorship_once(mentorship_id, 1)
            assert replay is None
            mentor = await db.profile(1, 99)
            assert mentor["reputation"] == 30
        finally:
            await db.close()

    asyncio.run(scenario())


def test_mentorship_completion_is_guild_scoped_and_requires_active_mentor(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            mentorship_id = await db.create_mentorship(1, 10, "discord")
            assert mentorship_id is not None
            assert await db.complete_mentorship_once(mentorship_id, 2) is None
            assert await db.complete_mentorship_once(mentorship_id, 1) is None

            assert await db.claim_mentorship(mentorship_id, 99) is True
            assert await db.complete_mentorship_once(mentorship_id, 1) is not None
        finally:
            await db.close()

    asyncio.run(scenario())


def test_parallel_mentorship_completion_only_rewards_once(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            mentorship_id = await db.create_mentorship(1, 10, "securite")
            assert mentorship_id is not None
            assert await db.claim_mentorship(mentorship_id, 99) is True

            first, second = await asyncio.gather(
                db.complete_mentorship_once(mentorship_id, 1),
                db.complete_mentorship_once(mentorship_id, 1),
            )
            assert sum(result is not None for result in (first, second)) == 1
            mentor = await db.profile(1, 99)
            assert mentor["reputation"] == 30
        finally:
            await db.close()

    asyncio.run(scenario())
