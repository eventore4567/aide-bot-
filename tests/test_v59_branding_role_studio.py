import discord
import pytest

from aidebot.blueprint import ROLE_SPECS
from aidebot.cogs.branding_role_studio_v59 import (
    BRAND_PANEL_CHANNELS,
    CUSTOM_ROLE_PRESETS,
    SELF_ROLE_SPECS,
    BrandingHomeViewV59,
    RoleStudioViewV59,
    SelfRoleViewV59,
    StaffPowerViewV59,
    _hex_color,
    _safe_https_image_url,
    staff_power_embed_v59,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyCog:
    pass


def test_v59_loads_after_v58_and_keeps_public_slash_surface_small():
    assert "aidebot.cogs.power_suite_v58" in EXTENSIONS
    assert "aidebot.cogs.branding_role_studio_v59" in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.branding_role_studio_v59") > EXTENSIONS.index("aidebot.cogs.power_suite_v58")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}


def test_v59_staff_panel_has_seven_distinct_tools_without_button_wall():
    view = StaffPowerViewV59(DummyCog())
    assert len(view.children) == 1
    select = view.children[0]
    assert isinstance(select, discord.ui.Select)
    assert len(select.options) == 7
    labels = [option.label for option in select.options]
    assert len(labels) == len(set(labels))
    assert "Branding Studio" in labels
    assert "Role Studio" in labels


def test_v59_branding_home_is_small_and_visible():
    view = BrandingHomeViewV59(DummyCog())
    assert len(view.children) == 2
    assert {item.label for item in view.children} == {"Configurer le branding", "Appliquer les réglages enregistrés"}
    embed = staff_power_embed_v59()
    text = " ".join(field.name + " " + field.value for field in embed.fields)
    assert "Branding Studio" in text
    assert "Role Studio" in text


def test_v59_self_roles_are_interest_only_and_capped_to_two():
    view = SelfRoleViewV59(DummyCog())
    assert len(view.children) == 1
    select = view.children[0]
    assert isinstance(select, discord.ui.Select)
    assert select.max_values == 2
    assert len(select.options) == len(SELF_ROLE_SPECS) == 4
    assert len({name for name, _ in SELF_ROLE_SPECS}) == len(SELF_ROLE_SPECS)


def test_v59_role_studio_has_clear_actions_not_duplicate_navigation():
    view = RoleStudioViewV59(DummyCog())
    labels = [item.label for item in view.children]
    assert labels == [
        "Auditer les rôles",
        "Réparer les rôles Aide Bot",
        "Créer un rôle sûr",
        "Réparer le panneau self-role",
    ]


def test_v59_custom_role_presets_never_grant_dangerous_admin_permissions():
    dangerous = {
        "administrator",
        "manage_guild",
        "manage_roles",
        "manage_channels",
        "manage_webhooks",
        "ban_members",
        "kick_members",
        "mention_everyone",
    }
    assert set(CUSTOM_ROLE_PRESETS) == {"lecture", "membre", "helper", "moderation"}
    for _label, spec in CUSTOM_ROLE_PRESETS.values():
        assert not any(spec.get(permission, False) for permission in dangerous)


def test_v59_branding_only_targets_known_panel_channels():
    assert "📋・staff" in BRAND_PANEL_CHANNELS
    assert "🎓・centre-aide" in BRAND_PANEL_CHANNELS
    assert "🛒・shop" in BRAND_PANEL_CHANNELS
    assert "🧾・logs" not in BRAND_PANEL_CHANNELS


def test_v59_url_guard_rejects_non_https_and_private_addresses():
    assert _safe_https_image_url("") == ""
    assert _safe_https_image_url("https://cdn.discordapp.com/attachments/a/b.png").startswith("https://")
    with pytest.raises(ValueError):
        _safe_https_image_url("http://cdn.discordapp.com/x.png")
    with pytest.raises(ValueError):
        _safe_https_image_url("https://127.0.0.1/x.png")
    with pytest.raises(ValueError):
        _safe_https_image_url("https://example.com/x.png")


def test_v59_hex_parser_is_strict():
    assert _hex_color("#5865F2") == 0x5865F2
    assert _hex_color("5865f2") == 0x5865F2
    with pytest.raises(ValueError):
        _hex_color("blue")


def test_v59_role_source_still_has_unique_canonical_roles():
    names = [name for name, _color, _spec in ROLE_SPECS]
    assert len(names) == len(set(names))
