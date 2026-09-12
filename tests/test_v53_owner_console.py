from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import discord

from aidebot.cogs.owner_console_v53 import OWNER_ACTIONS, OwnerConsoleView, owner_console_embed
from aidebot.owner_config import OwnerBackupStore
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyBot:
    settings = SimpleNamespace(db_path="/tmp/aidebot-test.db", vip_price_robux=2000)

    def add_view(self, _view):
        return None

    def get_cog(self, _name):
        return None


def test_v53_owner_console_is_one_menu_not_a_button_wall():
    view = OwnerConsoleView(SimpleNamespace())
    assert view.timeout is None
    assert len(view.children) == 1
    select = view.children[0]
    assert isinstance(select, discord.ui.Select)
    assert len(select.options) == len(OWNER_ACTIONS) == 6
    values = {option.value for option in select.options}
    assert values == {"diagnostic", "backup", "export", "repair", "bundle", "readiness"}


def test_v53_owner_console_copy_is_private_maintenance_focused():
    embed = owner_console_embed()
    text = "\n".join(
        [embed.title or "", embed.description or "", *(f"{field.name}\n{field.value}" for field in embed.fields)]
    ).casefold()
    assert "propriétaire" in text
    assert "sauvegarde" in text
    assert "maintenance" in text
    assert "10k" not in text
    assert "v53" not in text


def test_v53_backup_store_rotates_and_never_claims_message_content(tmp_path):
    store = OwnerBackupStore(tmp_path, retention=2)

    async def scenario():
        for index in range(3):
            await store.save(
                123,
                "Test",
                {"guild": {"id": 123}, "roles": [{"id": index}], "channels": []},
                digest=f"hash-{index}",
                audit_score=90 - index,
            )
        latest = await store.latest_bytes(123)
        assert latest is not None
        filename, payload = latest
        assert filename.startswith("config-")
        data = json.loads(payload.decode("utf-8"))
        assert data["contains_messages"] is False
        assert data["guild_id"] == 123
        assert len(list((tmp_path / "123").glob("config-*.json"))) == 2

    asyncio.run(scenario())


def test_v53_backend_remains_testable_but_dashboard_runtime_is_removed_in_v54():
    assert "aidebot.cogs.owner_console_v53" not in EXTENSIONS
    assert "aidebot.cogs.ops_dashboard" not in EXTENSIONS
    assert "aidebot.cogs.assistant_guardian_setup_v52" in EXTENSIONS
    assert "aidebot.cogs.help_system_v54" in EXTENSIONS
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
