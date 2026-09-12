from types import SimpleNamespace

from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT
from aidebot.cogs.center_autopost import CENTER_CHANNEL
from aidebot.public_panels import (
    SHOP_TITLE,
    TICKET_TITLE,
    VIDEOS_TITLE,
    WELCOME_TITLE,
    shop_embed,
    ticket_embed,
    videos_panel_embed,
    welcome_embed,
)
from main import PUBLIC_SLASH_COMMANDS, prune_public_slash_commands


def _channel_names() -> list[str]:
    return [channel for _category, channels in CATEGORY_SPECS for channel in channels]


def _assert_embed_safe(embed) -> None:
    assert embed.title is None or len(embed.title) <= 256
    assert embed.description is None or len(embed.description) <= 4096
    assert len(embed.fields) <= 25
    for field in embed.fields:
        assert len(field.name) <= 256
        assert len(field.value) <= 1024


def test_panel_first_server_structure_is_compact_and_distinct():
    channels = _channel_names()
    assert PERMANENT_CHANNEL_COUNT <= 14
    assert len(channels) == len(set(channels))
    assert "👋・bienvenue" in channels
    assert "🎓・centre-aide" in channels
    assert "🎓・formations" in channels
    assert "🤝・entraide" in channels
    assert "📌・solutions" in channels
    assert "🛒・shop" in channels
    assert "💎・espace-premium" in channels
    for obsolete in ("🆘・aide-rapide", "🤖・assistant-aide", "📚・guides", "🎫・ouvrir-ticket", "🎬・videos-premium"):
        assert obsolete not in channels
    assert CENTER_CHANNEL == "🎓・centre-aide"
    assert CENTER_CHANNEL != "👋・bienvenue"
    assert CENTER_CHANNEL != "🎓・formations"


def test_welcome_is_not_a_training_panel_anymore():
    welcome = welcome_embed()
    text = (welcome.description or "").casefold()
    assert welcome.title == WELCOME_TITLE
    assert "sert uniquement à t’accueillir" in text
    assert "🎓・formations" in (welcome.description or "")
    assert welcome.title != "Aide Bot — Centre d’aide & formations"
    assert welcome.title != "Aide Bot — Formations"


def test_public_panels_are_distinct_and_discord_safe():
    embeds = [
        welcome_embed(),
        shop_embed(500),
        ticket_embed(),
        videos_panel_embed(),
    ]
    assert [item.title for item in embeds] == [WELCOME_TITLE, SHOP_TITLE, TICKET_TITLE, VIDEOS_TITLE]
    assert len({item.title for item in embeds}) == len(embeds)
    for item in embeds:
        _assert_embed_safe(item)
        assert item.image.url


def test_only_setup_and_buy_are_public_slash_commands():
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}


def test_pruner_handles_groups_without_type_attribute():
    class FakeTree:
        def __init__(self):
            self.commands = [
                SimpleNamespace(name="setup", type="slash"),
                SimpleNamespace(name="buy", type="slash"),
                SimpleNamespace(name="formation"),
                SimpleNamespace(name="sante", type="slash"),
            ]
            self.removed = []

        def get_commands(self):
            return list(self.commands)

        def remove_command(self, name, **kwargs):
            self.removed.append((name, kwargs))

    tree = FakeTree()
    prune_public_slash_commands(tree)
    assert ("formation", {}) in tree.removed
    assert ("sante", {"type": "slash"}) in tree.removed
    assert all(name not in {"setup", "buy"} for name, _kwargs in tree.removed)
