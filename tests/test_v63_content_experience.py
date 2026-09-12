import discord

from aidebot.content_catalog_v63 import (
    FREE_RESOURCE_LIBRARY,
    PREMIUM_CATEGORIES,
    PREMIUM_RESOURCE_LIBRARY,
    free_resources,
    premium_resources,
)
from aidebot.cogs.content_experience_v63 import (
    PremiumCategoryViewV63,
    PremiumLanguageSelectV63,
    PremiumResourceLinksV63,
    PremiumVideoLibraryViewV63,
    academy_home_embed_v63,
    free_resources_embed_v63,
    help_hub_embed_v63,
    instant_help_embed_v63,
    premium_hub_embed_v63,
    premium_video_home_embed_v63,
    quick_setup_embed_v63,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


def test_v63_loads_last_without_new_public_slash_commands():
    assert EXTENSIONS[-1] == "aidebot.cogs.content_experience_v63"
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}


def test_free_library_is_short_docs_first_and_only_has_a_few_videos():
    assert set(FREE_RESOURCE_LIBRARY) == {"fr", "en"}
    for language in ("fr", "en"):
        resources = free_resources(language)
        assert 4 <= len(resources) <= 6
        videos = [item for item in resources if "video" in item["kind"].casefold() or "vidéo" in item["kind"].casefold()]
        docs = [item for item in resources if "doc" in item["kind"].casefold()]
        assert len(videos) <= 2
        assert len(docs) >= 3
        assert all(item["url"].startswith("https://") for item in resources)


def test_free_resource_embeds_are_clear_and_language_specific():
    fr = free_resources_embed_v63("fr")
    en = free_resources_embed_v63("en")
    assert "FR" in fr.title
    assert "EN" in en.title
    assert len(fr.fields) == len(free_resources("fr")) + 1
    assert len(en.fields) == len(free_resources("en")) + 1
    assert "quelques vidéos" in (fr.description or "")
    assert "few useful videos" in (en.description or "")


def test_premium_library_has_two_languages_five_topics_and_short_curated_sets():
    assert set(PREMIUM_RESOURCE_LIBRARY) == {"fr", "en"}
    assert len(PREMIUM_CATEGORIES) == 5
    for language in ("fr", "en"):
        assert set(PREMIUM_RESOURCE_LIBRARY[language]) == set(PREMIUM_CATEGORIES)
        for category in PREMIUM_CATEGORIES:
            resources = premium_resources(language, category)
            assert len(resources) == 4
            assert all(str(item["url"]).startswith("https://") for item in resources)


def test_premium_has_direct_verified_videos_and_explicit_recent_searches():
    all_resources = [
        item
        for language in PREMIUM_RESOURCE_LIBRARY.values()
        for resources in language.values()
        for item in resources
    ]
    direct_videos = [item for item in all_resources if item["type"] == "video" and item.get("direct")]
    searches = [item for item in all_resources if "youtube.com/results?search_query=" in str(item["url"])]
    assert direct_videos
    assert searches
    assert any("Atcxx0GdtFQ" in str(item["url"]) for item in direct_videos)
    assert any("Qb9s3UiMSTA" in str(item["url"]) for item in direct_videos)


def test_premium_navigation_starts_with_language_then_topic_not_a_button_wall():
    home = PremiumVideoLibraryViewV63()
    assert len(home.children) == 1
    language_select = home.children[0]
    assert isinstance(language_select, PremiumLanguageSelectV63)
    assert {option.value for option in language_select.options} == {"fr", "en"}

    fr_topics = PremiumCategoryViewV63("fr")
    assert len(fr_topics.children) == 1
    topic_select = fr_topics.children[0]
    assert isinstance(topic_select, discord.ui.Select)
    assert len(topic_select.options) == 5

    links = PremiumResourceLinksV63("fr", "architecture")
    assert len(links.children) == 4
    assert all(isinstance(item, discord.ui.Button) and item.url for item in links.children)


def test_v63_copy_is_shorter_and_product_like():
    setup = quick_setup_embed_v63()
    help_embed = help_hub_embed_v63()
    instant = instant_help_embed_v63(True)
    academy = academy_home_embed_v63()
    premium = premium_hub_embed_v63()
    premium_media = premium_video_home_embed_v63()

    assert "un clic" in (setup.description or "")
    assert "solution la plus simple" in (help_embed.description or "")
    assert "@Aide Bot" in (instant.description or "")
    assert "moins de liens" in (academy.footer.text or "").casefold()
    assert "FR / EN" in " ".join(field.name for field in premium.fields)
    assert "Français" in (premium_media.description or "") and "English" in (premium_media.description or "")
