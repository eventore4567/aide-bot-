import discord

from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT
from aidebot.catalog import CHALLENGES
from aidebot.cogs.enterprise_academy_v61 import (
    ACADEMY_TITLE,
    AcademyCoachModalV61,
    AcademyHomeViewV61,
    ChallengeActionViewV61,
    academy_home_embed,
    certification_catalog_embed,
    resources_embed,
    staff_enterprise_embed,
)
from aidebot.enterprise_catalog import (
    CERTIFICATIONS,
    CHALLENGE_LIBRARY,
    LEARNING_RESOURCES,
    challenge_categories,
    resources_for,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyBot:
    def get_cog(self, _name):
        return None


class DummyCog:
    bot = DummyBot()


def _channels():
    return [name for _category, names in CATEGORY_SPECS for name in names]


def test_v61_is_preserved_before_v62_without_extra_public_slash_commands():
    assert "aidebot.cogs.enterprise_academy_v61" in EXTENSIONS
    assert EXTENSIONS[-1] == "aidebot.cogs.simple_help_v62"
    assert EXTENSIONS.index("aidebot.cogs.simple_help_v62") > EXTENSIONS.index("aidebot.cogs.enterprise_academy_v61")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
    assert PERMANENT_CHANNEL_COUNT == 15
    assert _channels().count("🎓・formations") == 1


def test_v61_academy_is_one_compact_menu_with_distinct_jobs():
    view = AcademyHomeViewV61(DummyCog())
    assert len(view.children) == 1
    select = view.children[0]
    assert isinstance(select, discord.ui.Select)
    assert len(select.options) == 7
    labels = [option.label for option in select.options]
    assert len(labels) == len(set(labels))
    assert labels == [
        "Parcours & formations",
        "Ressources FR",
        "Resources EN",
        "Practice Lab — Challenges",
        "Academy AI Coach",
        "Certifications",
        "Ma progression",
    ]
    embed = academy_home_embed()
    assert embed.title == ACADEMY_TITLE
    text = " ".join(field.name + " " + field.value for field in embed.fields)
    assert "bilingue" in text.casefold()
    assert "Practice Lab" in text
    assert "AI Coach" in text


def test_v61_resource_library_is_large_bilingual_and_linked():
    assert len(LEARNING_RESOURCES) >= 24
    fr = resources_for("fr")
    en = resources_for("en")
    assert len(fr) >= 10
    assert len(en) >= 10
    assert {item["type"] for item in LEARNING_RESOURCES} == {"docs", "video"}
    assert all(item["url"].startswith("https://") for item in LEARNING_RESOURCES)
    assert all(item["title"] and item["note"] and item["category"] for item in LEARNING_RESOURCES)
    assert any("youtube.com/results?search_query=" in item["url"] for item in fr)
    assert any("youtube.com/results?search_query=" in item["url"] for item in en)
    assert any("discord.com/developers/docs" in item["url"] for item in en)
    assert any("docs.python.org/fr" in item["url"] for item in fr)
    assert resources_embed("fr").fields
    assert resources_embed("en").fields


def test_v61_challenge_library_is_substantial_and_quality_gated():
    assert len(CHALLENGE_LIBRARY) >= 24
    assert len(challenge_categories()) >= 8
    assert set(CHALLENGE_LIBRARY).issubset(CHALLENGES)
    for key, data in CHALLENGE_LIBRARY.items():
        assert key
        assert data["title"]
        assert data["description"]
        assert data["category"]
        assert data["difficulty"] in {"Débutant", "Intermédiaire", "Avancé"}
        assert len(data["criteria"]) >= 3
        assert int(data["reward"]) > 0
        assert data["estimated"]


def test_v61_challenge_actions_are_proof_plus_coaching_not_button_wall():
    view = ChallengeActionViewV61(DummyCog(), next(iter(CHALLENGE_LIBRARY)))
    labels = [item.label for item in view.children if isinstance(item, discord.ui.Button)]
    assert labels == ["Envoyer ma preuve", "Indice IA"]
    modal = AcademyCoachModalV61(DummyCog())
    assert len(modal.children) == 2


def test_v61_certifications_are_backed_by_real_challenges():
    assert len(CERTIFICATIONS) >= 5
    all_keys = set(CHALLENGE_LIBRARY)
    for data in CERTIFICATIONS.values():
        required = set(data["challenges"])
        assert required
        assert required.issubset(all_keys)
        assert data["title"] and data["description"] and data["level"]
    embed = certification_catalog_embed()
    assert len(embed.fields) == len(CERTIFICATIONS)


def test_v61_staff_panel_keeps_existing_tools_and_adds_academy_quality_control():
    embed = staff_enterprise_embed()
    assert embed.title == "Aide Bot — Outils avancés"
    text = " ".join(field.name + " " + field.value for field in embed.fields)
    assert "Audit 360" in text
    assert "Branding Studio" in text
    assert "Role Studio" in text
    assert "Academy QA" in text
