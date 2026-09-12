from types import SimpleNamespace

import discord

from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT
from aidebot.cogs.assistant_guardian_v52 import (
    AI_CHANNEL,
    AI_TITLE,
    GUARDIAN_TITLE,
    AideAIClient,
    AssistantPanelView,
    GuardianPanelView,
    SYSTEM_PROMPT,
    _extract_response_text,
    _redact_secrets,
    assistant_panel_embed,
    guardian_panel_embed,
)
from aidebot.guardian import diff_snapshots, snapshot_hash
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


class DummyCog:
    ai = SimpleNamespace(configured=True)


def _button_labels(view: discord.ui.View) -> set[str]:
    return {str(item.label) for item in view.children if isinstance(item, discord.ui.Button) and item.label}


def test_v52_ai_engine_remains_available_but_room_is_consolidated_in_v56():
    channels = [name for _category, names in CATEGORY_SPECS for name in names]
    assert PERMANENT_CHANNEL_COUNT <= 12
    assert AI_CHANNEL not in channels
    assert "🎓・centre-aide" in channels
    assert "aidebot.cogs.assistant_guardian_v52" in EXTENSIONS
    assert "aidebot.cogs.experience_v56" in EXTENSIONS


def test_v52_ai_panel_is_one_clear_action():
    embed = assistant_panel_embed(True)
    assert embed.title == AI_TITLE
    assert "discord" in (embed.description or "").casefold()
    view = AssistantPanelView(DummyCog())
    assert view.timeout is None
    assert _button_labels(view) == {"Poser une question"}


def test_v52_guardian_actions_are_distinct():
    embed = guardian_panel_embed()
    assert embed.title == GUARDIAN_TITLE
    view = GuardianPanelView(DummyCog())
    assert _button_labels(view) == {
        "Lancer un audit",
        "Enregistrer l’état sûr",
        "Voir les changements",
        "Restaurer les permissions",
    }


def test_v52_redacts_common_secrets_before_ai_call():
    text, changed = _redact_secrets("clé sk-abcdefghijklmnopqrstuvwxyz123456")
    assert changed is True
    assert "sk-" not in text
    tokenish, changed = _redact_secrets("abcDEF123456789012345678.abCDef.abcdefghijklmnopqrstuvwxyz123456")
    assert changed is True
    assert "SECRET MASQUÉ" in tokenish


def test_v52_response_parser_handles_responses_api_shape():
    payload = {
        "output": [
            {"content": [{"type": "output_text", "text": "Réponse utile"}]},
        ]
    }
    assert _extract_response_text(payload) == "Réponse utile"


def test_v52_ai_is_specialized_and_has_safe_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AIDEBOT_AI_MODEL", raising=False)
    client = AideAIClient()
    assert client.configured is False
    assert client.model == "gpt-5.6-luna"
    prompt = SYSTEM_PROMPT.casefold()
    assert "token" in prompt and "2fa" in prompt
    assert "discord" in prompt


def test_v52_snapshot_hash_and_diff_are_deterministic():
    before = {
        "guild": {"id": 1, "verification_level": 1, "explicit_content_filter": 1},
        "roles": [{"id": 10, "name": "Membre", "permissions": 1}],
        "channels": [{"id": 20, "name": "général", "category_id": None, "overwrites": {}}],
    }
    same = {
        "channels": [{"overwrites": {}, "category_id": None, "name": "général", "id": 20}],
        "roles": [{"permissions": 1, "name": "Membre", "id": 10}],
        "guild": {"explicit_content_filter": 1, "verification_level": 1, "id": 1},
    }
    after = {
        "guild": {"id": 1, "verification_level": 1, "explicit_content_filter": 1},
        "roles": [{"id": 10, "name": "Membre", "permissions": 8}],
        "channels": [{"id": 20, "name": "général", "category_id": None, "overwrites": {}}],
    }
    assert snapshot_hash(before) == snapshot_hash(same)
    assert diff_snapshots(before, same) == []
    assert any("Permissions du rôle" in item for item in diff_snapshots(before, after))


def test_v52_runtime_loads_without_new_public_slash_commands():
    assert "aidebot.cogs.assistant_guardian_v52" in EXTENSIONS
    assert EXTENSIONS.index("aidebot.cogs.assistant_guardian_v52") > EXTENSIONS.index("aidebot.cogs.product_experience_v51")
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}
