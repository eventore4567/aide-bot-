import discord

from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT
from aidebot.cogs.product_suite_v60 import SERVER_PROFILES
from aidebot.cogs.simple_help_v62 import (
    GENERAL_CHANNEL,
    GeneralHelpViewV62,
    QuickSetupViewV62,
    instant_help_embed,
    quick_setup_embed,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyCog:
    bot = None


def _channels():
    return [name for _category, names in CATEGORY_SPECS for name in names]


def test_v62_loads_before_v63_and_keeps_public_slash_surface_small():
    assert "aidebot.cogs.simple_help_v62" in EXTENSIONS
    assert EXTENSIONS[-1] == "aidebot.cogs.content_experience_v63"
    assert EXTENSIONS.index("aidebot.cogs.content_experience_v63") > EXTENSIONS.index("aidebot.cogs.simple_help_v62")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}


def test_v62_setup_first_screen_is_three_buttons_and_zero_selects():
    view = QuickSetupViewV62(DummyCog(), 42)
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
    buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
    assert selects == []
    assert [button.label for button in buttons] == [
        "Installer automatiquement",
        "Personnaliser",
        "Vérifier",
    ]
    embed = quick_setup_embed()
    assert "3 menus" in (embed.description or "")
    assert "profil Général" in (embed.description or "")


def test_v62_adds_general_profile_and_general_channel_once():
    assert "general" in SERVER_PROFILES
    assert list(SERVER_PROFILES)[0] == "general"
    assert SERVER_PROFILES["general"][0] == "Général"
    names = _channels()
    assert names.count(GENERAL_CHANNEL) == 1
    assert PERMANENT_CHANNEL_COUNT == 15


def test_v62_general_help_surface_makes_ai_visible():
    view = GeneralHelpViewV62(None)
    labels = [item.label for item in view.children if isinstance(item, discord.ui.Button)]
    assert labels == ["J’ai besoin d’aide", "Demander à l’IA"]
    ready = instant_help_embed(True)
    text = " ".join((ready.description or "", *(field.name + " " + field.value for field in ready.fields)))
    assert "Assistant IA" in text
    assert "mentionne Aide Bot" in text
    assert "Disponible maintenant" in text
