import asyncio

from aidebot.challenge_workflow import resolve_challenge_atomic
from aidebot.integrity_db import IntegrityDatabase
from aidebot.invite_integrity import finalize_pending_invite


def test_parallel_challenge_validation_rewards_once(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            submission_id = await db.submit_challenge(1, 10, "permissions", "preuve")
            assert submission_id is not None
            first, second = await asyncio.gather(
                resolve_challenge_atomic(db._db(), submission_id=submission_id, guild_id=1, reviewer_id=90, accepted=True, reward=50),
                resolve_challenge_atomic(db._db(), submission_id=submission_id, guild_id=1, reviewer_id=91, accepted=True, reward=50),
            )
            assert sum(result.changed for result in (first, second)) == 1
            profile = await db.profile(1, 10)
            assert profile["reputation"] == 50
        finally:
            await db.close()

    asyncio.run(scenario())


def test_parallel_invite_finalization_credits_once(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            await db.add_pending_invite(1, 10, 20, 1)
            pending_id = int((await db.due_pending_invites(2))[0]["id"])
            first, second = await asyncio.gather(
                finalize_pending_invite(db, pending_id, True),
                finalize_pending_invite(db, pending_id, True),
            )
            assert sum(result is not None for result in (first, second)) == 1
            assert await db.invite_credits(1, 10) == 1
        finally:
            await db.close()

    asyncio.run(scenario())
