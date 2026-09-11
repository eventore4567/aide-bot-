import asyncio

from aidebot.app_db import AideBotDatabase
from aidebot.invite_integrity import finalize_pending_invite


def test_valid_invite_is_finalized_and_credited_exactly_once(tmp_path):
    async def scenario() -> None:
        db = AideBotDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            await db.add_pending_invite(1, 10, 20, 1)
            due = await db.due_pending_invites(2)
            assert len(due) == 1
            pending_id = int(due[0]["id"])

            first = await finalize_pending_invite(db, pending_id, True)
            assert first is not None
            assert await db.invite_credits(1, 10) == 1
            assert await db.validated_invites(1, 10) == 1

            replay = await finalize_pending_invite(db, pending_id, True)
            assert replay is None
            assert await db.invite_credits(1, 10) == 1
            assert await db.validated_invites(1, 10) == 1
        finally:
            await db.close()

    asyncio.run(scenario())


def test_invalid_invite_is_finalized_without_credit(tmp_path):
    async def scenario() -> None:
        db = AideBotDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            await db.add_pending_invite(1, 11, 21, 1)
            pending_id = int((await db.due_pending_invites(2))[0]["id"])

            first = await finalize_pending_invite(db, pending_id, False)
            assert first is not None
            assert await db.invite_credits(1, 11) == 0
            assert await db.validated_invites(1, 11) == 0

            replay = await finalize_pending_invite(db, pending_id, False)
            assert replay is None
            assert await db.invite_credits(1, 11) == 0
        finally:
            await db.close()

    asyncio.run(scenario())


def test_missing_invite_cannot_create_credit(tmp_path):
    async def scenario() -> None:
        db = AideBotDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            assert await finalize_pending_invite(db, 999999, True) is None
            assert await db.invite_credits(1, 10) == 0
        finally:
            await db.close()

    asyncio.run(scenario())
