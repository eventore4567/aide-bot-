import discord

from aidebot.catalog import FORMATIONS
from aidebot.cogs.training_experience_v42 import (
    V42TrainingPanel,
    training_catalog_embed,
    training_preview_embed,
)
from aidebot.ux_text import missing_premium_embed
from aidebot.video_catalog import VIDEO_LIBRARY


def test_v42_catalog_explains_preview_first_flow():
    embed = training_catalog_embed()
    text = (embed.description or "").casefold()
    assert "chaque choix est réellement différent" in text
    assert "fiche complète" in text
    assert embed.image.url


def test_every_training_has_a_detailed_preview():
    for key, data in FORMATIONS.items():
        embed = training_preview_embed(key)
        assert embed.title == data["title"]
        field_names = {field.name for field in embed.fields}
        assert "En un coup d’œil" in field_names
        assert any(name.startswith("Programme") for name in field_names)
        assert "Le formulaire sera adapté à CE parcours" in field_names
        assert embed.image.url


def test_v42_training_panel_is_persistent_and_has_one_select():
    class DummyCog:
        pass

    view = V42TrainingPanel(DummyCog())
    assert view.timeout is None
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
    assert len(selects) == 1
    assert selects[0].custom_id == "aidebot:v42:training:select"
    assert len(selects[0].options) == len(FORMATIONS)


def test_video_library_is_large_but_within_discord_view_limit():
    # VideoView renders one link button per item; Discord limits a view to 25 components.
    assert len(VIDEO_LIBRARY) >= 15
    assert len(VIDEO_LIBRARY) <= 25
    assert {"developer-portal", "python", "ui", "database", "testing", "github-actions"}.issubset(VIDEO_LIBRARY)


def test_missing_premium_card_points_to_shop_without_creating_purchase():
    embed = missing_premium_embed()
    text = ((embed.description or "") + "\n" + "\n".join(field.value for field in embed.fields)).casefold()
    assert "abonnement premium requis" in (embed.title or "").casefold()
    assert "/buy" in text
    assert "seul point d’achat" in text or "seul point d'achat" in text
