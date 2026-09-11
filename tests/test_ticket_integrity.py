import asyncio

from aidebot.app_db import AideBotDatabase
from aidebot.catalog import FORMATIONS
from aidebot.ticketing import STEP_RESOURCES, format_guidance, next_step_guidance


def test_atomic_ticket_lifecycle(tmp_path):
    async def scenario() -> None:
        db = AideBotDatabase(str(tmp_path / "ticket-integrity.db"))
        await db.connect()
        try:
            first, existing = await db.create_request_guarded(
                guild_id=1,
                user_id=50,
                training_key="discord",
                total_steps=6,
                status="open",
                payment_status="not_required",
                invite_used=True,
            )
            assert first is not None
            assert existing is None

            duplicate, existing = await db.create_request_guarded(
                guild_id=1,
                user_id=50,
                training_key="discord",
                total_steps=6,
                status="open",
                payment_status="not_required",
                invite_used=True,
            )
            assert duplicate is None
            assert existing is not None
            assert existing["id"] == first

            assert await db.claim_request(first, 100) is True
            assert await db.claim_request(first, 100) is True
            assert await db.claim_request(first, 101) is False

            assert await db.advance_request(first) == (1, 6)
            completed = await db.complete_request_once(first)
            assert completed is not None
            assert completed["trainer_id"] == 100
            assert await db.complete_request_once(first) is None
            assert await db.close_request_once(first) is True
            assert await db.close_request_once(first) is False

            reopened, existing = await db.create_request_guarded(
                guild_id=1,
                user_id=50,
                training_key="discord",
                total_steps=6,
                status="open",
                payment_status="not_required",
                invite_used=False,
            )
            assert reopened is not None
            assert existing is None
        finally:
            await db.close()

    asyncio.run(scenario())


def test_orphan_cancel_frees_training_slot(tmp_path):
    async def scenario() -> None:
        db = AideBotDatabase(str(tmp_path / "ticket-orphan.db"))
        await db.connect()
        try:
            request_id, _ = await db.create_request_guarded(
                guild_id=2,
                user_id=60,
                training_key="serveur",
                total_steps=7,
                status="open",
                payment_status="not_required",
                invite_used=False,
            )
            assert request_id is not None
            rows = await db.active_requests_for_guild(2)
            assert [row["id"] for row in rows] == [request_id]
            assert await db.cancel_orphan_request(request_id) is True
            assert await db.active_requests_for_guild(2) == []
        finally:
            await db.close()

    asyncio.run(scenario())


def test_step_guidance_covers_every_training_step():
    for key, formation in FORMATIONS.items():
        assert key in STEP_RESOURCES
        assert len(STEP_RESOURCES[key]) == len(formation["steps"])
        for progress, step in enumerate(formation["steps"]):
            guidance = next_step_guidance(key, progress)
            assert guidance is not None
            assert guidance[0] == step
            assert format_guidance(key, progress)
        assert next_step_guidance(key, len(formation["steps"])) is None

    assert next_step_guidance("community_help", 0) is None
