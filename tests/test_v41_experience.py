from aidebot.catalog import FORMATIONS
from aidebot.cogs.training import TRAINING_FORMS
from aidebot.premium_access import PREMIUM_ROLE_NAMES, missing_premium_message
from aidebot.video_catalog import VIDEO_LIBRARY
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


def test_training_forms_cover_every_catalog_choice_and_are_not_generic():
    assert set(TRAINING_FORMS) == set(FORMATIONS)
    signatures = []
    for key, form in TRAINING_FORMS.items():
        fields = form["fields"]
        assert len(fields) == 5
        field_keys = [field[0] for field in fields]
        assert "level" in field_keys
        assert "availability" in field_keys
        signatures.append(tuple(field[1] for field in fields))
    # Les parcours ne doivent plus tous ouvrir exactement le même formulaire.
    assert len(set(signatures)) >= 6


def test_video_library_is_expanded_and_uses_https_links():
    assert len(VIDEO_LIBRARY) >= 9
    assert {"serveur", "permissions", "bot", "webhooks", "railway", "slash", "tickets", "security", "github"} <= set(VIDEO_LIBRARY)
    assert all(video["url"].startswith("https://") for video in VIDEO_LIBRARY.values())


def test_premium_access_message_points_to_shop_and_vip_role():
    assert "💎・VIP" in PREMIUM_ROLE_NAMES
    message = missing_premium_message()
    assert "Abonnement Premium manquant" in message
    assert "🛒・shop" in message
    assert "/buy" in message


def test_recruitment_panel_is_loaded_while_slash_surface_stays_small():
    assert "aidebot.cogs.recruitment_panel" in EXTENSIONS
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
