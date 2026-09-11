from aidebot.cogs.center import center_embed, guide_embed
from aidebot.experience_content import BANNER_URL, GUIDES, VIDEO_LIBRARY
from aidebot.permissions import decide


class Role:
    def __init__(self, name: str):
        self.name = name


class Guild:
    owner_id = 1


class GuildPermissions:
    def __init__(self, administrator: bool):
        self.administrator = administrator


class Member:
    def __init__(self, user_id: int, roles: list[str], administrator: bool = False):
        self.id = user_id
        self.guild = Guild()
        self.roles = [Role(name) for name in roles]
        self.guild_permissions = GuildPermissions(administrator)


def _embed_text_size(embed) -> int:
    total = len(embed.title or "") + len(embed.description or "")
    for field in embed.fields:
        total += len(field.name) + len(field.value)
    return total


def test_learning_center_has_real_long_form_guides_and_videos():
    assert len(GUIDES) >= 5
    for key, guide in GUIDES.items():
        assert len(guide["sections"]) >= 3, key
        assert all(len(text) >= 180 for _, text in guide["sections"]), key
        assert len(guide["example"]) >= 80, key
        assert len(guide["mistakes"]) >= 80, key
        assert guide["video_key"] in VIDEO_LIBRARY, key
        built = guide_embed(key)
        assert _embed_text_size(built) <= 6000
        assert all(len(field.value) <= 1024 for field in built.fields)


def test_center_embed_is_rich_but_inside_discord_limits():
    built = center_embed(500)
    assert len(built.fields) >= 3
    assert _embed_text_size(built) <= 6000
    assert BANNER_URL.endswith("assets/aidebot-banner.jpg")


def test_video_library_uses_clickable_https_urls():
    assert len(VIDEO_LIBRARY) >= 3
    for video in VIDEO_LIBRARY.values():
        assert video["url"].startswith("https://")
        assert len(video["note"]) >= 80


def test_discord_administrators_can_manage_and_claim_tickets():
    admin = Member(99, [], administrator=True)
    assert decide(admin, "help.claim").allowed is True
    assert decide(admin, "training.claim").allowed is True
    assert decide(admin, "training.manage").allowed is True
    assert decide(admin, "config.manage").allowed is True
