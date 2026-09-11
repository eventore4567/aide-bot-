import asyncio

from aidebot.integrity_db import IntegrityDatabase
from aidebot.reminder_schedule import schedule_reminder_atomic


PARALLEL = 40


def test_stress_parallel_request_creation_keeps_single_active_row(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "requests.db"))
        await db.connect()
        try:
            async def create_one():
                return await db.create_request_guarded(
                    guild_id=1,
                    user_id=10,
                    training_key="discord",
                    status="open",
                    payment_status="not_required",
                    total_steps=4,
                    invite_used=False,
                )

            results = await asyncio.gather(*(create_one() for _ in range(PARALLEL)))
            assert sum(request_id is not None for request_id, _ in results) == 1
            assert sum(request_id is None and existing is not None for request_id, existing in results) == PARALLEL - 1

            cur = await db._db().execute(
                """SELECT COUNT(*) AS n FROM requests
                   WHERE guild_id=1 AND user_id=10 AND training_key='discord'
                     AND status IN ('open','assigned','in_progress','payment_pending')"""
            )
            row = await cur.fetchone()
            assert int(row["n"]) == 1
        finally:
            await db.close()

    asyncio.run(scenario())


def test_stress_parallel_credit_consumption_never_overspends(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "credits.db"))
        await db.connect()
        try:
            available = 17
            await db.add_invite_credit(1, 10, available)
            results = await asyncio.gather(*(db.consume_invite_credit(1, 10) for _ in range(PARALLEL * 2)))
            assert sum(bool(result) for result in results) == available
            assert await db.invite_credits(1, 10) == 0
        finally:
            await db.close()

    asyncio.run(scenario())


def test_stress_parallel_completion_rewards_trainer_once(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "completion.db"))
        await db.connect()
        try:
            request_id = await db.create_request(
                guild_id=1,
                user_id=10,
                training_key="discord",
                status="open",
                payment_status="not_required",
                total_steps=5,
                invite_used=False,
            )
            await db.update_request(request_id, trainer_id=99, status="in_progress", progress=3)
            reminder = await schedule_reminder_atomic(
                db,
                guild_id=1,
                request_id=request_id,
                channel_id=200,
                user_id=10,
                trainer_id=99,
                remind_at=9999999999,
            )
            assert reminder.reminder_id is not None

            results = await asyncio.gather(*(db.complete_request_once(request_id) for _ in range(PARALLEL)))
            assert sum(result is not None for result in results) == 1

            req = await db.request_by_id(request_id)
            assert req is not None
            assert req["status"] == "completed"
            assert int(req["progress"]) == int(req["total_steps"])

            profile = await db.profile(1, 99)
            assert int(profile["reputation"]) == 50
            assert int(profile["trainings_completed"]) == 1

            cur = await db._db().execute(
                "SELECT COUNT(*) AS n FROM reminders WHERE request_id=? AND state='pending'",
                (request_id,),
            )
            row = await cur.fetchone()
            assert int(row["n"]) == 0
        finally:
            await db.close()

    asyncio.run(scenario())


def test_stress_parallel_application_acceptance_has_single_winner(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "applications.db"))
        await db.connect()
        try:
            application_id = await db.create_application(1, 10, "helper", "exp", "permissions", "soir")
            assert application_id is not None

            results = await asyncio.gather(
                *(db.begin_application_acceptance(application_id, 1, 1000 + index, "ok") for index in range(PARALLEL))
            )
            assert sum(result is not None for result in results) == 1

            row = await db.application(application_id)
            assert row is not None
            assert row["status"] == "processing"
            assert await db.finish_application_acceptance(application_id, 1) is True
            assert await db.finish_application_acceptance(application_id, 1) is False
        finally:
            await db.close()

    asyncio.run(scenario())


def test_stress_parallel_payment_decision_has_single_terminal_winner(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "payments.db"))
        await db.connect()
        try:
            request_id = await db.create_request(
                guild_id=1,
                user_id=10,
                training_key="vip",
                status="payment_pending",
                payment_status="pending",
                total_steps=3,
                invite_used=False,
            )
            targets = ["paid" if index % 2 == 0 else "refused" for index in range(PARALLEL)]
            results = await asyncio.gather(*(db.transition_payment(request_id, target) for target in targets))

            req = await db.request_by_id(request_id)
            assert req is not None
            assert req["payment_status"] in {"paid", "refused"}
            winner = str(req["payment_status"])
            assert any(changed and previous == "pending" for changed, previous in results)
            assert all(
                not changed or previous in {"pending", winner}
                for changed, previous in results
            )
        finally:
            await db.close()

    asyncio.run(scenario())


def test_stress_parallel_reminder_replacement_leaves_one_pending(tmp_path):
    async def scenario() -> None:
        db = IntegrityDatabase(str(tmp_path / "reminders.db"))
        await db.connect()
        try:
            request_id = await db.create_request(
                guild_id=1,
                user_id=10,
                training_key="discord",
                status="open",
                payment_status="not_required",
                total_steps=3,
                invite_used=False,
            )

            results = await asyncio.gather(
                *(
                    schedule_reminder_atomic(
                        db,
                        guild_id=1,
                        request_id=request_id,
                        channel_id=200,
                        user_id=10,
                        trainer_id=99,
                        remind_at=1000 + index,
                    )
                    for index in range(PARALLEL)
                )
            )
            assert all(result.reminder_id is not None for result in results)

            cur = await db._db().execute(
                "SELECT id,remind_at FROM reminders WHERE request_id=? AND state='pending'",
                (request_id,),
            )
            pending = list(await cur.fetchall())
            assert len(pending) == 1

            req = await db.request_by_id(request_id)
            assert req is not None
            assert req["scheduled_for"] == f"<t:{int(pending[0]['remind_at'])}:F>"
        finally:
            await db.close()

    asyncio.run(scenario())
