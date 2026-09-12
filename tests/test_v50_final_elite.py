from types import SimpleNamespace

import discord

from aidebot.cogs.premium_service_v50 import (
    ELITE_PRICE_ROBUX,
    EliteDeliveryView,
    ElitePurchaseModalV50,
    PremiumHubV50View,
    ServerBuildV50TicketView,
    ShopV50View,
    elite_scope_embed,
    is_elite_key,
)
from aidebot.cogs.premium_service_v50_runtime import premium_shop_embed, premium_v50_hub_embed
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyBot:
    settings = SimpleNamespace(vip_price_robux=10_000)

    def get_cog(self, _name):
        return None


def _text(embed: discord.Embed) -> str:
    return ((embed.description or "") + "\n" + "\n".join(f"{field.name}\n{field.value}" for field in embed.fields)).casefold()


def test_v50_price_and_scope_are_explicit():
    assert ELITE_PRICE_ROBUX == 10_000
    embed = elite_scope_embed(10_000)
    text = _text(embed)
    assert "10 000 robux" in text
    assert "une mission active à la fois" in text
    assert "cahier des charges" in text
    assert "validation client" in text
    assert "oauth2" in text
    assert "construire" in text


def test_v50_purchase_requires_a_real_cahier_des_charges():
    modal = ElitePurchaseModalV50(DummyBot())
    labels = [item.label for item in modal.children]
    assert len(labels) == 5
    assert "Type de projet" in labels
    assert "Situation actuelle" in labels
    assert "Résultat principal attendu" in labels
    assert "Critères d'acceptation" in labels
    assert "Disponibilités" in labels


def test_v50_shop_is_clean_and_10k_specific():
    view = ShopV50View(DummyBot())
    labels = {getattr(item, "label", None) for item in view.children}
    assert "Acheter Elite 10K" in labels
    assert "Ce que couvre 10K" in labels
    assert "Commander un serveur" in labels
    assert "Voir le pack 10K" in labels
    assert "Audit 360°" in labels

    text = _text(premium_shop_embed(10_000))
    assert "10 000 robux" in text
    assert "cahier des charges" in text
    assert "validation client" in text


def test_v50_hub_has_project_status_and_service_standard():
    view = PremiumHubV50View(DummyBot())
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
    labels = {getattr(item, "label", None) for item in view.children if isinstance(item, discord.ui.Button)}
    assert len(selects) == 1
    assert len(selects[0].options) >= 16
    assert "Mon projet actif" in labels
    assert "Standard Elite" in labels
    assert "Serveur sur mesure" in labels
    assert "Projet 360°" in labels

    text = _text(premium_v50_hub_embed(10_000))
    assert "standard de livraison" in text
    assert "une mission" in text


def test_v50_delivery_controls_are_client_facing():
    view = EliteDeliveryView(DummyBot())
    labels = {getattr(item, "label", None) for item in view.children}
    assert labels == {"Voir les livrables", "Demander un ajustement", "Valider le résultat"}


def test_v50_server_delivery_keeps_v49_safety_and_adds_standard():
    view = ServerBuildV50TicketView(DummyBot())
    labels = {getattr(item, "label", None) for item in view.children}
    assert {"Autoriser Aide Bot", "Audit 360°", "Exporter snapshot", "Voir le plan", "Construire mon serveur", "Standard de livraison"}.issubset(labels)


def test_v50_elite_key_detection_is_strict():
    assert is_elite_key("premium_server_build")
    assert is_elite_key("premium_service_project_360")
    assert is_elite_key("premium_service_security")
    assert not is_elite_key("vip")
    assert not is_elite_key("community_help")
    assert not is_elite_key("bot-avance")


def test_v50_runtime_is_final_without_expanding_public_slash_surface():
    assert "aidebot.cogs.premium_service_v50_runtime" in EXTENSIONS
    assert "aidebot.cogs.premium_service_v50" not in EXTENSIONS
    assert "aidebot.cogs.premium_service_v49" not in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.premium_service_v50_runtime") > EXTENSIONS.index("aidebot.cogs.ticket_experience")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
