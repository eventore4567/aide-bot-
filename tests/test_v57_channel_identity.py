import discord

from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT, ROLE_SPECS
from aidebot.cogs.channel_experience_v57 import (
    CHANNEL_PURPOSES,
    NOTIFICATION_ROLE,
    AnnouncementPreferenceViewV57,
    ReviewsViewV57,
    RulesAckViewV57,
    TrainingFollowupViewV57,
    announcements_embed_v57,
    followup_embed_v57,
    logs_embed_v57,
    reviews_embed_v57,
    rules_embed_v57,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyCog:
    bot = object()


def _channels() -> list[str]:
    return [name for _category, names in CATEGORY_SPECS for name in names]


def test_v57_original_channel_purposes_remain_unique_inside_v60_structure():
    channels = _channels()
    assert PERMANENT_CHANNEL_COUNT == 14
    assert set(CHANNEL_PURPOSES).issubset(set(channels))
    assert len(set(CHANNEL_PURPOSES.values())) == len(CHANNEL_PURPOSES)
    assert all(text.strip() for text in CHANNEL_PURPOSES.values())
    assert {"🤝・entraide", "📌・solutions"}.issubset(channels)


def test_v57_notification_role_remains_unique_after_v60_role_expansion():
    roles = [name for name, _color, _perms in ROLE_SPECS]
    assert NOTIFICATION_ROLE in roles
    assert len(roles) == len(set(roles))


def test_v57_unique_public_surfaces_are_not_button_walls():
    rules = RulesAckViewV57()
    announcements = AnnouncementPreferenceViewV57()
    reviews = ReviewsViewV57(DummyCog())
    followup = TrainingFollowupViewV57(DummyCog())

    assert len(rules.children) == 1
    assert len(announcements.children) == 1
    assert len(reviews.children) == 1
    assert isinstance(reviews.children[0], discord.ui.Select)
    assert len(reviews.children[0].options) == 5
    assert len(followup.children) == 1


def test_v57_copy_makes_channel_jobs_visibly_different():
    rules = rules_embed_v57()
    announcements = announcements_embed_v57()
    reviews = reviews_embed_v57()
    logs = logs_embed_v57()
    followup = followup_embed_v57()

    titles = {item.title for item in (rules, announcements, reviews, logs, followup)}
    assert len(titles) == 5
    rule_copy = " ".join(f"{field.name} {field.value}" for field in rules.fields).casefold()
    assert "validation" in rule_copy and "rôle membre" in rule_copy
    assert "notifications" in (announcements.description or "").casefold()
    assert "terminée" in (reviews.description or "").casefold()
    assert "journal" in (logs.description or "").casefold()
    assert "progression" in " ".join(field.value for field in followup.fields).casefold()


def test_v57_loads_after_v56_without_adding_slash_commands():
    assert "aidebot.cogs.experience_v56" in EXTENSIONS
    assert "aidebot.cogs.channel_experience_v57" in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.channel_experience_v57") > EXTENSIONS.index("aidebot.cogs.experience_v56")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
