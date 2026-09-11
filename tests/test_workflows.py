import asyncio

from aidebot.db import Database


def test_applications_helpers_and_reminders(tmp_path):
    async def scenario() -> None:
        db = Database(str(tmp_path / "aidebot-test.db"))
        await db.connect()
        try:
            await db.set_helper_available(1, 42, True)
            await db.add_skill(1, 42, "permissions")
            helpers = await db.available_helpers(1)
            assert [row["user_id"] for row in helpers] == [42]

            first = await db.create_application(1, 50, "helper", "6 mois", "permissions", "soir")
            assert first is not None
            duplicate = await db.create_application(1, 50, "trainer", "6 mois", "bots", "soir")
            assert duplicate is None

            app = await db.application(first)
            assert app is not None
            assert app["status"] == "pending"
            assert await db.resolve_application(first, 99, True, "Bon test") is True
            assert await db.resolve_application(first, 99, False, "double traitement") is False

            second = await db.create_application(1, 50, "trainer", "1 an", "bots", "week-end")
            assert second is not None
            pending = await db.pending_applications(1)
            assert [row["id"] for row in pending] == [second]

            request_id = await db.create_request(
                guild_id=1,
                user_id=50,
                training_key="discord",
                total_steps=6,
                status="assigned",
                payment_status="not_required",
                invite_used=False,
            )
            reminder_a = await db.create_reminder(1, request_id, 777, 50, 42, 100)
            reminder_b = await db.create_reminder(1, request_id, 777, 50, 42, 200)
            assert reminder_b > reminder_a
            assert await db.due_reminders(150) == []
            due = await db.due_reminders(250)
            assert [row["id"] for row in due] == [reminder_b]
            assert await db.finish_reminder(reminder_b, "sent") is True
            assert await db.finish_reminder(reminder_b, "sent") is False

            stats = await db.dashboard_stats(1)
            assert stats["available_helpers"] == 1
            assert stats["pending_applications"] == 1
            assert stats["pending_reminders"] == 0
        finally:
            await db.close()

    asyncio.run(scenario())
