import asyncio

from aidebot.cogs.member_experience import _learning_overview
from aidebot.lessons import LESSON_PATHS, path_size


class FakeGuild:
    id = 1


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    async def learning_progress(self, guild_id, user_id):
        assert guild_id == 1
        assert user_id == 42
        return self.rows


class FakeBot:
    def __init__(self, rows):
        self.db = FakeDB(rows)


def test_learning_overview_starts_first_path():
    async def scenario():
        validated, total, action = await _learning_overview(FakeBot([]), FakeGuild(), 42)
        assert validated == 0
        assert total == len(LESSON_PATHS)
        first_key = next(iter(LESSON_PATHS))
        assert f"sujet:{first_key}" in action
        assert "numero:1" in action

    asyncio.run(scenario())


def test_learning_overview_counts_validated_and_resumes_partial():
    async def scenario():
        keys = list(LESSON_PATHS)
        first, second = keys[0], keys[1]
        rows = [
            {"path_key": first, "max_lesson": path_size(first), "quiz_correct": 1},
            {"path_key": second, "max_lesson": 1, "quiz_correct": 0},
        ]
        validated, total, action = await _learning_overview(FakeBot(rows), FakeGuild(), 42)
        assert validated == 1
        assert total == len(LESSON_PATHS)
        assert "Reprends" in action
        assert "/apprendre reprendre" in action

    asyncio.run(scenario())


def test_learning_overview_all_validated():
    async def scenario():
        rows = [
            {"path_key": key, "max_lesson": path_size(key), "quiz_correct": 1}
            for key in LESSON_PATHS
        ]
        validated, total, action = await _learning_overview(FakeBot(rows), FakeGuild(), 42)
        assert validated == total == len(LESSON_PATHS)
        assert "/challenge liste" in action

    asyncio.run(scenario())
