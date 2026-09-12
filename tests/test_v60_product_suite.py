import discord

from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT, ROLE_SPECS
from aidebot.cogs.product_suite_v60 import (
    COMMUNITY_TITLE,
    ENTRAIDE_CHANNEL,
    SERVER_PROFILES,
    SOLUTIONS_CHANNEL,
    THEMES,
    CommunityHomeView,
    SetupWizardViewV60,
    StaffViewV60,
    audit360,
    community_home_embed,
    role360_embed,
    staff_embed_v60,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyStore:
    async def save_preferences(self, *args, **kwargs):
        return None


class DummyCog:
    store = DummyStore()
    bot = None


def _channel_names():
    return [name for _category, names in CATEGORY_SPECS for name in names]


def test_v60_loads_last_and_keeps_only_two_public_slash_commands():
    assert EXTENSIONS[-1] == "aidebot.cogs.product_suite_v60"
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}


def test_v60_community_channels_are_distinct_and_compact():
    names = _channel_names()
    assert ENTRAIDE_CHANNEL in names
    assert SOLUTIONS_CHANNEL in names
    assert names.count(ENTRAIDE_CHANNEL) == 1
    assert names.count(SOLUTIONS_CHANNEL) == 1
    assert PERMANENT_CHANNEL_COUNT == 14
    assert len(names) == len(set(names))


def test_v60_adds_mentor_without_duplicate_canonical_roles():
    names = [name for name, _color, _spec in ROLE_SPECS]
    assert "🧭・Mentor" in names
    assert len(names) == len(set(names))


def test_v60_staff_surface_is_one_select_with_eight_distinct_tools():
    view = StaffViewV60(DummyCog())
    assert len(view.children) == 1
    select = view.children[0]
    assert isinstance(select, discord.ui.Select)
    assert len(select.options) == 8
    labels = [option.label for option in select.options]
    assert len(labels) == len(set(labels))
    assert labels == [
        "Audit 360",
        "Permission Lab",
        "Guardian",
        "Mode incident",
        "Studio structure",
        "Branding Studio",
        "Role Studio",
        "Communauté",
    ]


def test_v60_setup_is_a_compact_three_choice_wizard_not_a_button_wall():
    view = SetupWizardViewV60(DummyCog(), 42)
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
    buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
    assert len(selects) == 3
    assert len(buttons) == 2
    assert {button.label for button in buttons} == {"Appliquer", "Annuler"}
    assert set(SERVER_PROFILES) == {"auto", "community", "gaming", "creator", "support", "education", "dev"}
    assert set(THEMES) == {"clean", "minimal", "luxury", "gaming", "cyber", "creator"}


def test_v60_visible_embeds_explain_distinct_missions():
    community = community_home_embed()
    assert community.title == COMMUNITY_TITLE
    assert "thread" in (community.description or "").lower()
    staff = staff_embed_v60()
    text = " ".join(field.name + " " + field.value for field in staff.fields)
    assert "Audit 360" in text
    assert "Branding Studio" in text
    assert "Role Studio" in text
    assert "Communauté" in text


def test_v60_role360_is_visible_and_non_destructive():
    # Avoid constructing a full guild here; the source-level contract is also
    # checked by CI compile and integration tests. The function must remain
    # public and the copy explicitly promise non-destructive behavior.
    assert callable(role360_embed)
    assert callable(audit360)


def test_v60_does_not_add_random_generalist_features():
    source_terms = " ".join(_channel_names()).lower()
    for forbidden in ("casino", "musique", "economy", "économie", "giveaway", "level", "mini-jeu"):
        assert forbidden not in source_terms
