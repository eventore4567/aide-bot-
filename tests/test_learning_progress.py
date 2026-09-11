import asyncio

from aidebot.app_db import AideBotDatabase
from aidebot.cogs.self_learning import _progress_bar, _progress_status


def test_self_learning_progress_persists(tmp_path):
    async def scenario() -> None:
        path = str(tmp_path / "learning.db")
        db = AideBotDatabase(path)
        await db.connect()
        try:
            await db.mark_lesson_seen(1, 42, "discord", 1)
            await db.mark_lesson_seen(1, 42, "discord", 3)
            await db.mark_lesson_seen(1, 42, "discord", 2)
            await db.record_quiz_answer(1, 42, "discord", False)
            await db.record_quiz_answer(1, 42, "discord", True)

            row = await db.learning_progress_for_path(1, 42, "discord")
            assert row is not None
            assert row["max_lesson"] == 3
            assert row["quiz_attempts"] == 2
            assert row["quiz_correct"] == 1
        finally:
            await db.close()

        reopened = AideBotDatabase(path)
        await reopened.connect()
        try:
            rows = await reopened.learning_progress(1, 42)
            assert len(rows) == 1
            assert rows[0]["path_key"] == "discord"
            assert rows[0]["max_lesson"] == 3
            assert rows[0]["quiz_correct"] == 1
        finally:
            await reopened.close()

    asyncio.run(scenario())


def test_learning_progress_display_states():
    assert _progress_status(0, 6, 0) == "Non commencé"
    assert _progress_status(2, 6, 0) == "En cours"
    assert _progress_status(6, 6, 0) == "Quiz à valider"
    assert _progress_status(6, 6, 1) == "Validé"
    assert _progress_bar(0, 4) == "░" * 10
    assert _progress_bar(4, 4) == "█" * 10
