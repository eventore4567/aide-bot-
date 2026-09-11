import asyncio

from aidebot.app_db import AideBotDatabase
from aidebot.payments import can_transition_payment, request_status_after_payment


def test_payment_transition_rules():
    assert can_transition_payment("pending", "paid") is True
    assert can_transition_payment("pending", "refused") is True
    assert can_transition_payment("paid", "refunded") is True
    assert can_transition_payment("paid", "pending") is False
    assert can_transition_payment("refunded", "paid") is False
    assert request_status_after_payment("completed", "refunded") == "completed"
    assert request_status_after_payment("closed", "refunded") == "closed"
    assert request_status_after_payment("payment_pending", "paid") == "open"


def test_atomic_payment_transitions_and_free_ticket_protection(tmp_path):
    async def scenario():
        db = AideBotDatabase(str(tmp_path / "payments.db"))
        await db.connect()
        try:
            vip = await db.create_request(
                guild_id=1,
                user_id=10,
                training_key="vip",
                status="payment_pending",
                payment_status="pending",
                invite_used=False,
                total_steps=5,
            )
            changed, previous = await db.transition_payment(vip, "paid")
            assert changed is True
            assert previous == "pending"
            row = await db.request_by_id(vip)
            assert row["payment_status"] == "paid"
            assert row["status"] == "open"

            # Idempotent confirmation: no second state mutation.
            changed, previous = await db.transition_payment(vip, "paid")
            assert changed is True
            assert previous == "paid"

            # A paid transaction cannot silently regress to pending.
            changed, previous = await db.transition_payment(vip, "pending")
            assert changed is False
            assert previous == "paid"

            await db.update_request(vip, status="completed")
            changed, previous = await db.transition_payment(vip, "refunded")
            assert changed is True
            assert previous == "paid"
            row = await db.request_by_id(vip)
            assert row["payment_status"] == "refunded"
            assert row["status"] == "completed"

            free = await db.create_request(
                guild_id=1,
                user_id=11,
                training_key="discord",
                status="open",
                payment_status="not_required",
                invite_used=True,
                total_steps=6,
            )
            changed, previous = await db.transition_payment(free, "paid")
            assert changed is False
            assert previous == "not_required"
            row = await db.request_by_id(free)
            assert row["payment_status"] == "not_required"
            assert row["status"] == "open"
        finally:
            await db.close()

    asyncio.run(scenario())
