from __future__ import annotations

import os
from types import SimpleNamespace

import discord

from aidebot.config import Settings
from aidebot.cogs.premium_service_v49 import (
    ELITE_PRICE_ROBUX,
    PremiumHubV49View,
    ServerBuildV49TicketView,
    ShopV49View,
    V49_PREMIUM_SERVICES,
    V49_SERVER_TEMPLATES,
    _score_label,
    analyze_360,
    premium_shop_embed,
    premium_v49_hub_embed,
    server_templates_v49_embed,
)
from aidebot.cogs.premium_service_v48 import PREMIUM_SERVICE_FORMS, SERVER_TEMPLATES
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyBot:
    settings = SimpleNamespace(vip_price_robux=10_000)

    def get_cog(self, _name):
        return None


def _embed_text(embed: discord.Embed) -> str:
    return ((embed.description or "") + "\n" + "\n".join(f"{field.name}\n{field.value}" for field in embed.fields)).casefold()


def test_v49_price_is_10000_by_default(monkeypatch):
    monkeypatch.delenv("VIP_PRICE_ROBUX", raising=False)
    monkeypatch.setenv("DISCORD_TOKEN", "dummy")
    settings = Settings.from_env()
    assert settings.vip_price_robux == 10_000
    assert ELITE_PRICE_ROBUX == 10_000


def test_v49_shop_explains_10k_value():
    embed = premium_shop_embed(10_000)
    text = _embed_text(embed)
    assert "10 000 robux" in text
    assert "serveur sur mesure" in text
    assert "projet 360" in text
    assert "snapshot" in text
    assert "livraison" in text or "résultat" in text


def test_v49_hub_is_a_real_elite_command_center():
    embed = premium_v49_hub_embed(10_000)
    text = _embed_text(embed)
    assert "10 000 robux" in text
    assert "audit 360" in text
    assert "12 modèles" in text
    assert "15+ services" in text
    assert "dossier final" in text or "livraison" in text

    view = PremiumHubV49View(DummyBot())
    selects = [child for child in view.children if isinstance(child, discord.ui.Select)]
    buttons = [child for child in view.children if isinstance(child, discord.ui.Button)]
    assert len(selects) == 1
    assert len(selects[0].options) >= 16
    labels = {button.label for button in buttons}
    assert {"Serveur sur mesure", "Audit 360°", "Academy Elite", "Projet 360°", "Mon espace", "Statut VIP"}.issubset(labels)


def test_v49_adds_twelve_server_templates():
    assert {"marketplace", "event", "roleplay", "agency"}.issubset(V49_SERVER_TEMPLATES)
    assert len(SERVER_TEMPLATES) >= 12
    for data in V49_SERVER_TEMPLATES.values():
        assert len(data["categories"]) >= 5
        assert sum(len(channels) for _category, channels in data["categories"]) >= 10
    embed = server_templates_v49_embed()
    assert "12 modèles" in (embed.description or "").casefold()


def test_v49_adds_high_value_services():
    assert {"project-360", "migration", "branding-ux", "automation", "data-backup"}.issubset(V49_PREMIUM_SERVICES)
    assert len(PREMIUM_SERVICE_FORMS) >= 15
    assert all(len(service["questions"]) == 5 for service in V49_PREMIUM_SERVICES.values())


def test_v49_server_delivery_view_has_audit_snapshot_and_confirmation_path():
    view = ServerBuildV49TicketView(DummyBot())
    labels = {getattr(child, "label", None) for child in view.children}
    assert {"Autoriser Aide Bot", "Audit 360°", "Exporter snapshot", "Voir le plan", "Construire mon serveur"}.issubset(labels)


def test_v49_shop_keeps_purchase_and_adds_elite_entrypoints():
    view = ShopV49View(DummyBot())
    labels = {getattr(child, "label", None) for child in view.children}
    assert "Acheter Premium" in labels
    assert "Commander un serveur" in labels
    assert "Voir le pack 10K" in labels
    assert "Audit 360°" in labels


def test_v49_score_labels_are_clear():
    assert _score_label(95) == "Excellent"
    assert _score_label(80) == "Solide"
    assert _score_label(60) == "À améliorer"
    assert _score_label(30) == "Prioritaire"


def test_v49_is_compatibility_layer_while_v50_owns_runtime():
    assert "aidebot.cogs.premium_service_v50_runtime" in EXTENSIONS
    assert "aidebot.cogs.premium_service_v50" not in EXTENSIONS
    assert "aidebot.cogs.premium_service_v49" not in EXTENSIONS
    assert "aidebot.cogs.premium_service_v48" not in EXTENSIONS
    assert "aidebot.cogs.premium_service_v48_runtime" in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.premium_service_v50_runtime") > EXTENSIONS.index("aidebot.cogs.ticket_experience")
    assert EXTENSIONS.index("aidebot.cogs.premium_service_v48_runtime") > EXTENSIONS.index("aidebot.cogs.premium_service_v50_runtime")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
