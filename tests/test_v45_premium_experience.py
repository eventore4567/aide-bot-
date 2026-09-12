import discord

from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT
from aidebot.cogs.premium_v45 import (
    PREMIUM_CATEGORY,
    PREMIUM_HUB_CHANNEL,
    PREMIUM_VIDEO_CATEGORIES,
    PREMIUM_VIDEO_CHANNEL,
    PremiumHubView,
    PremiumVideoLibraryView,
    premium_hub_embed,
    premium_video_category_embed,
    premium_video_home_embed,
)
from aidebot.video_catalog import PREMIUM_VIDEO_LIBRARY


def test_v45_premium_resources_survive_v60_compact_expansion():
    categories = dict(CATEGORY_SPECS)
    assert PREMIUM_CATEGORY in categories
    assert categories[PREMIUM_CATEGORY] == [PREMIUM_HUB_CHANNEL]
    assert PREMIUM_VIDEO_CHANNEL not in categories[PREMIUM_CATEGORY]
    assert PERMANENT_CHANNEL_COUNT <= 15


def test_premium_video_library_is_large_and_search_based():
    assert len(PREMIUM_VIDEO_LIBRARY) >= 25
    for key, video in PREMIUM_VIDEO_LIBRARY.items():
        assert key.startswith("p-")
        assert video["title"]
        assert video["note"]
        assert video["url"].startswith("https://www.youtube.com/results?search_query=")


def test_every_premium_category_has_five_distinct_resources():
    all_keys = set()
    for category, data in PREMIUM_VIDEO_CATEGORIES.items():
        keys = data["keys"]
        assert len(keys) == 5
        assert len(set(keys)) == 5
        assert set(keys).issubset(PREMIUM_VIDEO_LIBRARY)
        all_keys.update(keys)
        embed = premium_video_category_embed(category)
        assert len(embed.fields) == 5
        assert embed.image.url
    assert len(all_keys) == 25


def test_premium_panels_are_product_like_and_persistent():
    hub = premium_hub_embed()
    videos = premium_video_home_embed()
    assert "25 sujets" in "\n".join(field.value for field in hub.fields)
    assert "vip" in (hub.description or "").casefold()
    assert hub.image.url and videos.image.url

    hub_view = PremiumHubView(object())
    assert hub_view.timeout is None
    labels = {getattr(item, "label", None) for item in hub_view.children}
    assert {"Vidéos Premium", "Formations avancées", "Support Premium", "Mon espace", "Statut VIP"}.issubset(labels)
    assert len(hub_view.children) <= 5

    video_view = PremiumVideoLibraryView()
    assert video_view.timeout is None
    selects = [item for item in video_view.children if isinstance(item, discord.ui.Select)]
    assert len(selects) == 1
    assert len(selects[0].options) == 5
