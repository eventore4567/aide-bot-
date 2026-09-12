from types import SimpleNamespace

import discord

from aidebot.config import Settings
from aidebot.cogs import center_autopost
from aidebot.cogs.premium_service_v48 import SERVER_TEMPLATES
from aidebot.cogs.product_experience_v51 import (
    CENTER_TITLE,
    HelpCenterViewV51,
    PremiumHubViewV51,
    ShopViewV51,
    WelcomeViewV51,
    help_center_embed_v51,
    premium_hub_embed_v51,
    server_templates_embed_v51,
    shop_embed_v51,
    welcome_embed_v51,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyBot:
    settings = SimpleNamespace(vip_price_robux=2_000)

    def get_cog(self, _name):
        return None


def _embed_text(embed: discord.Embed) -> str:
    return "\n".join(
        [embed.title or "", embed.description or "", *(f"{field.name}\n{field.value}" for field in embed.fields), embed.footer.text or ""]
    ).casefold()


def _button_labels(view: discord.ui.View) -> set[str]:
    return {str(child.label) for child in view.children if isinstance(child, discord.ui.Button) and child.label}


def test_v51_restores_the_real_product_price(monkeypatch):
    monkeypatch.delenv("VIP_PRICE_ROBUX", raising=False)
    monkeypatch.setenv("DISCORD_TOKEN", "dummy")
    assert Settings.from_env().vip_price_robux == 2_000


def test_v51_shop_is_small_and_member_facing():
    embed = shop_embed_v51(2_000)
    text = _embed_text(embed)
    assert "2 000 robux" in text
    for leaked in ("10k", "10 000", "v50", "elite", "prix configuré", "direction", "oauth2"):
        assert leaked not in text

    view = ShopViewV51(DummyBot())
    assert view.timeout is None
    assert _button_labels(view) == {"Passer Premium", "Voir les avantages", "Continuer gratuitement"}


def test_v51_welcome_has_three_distinct_actions_only():
    view = WelcomeViewV51(DummyBot())
    assert view.timeout is None
    assert _button_labels(view) == {"Centre d’aide", "Formations", "Support"}
    text = _embed_text(welcome_embed_v51())
    assert "v50" not in text
    assert "10k" not in text
    assert "oauth2" not in text


def test_v51_help_center_uses_dropdown_for_breadth_and_two_actions():
    view = HelpCenterViewV51(DummyBot())
    selects = [child for child in view.children if isinstance(child, discord.ui.Select)]
    assert len(selects) == 1
    assert len(selects[0].options) >= 10
    values = {option.value for option in selects[0].options}
    assert "premium" not in values
    assert "recruitment" not in values
    assert _button_labels(view) == {"Guides", "Support"}

    text = _embed_text(help_center_embed_v51())
    for leaked in ("robux", "premium", "candidature", "v46", "v50", "elite"):
        assert leaked not in text


def test_v51_premium_hub_uses_one_service_menu_and_three_tools():
    view = PremiumHubViewV51(DummyBot())
    selects = [child for child in view.children if isinstance(child, discord.ui.Select)]
    assert len(selects) == 1
    assert 10 <= len(selects[0].options) <= 25
    assert "build-server" in {option.value for option in selects[0].options}
    assert _button_labels(view) == {"Mon projet", "Ressources", "Mon espace"}

    text = _embed_text(premium_hub_embed_v51())
    for leaked in ("10k", "10 000", "v50", "elite"):
        assert leaked not in text


def test_v51_keeps_server_builder_depth_without_a_button_wall():
    assert len(SERVER_TEMPLATES) >= 12
    embed = server_templates_embed_v51()
    assert len(embed.fields) >= 12
    text = _embed_text(embed)
    assert "ne supprime pas automatiquement" in text


def test_v51_fixes_center_autopost_title_and_owns_public_runtime():
    assert CENTER_TITLE == "Aide Bot — Centre d’aide"
    assert center_autopost.CENTER_TITLE == CENTER_TITLE
    assert "aidebot.cogs.product_experience_v51" in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.product_experience_v51") > EXTENSIONS.index("aidebot.cogs.premium_service_v48_runtime")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
