import asyncio
from types import SimpleNamespace

import discord

from aidebot.cogs.power_suite_v58 import (
    BLUEPRINTS,
    KEY_PERMISSION_GROUPS,
    POWER_TITLE,
    SENSITIVE_EVERYONE_PERMISSIONS,
    BlueprintHomeViewV58,
    PowerStateStore,
    StaffPowerViewV58,
    blueprint_embed_v58,
    blueprint_payload,
    permission_embed_v58,
    staff_power_embed_v58,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyCog:
    bot = SimpleNamespace()


def test_v58_staff_panel_is_one_menu_with_five_distinct_tools():
    view = StaffPowerViewV58(DummyCog())
    assert view.timeout is None
    assert len(view.children) == 1
    select = view.children[0]
    assert isinstance(select, discord.ui.Select)
    assert {option.value for option in select.options} == {
        "doctor",
        "permissions",
        "guardian",
        "incident",
        "blueprint",
    }

    embed = staff_power_embed_v58()
    assert embed.title == POWER_TITLE
    assert len(embed.fields) == 5
    text = " ".join(field.name for field in embed.fields).casefold()
    assert "doctor" in text
    assert "permission" in text
    assert "guardian" in text
    assert "incident" in text
    assert "structure" in text


def test_v58_blueprints_are_real_previewable_structures():
    assert set(BLUEPRINTS) == {"community", "gaming", "creator", "support"}
    for key, blueprint in BLUEPRINTS.items():
        assert blueprint.roles
        assert len(blueprint.categories) >= 2
        assert sum(len(category.channels) for category in blueprint.categories) >= 5
        assert any(channel.kind == "voice" for category in blueprint.categories for channel in category.channels)
        assert any(channel.read_only for category in blueprint.categories for channel in category.channels)
        embed = blueprint_embed_v58(key)
        assert blueprint.label in (embed.title or "")
        assert len(embed.fields) >= 3
        payload = blueprint_payload(key).decode("utf-8")
        assert f'"template": "{key}"' in payload

    home = BlueprintHomeViewV58(DummyCog())
    selects = [item for item in home.children if isinstance(item, discord.ui.Select)]
    buttons = [item for item in home.children if isinstance(item, discord.ui.Button)]
    assert len(selects) == 1
    assert len(selects[0].options) == 4
    assert {button.label for button in buttons} == {"Annuler ma dernière création"}


def test_v58_permission_lab_has_clear_groups_and_admin_warning():
    permissions = discord.Permissions.none()
    permissions.view_channel = True
    permissions.send_messages = True
    embed = permission_embed_v58("Membre test", SimpleNamespace(name="général"), permissions)
    assert embed.title == "Permission Lab"
    assert set(KEY_PERMISSION_GROUPS) == {"Accès", "Modération", "Administration"}
    assert len(embed.fields) == 3

    admin = discord.Permissions.none()
    admin.administrator = True
    admin_embed = permission_embed_v58("Admin", SimpleNamespace(name="staff"), admin)
    assert any(field.name == "Attention" for field in admin_embed.fields)


def test_v58_incident_scope_is_narrow_and_reversible():
    assert set(SENSITIVE_EVERYONE_PERMISSIONS) == {
        "administrator",
        "manage_guild",
        "manage_roles",
        "manage_channels",
        "manage_webhooks",
        "mention_everyone",
    }
    assert "ban_members" not in SENSITIVE_EVERYONE_PERMISSIONS
    assert "send_messages" not in SENSITIVE_EVERYONE_PERMISSIONS


def test_v58_state_store_persists_only_reversible_metadata(tmp_path):
    async def scenario():
        store = PowerStateStore(str(tmp_path / "state.json"))
        await store.save_incident(123, 456)
        assert await store.get(123, "incident") == {"everyone_permissions": 456}
        await store.save_build(123, {"roles": [1], "categories": [2], "channels": [3], "template": "gaming"})
        build = await store.get(123, "last_build")
        assert build["template"] == "gaming"
        await store.clear_incident(123)
        assert await store.get(123, "incident") is None
        await store.clear_build(123)
        assert await store.get(123, "last_build") is None

    asyncio.run(scenario())


def test_v58_loads_after_v57_without_new_public_slash_commands():
    assert "aidebot.cogs.channel_experience_v57" in EXTENSIONS
    assert "aidebot.cogs.power_suite_v58" in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.power_suite_v58") > EXTENSIONS.index("aidebot.cogs.channel_experience_v57")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
