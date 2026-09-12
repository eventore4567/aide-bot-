from types import SimpleNamespace

import discord

from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT
from aidebot.cogs.help_system_v54 import (
    CENTER_CHANNEL,
    HELP_CARDS,
    HELP_CATEGORIES,
    card_embed,
    classify_problem,
)
from aidebot.cogs.experience_v56 import HelpHubViewV56, help_hub_embed
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyBot:
    settings = SimpleNamespace(vip_price_robux=2_000)

    def get_cog(self, _name):
        return None


def _labels(view: discord.ui.View) -> set[str]:
    return {
        str(child.label)
        for child in view.children
        if isinstance(child, discord.ui.Button) and child.label
    }


def test_v54_knowledge_engine_stays_consolidated_with_v60_community():
    categories = dict(CATEGORY_SPECS)
    help_channels = categories["━━ AIDE & FORMATIONS ━━"]
    assert help_channels == [CENTER_CHANNEL, "🎓・formations"]
    assert PERMANENT_CHANNEL_COUNT <= 14
    assert "🆘・aide-rapide" not in help_channels
    assert "🤖・assistant-aide" not in help_channels
    assert "📚・guides" not in help_channels
    assert categories["━━ COMMUNAUTÉ ━━"] == ["🤝・entraide", "📌・solutions"]


def test_v54_help_catalog_is_real_and_broad():
    assert len(HELP_CATEGORIES) == 8
    assert len(HELP_CARDS) >= 20
    for card in HELP_CARDS.values():
        assert card.category in HELP_CATEGORIES
        assert len(card.checks) >= 3
        assert len(card.fixes) >= 3
        assert card.keywords
        embed = card_embed(card)
        assert embed.title
        assert len(embed.fields) == 2


def test_v54_free_text_router_finds_common_problems():
    assert classify_problem("je vois pas le salon staff avec mon role") is not None
    assert classify_problem("mon bot est offline sur railway") is not None
    assert classify_problem("j'ai exposé mon token discord") is not None
    assert classify_problem("database is locked sqlite") is not None
    assert classify_problem("bonjour juste une question sans contexte précis") is None


def test_v56_hub_replaces_three_duplicate_help_surfaces():
    bot = DummyBot()
    home = HelpHubViewV56(bot)
    selects = [x for x in home.children if isinstance(x, discord.ui.Select)]
    assert len(selects) == 1
    assert len(selects[0].options) == 5
    assert _labels(home) == {"Décrire mon problème"}
    text = (help_hub_embed().description or "").casefold()
    assert "un seul endroit" in text
    assert "ia" in text
    assert "support" in text


def test_v56_replaces_v54_runtime_and_keeps_public_commands_small():
    assert "aidebot.cogs.help_system_v54" not in EXTENSIONS
    assert "aidebot.cogs.experience_v56" in EXTENSIONS
    assert "aidebot.cogs.owner_console_v53" not in EXTENSIONS
    assert "aidebot.cogs.ops_dashboard" not in EXTENSIONS
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
