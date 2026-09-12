import discord

from aidebot.cogs.center import CenterView, center_embed
from aidebot.cogs.experience_v43 import (
    SUPPORT_TYPES,
    VIDEO_CATEGORIES,
    TicketPortalView,
    VideoLibraryView,
    video_category_embed,
    video_home_embed,
)
from aidebot.public_panels import ticket_embed, welcome_embed


class DummyBot:
    settings = type("Settings", (), {"vip_price_robux": 100})()

    def get_cog(self, _name):
        return None


class DummyCenterCog:
    bot = DummyBot()


def test_v43_welcome_is_short_and_action_oriented():
    embed = welcome_embed()
    text = (embed.description or "").casefold()
    assert "sert uniquement à t’accueillir" in text
    assert "formations" in text
    assert "ouvrir-ticket" in text
    assert "shop" in text
    assert embed.image.url


def test_v44_center_is_dashboard_first_with_smart_navigation():
    embed = center_embed(100)
    assert "tableau de bord" in (embed.title or "").casefold()
    view = CenterView(DummyCenterCog())
    buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
    assert len(buttons) == 5
    assert len(selects) == 1
    labels = {button.label for button in buttons}
    assert {"Formations", "Support intelligent", "Vidéos", "Mon espace", "Premium"}.issubset(labels)


def test_v43_ticket_portal_triages_before_opening_ticket():
    embed = ticket_embed()
    assert "choisis d’abord le type de problème" in (embed.description or "").casefold()
    view = TicketPortalView(DummyBot())
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]
    assert len(selects) == 1
    assert len(selects[0].options) == len(SUPPORT_TYPES)
    assert len(SUPPORT_TYPES) >= 5


def test_v43_video_library_is_categorized_not_twenty_buttons():
    embed = video_home_embed()
    assert "catégorie" in (embed.description or "").casefold()
    view = VideoLibraryView()
    assert len(view.children) == 1
    select = view.children[0]
    assert isinstance(select, discord.ui.Select)
    assert len(select.options) == len(VIDEO_CATEGORIES)
    assert len(VIDEO_CATEGORIES) >= 5
    for key in VIDEO_CATEGORIES:
        category = video_category_embed(key)
        assert category.title
        assert len(category.fields) <= 5
