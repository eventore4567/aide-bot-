import asyncio

from aidebot.integrity_db import IntegrityDatabase
from aidebot.request_integrity import cancel_request_atomic, create_request_with_entitlement_atomic


def test_classic_training_consumes_credit_with_request(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            await db.add_invite_credit(1, 10, 1)
            result = await create_request_with_entitlement_atomic(
                db,
                requires_invite=True,
                guild_id=1,
                user_id=10,
                training_key="discord",
                total_steps=3,
            )
            assert result.request_id is not None
            assert result.invite_used is True
            assert await db.invite_credits(1, 10) == 0
            row = await db.request_by_id(result.request_id)
            assert row["invite_used"] == 1
        finally:
            await db.close()

    asyncio.run(scenario())


def test_insufficient_credit_creates_no_request(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            result = await create_request_with_entitlement_atomic(
                db,
                requires_invite=True,
                guild_id=1,
                user_id=10,
                training_key="discord",
                total_steps=3,
            )
            assert result.request_id is None
            assert result.reason == "insufficient_credit"
            rows = await db.active_requests_for_user(1, 10)
            assert rows == []
        finally:
            await db.close()

    asyncio.run(scenario())


def test_duplicate_request_does_not_consume_another_credit(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            await db.add_invite_credit(1, 10, 2)
            first = await create_request_with_entitlement_atomic(
                db,
                requires_invite=True,
                guild_id=1,
                user_id=10,
                training_key="discord",
                total_steps=3,
            )
            assert first.request_id is not None
            assert await db.invite_credits(1, 10) == 1

            duplicate = await create_request_with_entitlement_atomic(
                db,
                requires_invite=True,
                guild_id=1,
                user_id=10,
                training_key="discord",
                total_steps=3,
            )
            assert duplicate.request_id is None
            assert duplicate.reason == "duplicate"
            assert duplicate.existing is not None
            assert await db.invite_credits(1, 10) == 1
        finally:
            await db.close()

    asyncio.run(scenario())


def test_cancel_and_refund_is_atomic_and_idempotent(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            await db.add_invite_credit(1, 10, 1)
            created = await create_request_with_entitlement_atomic(
                db,
                requires_invite=True,
                guild_id=1,
                user_id=10,
                training_key="discord",
                total_steps=3,
            )
            assert created.request_id is not None
            assert await db.invite_credits(1, 10) == 0

            cancelled = await cancel_request_atomic(db, created.request_id, refund_invite=True)
            assert cancelled.changed is True
            assert cancelled.refunded_invite is True
            assert await db.invite_credits(1, 10) == 1

            replay = await cancel_request_atomic(db, created.request_id, refund_invite=True)
            assert replay.changed is False
            assert replay.refunded_invite is False
            assert await db.invite_credits(1, 10) == 1
        finally:
            await db.close()

    asyncio.run(scenario())


def test_parallel_different_trainings_cannot_spend_one_credit_twice(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            await db.add_invite_credit(1, 10, 1)

            async def create(key: str):
                return await create_request_with_entitlement_atomic(
                    db,
                    requires_invite=True,
                    guild_id=1,
                    user_id=10,
                    training_key=key,
                    total_steps=3,
                )

            first, second = await asyncio.gather(create("discord"), create("serveur"))
            assert sum(result.request_id is not None for result in (first, second)) == 1
            assert sum(result.reason == "insufficient_credit" for result in (first, second)) == 1
            assert await db.invite_credits(1, 10) == 0
        finally:
            await db.close()

    asyncio.run(scenario())
