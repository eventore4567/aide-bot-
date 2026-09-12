import discord

from aidebot.cogs.experience_v43 import SUPPORT_TYPES
from aidebot.cogs.experience_v44 import (
    DashboardView,
    SmartSupportView,
    SUPPORT_PREFLIGHT,
    dashboard_embed,
    premium_compare_embed,
    support_preflight_embed,
)
from aidebot.cogs.ticket_polish_v44 import ticket_card


def test_v44_dashboard_is_product_like_and_within_component_limit():
    embed = dashboard_embed(500)
    text = (embed.description or "").casefold()
    assert "un seul point d’entrée" in text
    assert "diagnostiquer" in text
    assert embed.image.url

    view = DashboardView(object())
    assert view.timeout is None
    assert len(view.children) <= 25
    assert any(isinstance(item, discord.ui.Select) for item in view.children)
    labels = {getattr(item, "label", None) for item in view.children}
    assert {"Formations", "Support intelligent", "Vidéos", "Mon espace", "Premium"}.issubset(labels)


def test_every_support_type_has_a_real_preflight():
    assert set(SUPPORT_PREFLIGHT) == set(SUPPORT_TYPES)
    for key, data in SUPPORT_PREFLIGHT.items():
        assert len(data["checks"]) >= 4
        embed = support_preflight_embed(key)
        assert "diagnostic" in (embed.title or "").casefold() or key == "other"
        assert any(field.name == "Checklist avant ticket" for field in embed.fields)
        assert embed.image.url


def test_smart_support_is_persistent_and_small():
    view = SmartSupportView(object())
    assert view.timeout is None
    assert len(view.children) <= 5
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
    assert len(selects) == 1
    assert len(selects[0].options) == len(SUPPORT_TYPES)


def test_premium_compare_keeps_free_useful_and_shop_only_purchase():
    embed = premium_compare_embed(750)
    text = ((embed.description or "") + "\n" + "\n".join(field.value for field in embed.fields)).casefold()
    assert "le gratuit reste utilisable" in text
    assert "🛒・shop" in text
    assert "/buy" in text
    assert "750 robux" in "\n".join(field.name for field in embed.fields).casefold()


def test_ticket_card_is_a_single_clear_summary():
    req = {
        "id": 42,
        "user_id": 123,
        "training_key": "community_help",
        "objective": "Le bot ne peut pas attribuer mon rôle Membre.",
        "level": "Débutant",
        "availability": "Ce soir",
        "budget": "Aide gratuite",
        "status": "open",
        "payment_status": "not_required",
        "trainer_id": None,
        "progress": 0,
        "total_steps": 1,
    }
    embed = ticket_card(req)
    assert embed.title == "Ticket #42 — Aide gratuite"
    names = {field.name for field in embed.fields}
    assert {"Ta demande", "Contexte", "Suivi", "Ce qui se passe maintenant", "Sécurité"}.issubset(names)
    all_text = "\n".join(str(field.value) for field in embed.fields).casefold()
    assert "un seul" in all_text
    assert "token" in all_text
