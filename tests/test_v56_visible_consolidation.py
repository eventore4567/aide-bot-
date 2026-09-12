import discord

from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT
from aidebot.cogs.experience_v56 import (
    OBSOLETE_PANEL_CHANNELS,
    HelpHubViewV56,
    WelcomeViewV56,
    help_hub_embed,
    welcome_embed_v56,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyBot:
    def get_cog(self, _name):
        return None


def test_v56_visible_structure_stays_compact_after_v62_general_expansion():
    channels = [name for _category, names in CATEGORY_SPECS for name in names]
    assert PERMANENT_CHANNEL_COUNT == 15
    assert "🎓・centre-aide" in channels
    assert "🎓・formations" in channels
    assert "💬・général" in channels
    assert "🤝・entraide" in channels
    assert "📌・solutions" in channels
    assert "💎・espace-premium" in channels
    for name in OBSOLETE_PANEL_CHANNELS:
        assert name not in channels


def test_v56_help_hub_has_one_menu_and_one_primary_entry():
    view = HelpHubViewV56(DummyBot())
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
    buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
    assert len(selects) == 1
    assert len(selects[0].options) == 5
    assert [str(button.label) for button in buttons] == ["Décrire mon problème"]
    values = {option.value for option in selects[0].options}
    assert values == {"solution", "ai", "support", "training", "space"}


def test_v56_welcome_has_one_clear_cta():
    view = WelcomeViewV56(DummyBot())
    buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
    assert len(buttons) == 1
    assert buttons[0].label == "Commencer"
    assert "centre d’aide" in (welcome_embed_v56().description or "").casefold()


def test_v56_copy_explicitly_explains_consolidation():
    text = "\n".join(
        [
            help_hub_embed().title or "",
            help_hub_embed().description or "",
            *(field.value for field in help_hub_embed().fields),
        ]
    ).casefold()
    assert "un seul endroit" in text
    assert "solution" in text
    assert "support" in text
    assert "ia" in text


def test_v56_load_order_and_public_commands():
    assert "aidebot.cogs.experience_v56" in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.experience_v56") > EXTENSIONS.index("aidebot.cogs.setup_experience_v55")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
