from types import SimpleNamespace

import discord

from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT
from aidebot.cogs.help_system_v54 import (
    CENTER_CHANNEL,
    GUIDES_CHANNEL,
    HELP_CARDS,
    HELP_CATEGORIES,
    QUICK_CHANNEL,
    GuidesView,
    HelpHomeView,
    QuickHelpView,
    card_embed,
    classify_problem,
    guides_home_embed,
    help_home_embed,
    quick_help_embed,
)
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


def test_v54_adds_only_two_specialized_help_channels():
    categories = dict(CATEGORY_SPECS)
    help_channels = categories["━━ AIDE & FORMATIONS ━━"]
    assert CENTER_CHANNEL in help_channels
    assert QUICK_CHANNEL in help_channels
    assert GUIDES_CHANNEL in help_channels
    assert "🤖・assistant-aide" in help_channels
    assert "🎓・formations" in help_channels
    assert len(help_channels) == 5
    assert PERMANENT_CHANNEL_COUNT == 17


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


def test_v54_surfaces_have_distinct_jobs_and_few_controls():
    bot = DummyBot()
    home = HelpHomeView(bot)
    quick = QuickHelpView(bot)
    guides = GuidesView(bot)

    assert len([x for x in home.children if isinstance(x, discord.ui.Select)]) == 1
    assert _labels(home) == {"Décrire mon problème"}

    assert len([x for x in quick.children if isinstance(x, discord.ui.Select)]) == 1
    assert _labels(quick) == {"Décrire mon problème"}

    assert len([x for x in guides.children if isinstance(x, discord.ui.Select)]) == 1
    assert _labels(guides) == set()

    assert "orientation" in (help_home_embed().description or "").casefold()
    assert "symptôme" in (quick_help_embed().description or "").casefold()
    assert "bibliothèque" in (guides_home_embed().description or "").casefold()


def test_v54_removes_dashboard_runtime_and_keeps_public_commands_small():
    assert "aidebot.cogs.help_system_v54" in EXTENSIONS
    assert "aidebot.cogs.owner_console_v53" not in EXTENSIONS
    assert "aidebot.cogs.ops_dashboard" not in EXTENSIONS
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
