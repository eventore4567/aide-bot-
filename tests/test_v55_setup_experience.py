import asyncio
from types import SimpleNamespace

import discord

from aidebot.cogs.setup_experience_v55 import (
    SETUP_STAGES,
    SNAPSHOT_RETENTION,
    SetupSessionView,
    SetupSnapshotStore,
)
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyCog:
    async def run_setup(self, _interaction):
        return None

    async def verify_only(self, _interaction):
        return None


def test_v55_replaces_setup_after_historical_setup_layers():
    assert "aidebot.cogs.setup_experience_v55" in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.setup_experience_v55") > EXTENSIONS.index("aidebot.cogs.setup_server")
    assert EXTENSIONS.index("aidebot.cogs.setup_experience_v55") > EXTENSIONS.index("aidebot.cogs.help_system_v54")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}


def test_v55_setup_has_real_safety_stages():
    assert len(SETUP_STAGES) == 8
    joined = " ".join(SETUP_STAGES).casefold()
    assert "analyse" in joined
    assert "sauvegarde" in joined
    assert "migration" in joined
    assert "rôles" in joined
    assert "permissions" in joined
    assert "panneaux" in joined
    assert "vérification" in joined
    assert SNAPSHOT_RETENTION == 3


def test_v55_setup_session_is_not_a_button_wall():
    async def scenario():
        view = SetupSessionView(DummyCog(), 123, install_disabled=False)
        buttons = [item for item in view.children if isinstance(item, discord.ui.Button)]
        labels = {str(item.label) for item in buttons}
        assert labels == {"Installer / réparer", "Vérifier seulement", "Annuler"}
        assert len(buttons) == 3
        assert view.timeout == 300

        blocked = SetupSessionView(DummyCog(), 123, install_disabled=True)
        install = next(item for item in blocked.children if getattr(item, "label", None) == "Installer / réparer")
        assert install.disabled is True

    asyncio.run(scenario())


def test_v55_snapshot_store_defaults_to_three_versions(tmp_path):
    store = SetupSnapshotStore(tmp_path)
    assert store.retention == 3
