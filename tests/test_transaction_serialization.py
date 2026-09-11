import asyncio

from aidebot.integrity_db import IntegrityDatabase


def test_parallel_request_creation_keeps_one_active_request(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            async def create():
                return await db.create_request_guarded(
                    guild_id=1,
                    user_id=10,
                    training_key="discord",
                    total_steps=3,
                    status="open",
                    payment_status="not_required",
                    invite_used=False,
                )

            first, second = await asyncio.gather(create(), create())
            results = [first, second]
            assert sum(1 for request_id, _ in results if request_id is not None) == 1
            assert sum(1 for request_id, existing in results if request_id is None and existing is not None) == 1
        finally:
            await db.close()

    asyncio.run(scenario())


def test_parallel_credit_consumption_spends_only_one_credit(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            await db.add_invite_credit(1, 10, 1)
            results = await asyncio.gather(
                db.consume_invite_credit(1, 10),
                db.consume_invite_credit(1, 10),
            )
            assert sorted(results) == [False, True]
            assert await db.invite_credits(1, 10) == 0
        finally:
            await db.close()

    asyncio.run(scenario())


def test_parallel_mentorship_creation_keeps_one_active_request(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            results = await asyncio.gather(
                db.create_mentorship(1, 10, "permissions"),
                db.create_mentorship(1, 10, "discord"),
            )
            assert sum(value is not None for value in results) == 1
            cur = await db._db().execute(
                "SELECT COUNT(*) AS n FROM mentorships WHERE guild_id=1 AND student_id=10 AND status IN ('open','active')"
            )
            row = await cur.fetchone()
            assert int(row["n"]) == 1
        finally:
            await db.close()

    asyncio.run(scenario())
