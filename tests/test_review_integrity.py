import asyncio

from aidebot.integrity_db import IntegrityDatabase


def test_review_and_rating_counters_commit_once(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            request_id = await db.create_request(
                guild_id=1,
                user_id=10,
                training_key="discord",
                total_steps=3,
                status="open",
                payment_status="not_required",
                invite_used=False,
            )
            await db.update_request(request_id, trainer_id=99, status="completed", progress=3)

            created = await db.add_review(1, request_id, 10, 99, 5, "Très bonne formation")
            assert created is True
            trainer = await db.profile(1, 99)
            assert trainer["reviews_count"] == 1
            assert trainer["rating_sum"] == 5

            replay = await db.add_review(1, request_id, 10, 99, 4, "Deuxième avis")
            assert replay is False
            trainer = await db.profile(1, 99)
            assert trainer["reviews_count"] == 1
            assert trainer["rating_sum"] == 5
        finally:
            await db.close()

    asyncio.run(scenario())


def test_review_revalidates_request_ownership_trainer_and_state(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            request_id = await db.create_request(
                guild_id=1,
                user_id=10,
                training_key="discord",
                total_steps=3,
                status="open",
                payment_status="not_required",
                invite_used=False,
            )
            await db.update_request(request_id, trainer_id=99, status="assigned")

            assert await db.add_review(1, request_id, 10, 99, 5, "Trop tôt") is False
            await db.update_request(request_id, status="completed", progress=3)
            assert await db.add_review(1, request_id, 11, 99, 5, "Mauvais auteur") is False
            assert await db.add_review(1, request_id, 10, 98, 5, "Mauvais formateur") is False
            assert await db.add_review(2, request_id, 10, 99, 5, "Mauvais serveur") is False
            assert await db.add_review(1, request_id, 10, 99, 6, "Note invalide") is False

            trainer = await db.profile(1, 99)
            assert trainer["reviews_count"] == 0
            assert trainer["rating_sum"] == 0
        finally:
            await db.close()

    asyncio.run(scenario())
