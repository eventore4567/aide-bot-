from types import SimpleNamespace

import discord

from aidebot.cogs.premium_service_v47 import (
    DIRECT_PREMIUM_VIDEOS,
    PREMIUM_SERVICE_FORMS,
    SERVER_BUILD_KEY,
    SERVER_TEMPLATES,
    PremiumServiceHubView,
    ServerTemplateChoiceView,
    _parse_build_data,
    _server_bot_permissions,
    premium_v47_hub_embed,
    premium_v47_video_embed,
)
from aidebot.cogs.premium_service_v47_runtime import ShopV47View, premium_shop_embed
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyBot:
    settings = SimpleNamespace(vip_price_robux=2000)

    def get_cog(self, _name):
        return None


def test_v47_premium_is_a_real_service_pack():
    embed = premium_v47_hub_embed(2000)
    text = ((embed.description or "") + "\n" + "\n".join(field.value for field in embed.fields)).casefold()
    assert "2000 robux" in text
    assert "audit" in text
    assert "serveur" in text
    assert "support prioritaire" in text
    assert "oauth2" in text
    assert len(PREMIUM_SERVICE_FORMS) >= 7


def test_v47_has_five_server_templates_and_real_structure():
    assert set(SERVER_TEMPLATES) == {"community", "gaming", "shop", "creator", "support"}
    for data in SERVER_TEMPLATES.values():
        assert len(data["categories"]) >= 4
        channel_count = sum(len(channels) for _category, channels in data["categories"])
        assert channel_count >= 9

    view = ServerTemplateChoiceView(DummyBot())
    assert len(view.children) == 1
    select = view.children[0]
    assert isinstance(select, discord.ui.Select)
    assert len(select.options) == 5


def test_v47_server_build_metadata_is_parseable():
    objective = (
        "Serveur cible ID : 123456789012345678\n"
        "Modèle : gaming\n"
        "Nom souhaité : Test Gaming\n"
        "Objectif : communauté gaming\n"
        "Options : tickets + vocaux"
    )
    parsed = _parse_build_data(objective)
    assert parsed is not None
    assert parsed.target_guild_id == 123456789012345678
    assert parsed.template_key == "gaming"
    assert parsed.requested_name == "Test Gaming"
    assert parsed.purpose == "communauté gaming"


def test_v47_oauth_permissions_are_powerful_but_not_administrator():
    permissions = _server_bot_permissions()
    assert permissions.manage_channels
    assert permissions.manage_roles
    assert permissions.manage_guild
    assert permissions.send_messages
    assert not permissions.administrator


def test_v47_premium_videos_are_direct_links():
    assert len(DIRECT_PREMIUM_VIDEOS) >= 4
    for video in DIRECT_PREMIUM_VIDEOS.values():
        assert "youtube.com/watch?v=" in video["url"]
        assert "results?search_query=" not in video["url"]
    embed = premium_v47_video_embed()
    assert "vidéos directes" in (embed.description or "").casefold()


def test_v47_shop_exposes_server_order_and_full_pack():
    embed = premium_shop_embed(2000)
    text = ((embed.description or "") + "\n" + "\n".join(field.value for field in embed.fields)).casefold()
    assert "2000 robux" in text
    assert "création" in text and "serveur" in text
    view = ShopV47View(DummyBot())
    labels = {getattr(item, "label", None) for item in view.children}
    assert "Commander un serveur" in labels
    assert "Voir tout le pack" in labels
    assert "Acheter Premium" in labels


def test_v47_extension_order_and_public_commands_stay_compact():
    assert "aidebot.cogs.premium_service_v47" in EXTENSIONS
    assert "aidebot.cogs.premium_service_v47_runtime" in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.premium_service_v47_runtime") > EXTENSIONS.index("aidebot.cogs.ticket_experience")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
    assert SERVER_BUILD_KEY == "premium_server_build"


def test_v47_hub_has_many_choices_without_more_slash_commands():
    view = PremiumServiceHubView(DummyBot())
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
    assert len(selects) == 1
    assert len(selects[0].options) >= 8
