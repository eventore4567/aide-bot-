import asyncio

from aidebot.integrity_db import IntegrityDatabase


def test_application_acceptance_claim_is_exclusive(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            application_id = await db.create_application(1, 10, "helper", "exp", "permissions", "soir")
            assert application_id is not None

            first, second = await asyncio.gather(
                db.begin_application_acceptance(application_id, 1, 90, "ok"),
                db.begin_application_acceptance(application_id, 1, 91, "ok"),
            )
            assert sum(result is not None for result in (first, second)) == 1
            row = await db.application(application_id)
            assert row["status"] == "processing"

            assert await db.finish_application_acceptance(application_id, 1) is True
            row = await db.application(application_id)
            assert row["status"] == "accepted"
            assert await db.finish_application_acceptance(application_id, 1) is False
        finally:
            await db.close()

    asyncio.run(scenario())


def test_failed_role_grant_can_return_application_to_pending(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            application_id = await db.create_application(1, 10, "trainer", "exp", "discord", "weekend")
            assert application_id is not None
            assert await db.begin_application_acceptance(application_id, 1, 90, "test") is not None
            assert await db.release_application_acceptance(application_id, 1) is True

            row = await db.application(application_id)
            assert row["status"] == "pending"
            assert row["reviewer_id"] is None
            assert row["review_reason"] == ""
        finally:
            await db.close()

    asyncio.run(scenario())


def test_processing_application_is_recovered_after_restart(tmp_path):
    async def scenario() -> None:
        path = str(tmp_path / "aidebot-test.db")
        db = IntegrityDatabase(path)
        await db.connect()
        application_id = await db.create_application(1, 10, "helper", "exp", "permissions", "soir")
        assert application_id is not None
        assert await db.begin_application_acceptance(application_id, 1, 90, "ok") is not None
        await db.close()

        restarted = IntegrityDatabase(path)
        await restarted.connect()
        try:
            row = await restarted.application(application_id)
            assert row["status"] == "pending"
            assert row["reviewer_id"] is None
            assert row["review_reason"] == ""
        finally:
            await restarted.close()

    asyncio.run(scenario())


def test_application_acceptance_is_guild_scoped(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            application_id = await db.create_application(1, 10, "helper", "exp", "permissions", "soir")
            assert application_id is not None
            assert await db.begin_application_acceptance(application_id, 2, 90, "ok") is None
            row = await db.application(application_id)
            assert row["status"] == "pending"
        finally:
            await db.close()

    asyncio.run(scenario())
