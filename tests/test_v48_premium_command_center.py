from types import SimpleNamespace

import discord

from aidebot.cogs.premium_service_v47 import PREMIUM_SERVICE_FORMS, SERVER_TEMPLATES
from aidebot.cogs.premium_service_v48 import (
    CONFIRM_WORD,
    PremiumHubV48View,
    ServerBuildV48TicketView,
    ShopV48View,
    _score_security,
    premium_shop_embed,
    premium_v48_hub_embed,
    server_templates_v48_embed,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyBot:
    settings = SimpleNamespace(vip_price_robux=2000)

    def get_cog(self, _name):
        return None


def test_v48_premium_is_presented_as_a_real_service_center():
    embed = premium_v48_hub_embed(2000)
    text = ((embed.description or "") + "\n" + "\n".join(field.value for field in embed.fields)).casefold()
    assert "2000 robux" in text
    assert "diagnostic" in text
    assert "audit" in text
    assert "rapport" in text
    assert "8 modèles" in text
    assert len(PREMIUM_SERVICE_FORMS) >= 10


def test_v48_adds_more_server_templates():
    assert {"community", "gaming", "shop", "creator", "support", "academy", "esport", "project"}.issubset(SERVER_TEMPLATES)
    assert len(SERVER_TEMPLATES) >= 8
    for key in ("academy", "esport", "project"):
        data = SERVER_TEMPLATES[key]
        assert len(data["categories"]) >= 5
        assert sum(len(channels) for _category, channels in data["categories"]) >= 10

    embed = server_templates_v48_embed()
    assert "8 modèles" in (embed.description or "").casefold()


def test_v48_security_score_penalizes_dangerous_everyone_permissions():
    safe_score, safe_risks = _score_security(
        everyone_administrator=False,
        everyone_manage_guild=False,
        everyone_manage_roles=False,
        everyone_manage_channels=False,
        everyone_manage_webhooks=False,
        everyone_mention_everyone=False,
        admin_role_count=2,
        dangerous_role_count=4,
        verification_value=2,
        content_filter_value=2,
    )
    risky_score, risky_risks = _score_security(
        everyone_administrator=True,
        everyone_manage_guild=True,
        everyone_manage_roles=True,
        everyone_manage_channels=True,
        everyone_manage_webhooks=True,
        everyone_mention_everyone=True,
        admin_role_count=8,
        dangerous_role_count=12,
        verification_value=0,
        content_filter_value=0,
    )
    assert safe_score == 100
    assert safe_risks == ()
    assert risky_score < 25
    assert len(risky_risks) >= 8


def test_v48_server_builder_has_preflight_and_explicit_confirmation():
    view = ServerBuildV48TicketView(DummyBot())
    labels = {getattr(item, "label", None) for item in view.children}
    assert {"Autoriser Aide Bot", "Pré-vérifier", "Voir le plan", "Construire mon serveur"}.issubset(labels)
    assert CONFIRM_WORD == "CONSTRUIRE"


def test_v48_shop_exposes_value_before_purchase():
    embed = premium_shop_embed(2000)
    text = ((embed.description or "") + "\n" + "\n".join(field.value for field in embed.fields)).casefold()
    assert "2000 robux" in text
    assert "audit" in text
    assert "construction" in text
    assert "suivi" in text

    view = ShopV48View(DummyBot())
    labels = {getattr(item, "label", None) for item in view.children}
    assert "Acheter Premium" in labels
    assert "Commander un serveur" in labels
    assert "Voir tout le pack" in labels
    assert "Audit Premium" in labels


def test_v48_hub_has_services_audit_videos_and_member_space():
    view = PremiumHubV48View(DummyBot())
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
    buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
    assert len(selects) == 1
    assert len(selects[0].options) >= 11
    labels = {button.label for button in buttons}
    assert {"Créer mon serveur", "Audit instantané", "Vidéos VIP", "Mon espace", "Statut VIP"}.issubset(labels)


def test_v48_replaces_v47_runtime_without_expanding_slash_surface():
    assert "aidebot.cogs.premium_service_v48" in EXTENSIONS
    assert "aidebot.cogs.premium_service_v47" not in EXTENSIONS
    assert "aidebot.cogs.premium_service_v47_runtime" not in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.premium_service_v48") > EXTENSIONS.index("aidebot.cogs.ticket_experience")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
