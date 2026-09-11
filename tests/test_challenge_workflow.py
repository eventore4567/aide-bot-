import asyncio

from aidebot.app_db import AideBotDatabase
from aidebot.challenge_workflow import challenge_already_completed, resolve_challenge_atomic


def test_accepted_challenge_grants_reward_once():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            submission_id = await db.submit_challenge(1, 10, "permissions-1", "preuve")
            assert submission_id is not None
            first = await resolve_challenge_atomic(
                db._db(),
                submission_id=submission_id,
                guild_id=1,
                reviewer_id=99,
                accepted=True,
                reward=125,
            )
            assert first.changed is True
            profile = await db.profile(1, 10)
            assert int(profile["reputation"]) == 125

            second = await resolve_challenge_atomic(
                db._db(),
                submission_id=submission_id,
                guild_id=1,
                reviewer_id=98,
                accepted=True,
                reward=125,
            )
            assert second.changed is False
            profile = await db.profile(1, 10)
            assert int(profile["reputation"]) == 125
            assert await challenge_already_completed(db._db(), 1, 10, "permissions-1") is True
        finally:
            await db.close()

    asyncio.run(run())


def test_rejected_challenge_does_not_grant_reward():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            submission_id = await db.submit_challenge(1, 11, "bot-1", "preuve")
            assert submission_id is not None
            result = await resolve_challenge_atomic(
                db._db(),
                submission_id=submission_id,
                guild_id=1,
                reviewer_id=99,
                accepted=False,
                reward=200,
            )
            assert result.changed is True
            profile = await db.profile(1, 11)
            assert int(profile["reputation"]) == 0
            assert await challenge_already_completed(db._db(), 1, 11, "bot-1") is False
        finally:
            await db.close()

    asyncio.run(run())


def test_resolution_is_scoped_to_guild():
    async def run():
        db = AideBotDatabase(":memory:")
        await db.connect()
        try:
            submission_id = await db.submit_challenge(1, 12, "serveur-1", "preuve")
            assert submission_id is not None
            result = await resolve_challenge_atomic(
                db._db(),
                submission_id=submission_id,
                guild_id=2,
                reviewer_id=99,
                accepted=True,
                reward=100,
            )
            assert result.changed is False
            row = await db.challenge_submission(submission_id)
            assert row is not None
            assert row["status"] == "pending"
        finally:
            await db.close()

    asyncio.run(run())
