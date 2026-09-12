from aidebot.cogs.assistant_guardian_v52 import guardian_panel_embed
from aidebot.cogs.enterprise_academy_v61 import staff_enterprise_embed
from aidebot.cogs.panel_authority_v64 import (
    CANONICAL_STAFF_TITLE,
    is_latest_staff_embed,
    is_legacy_guardian_embed,
)
from aidebot.cogs.power_suite_v58 import staff_power_embed_v58
from main import EXTENSIONS, PUBLIC_SLASH_COMMANDS


def test_v64_loads_last_without_expanding_public_slash_surface():
    assert EXTENSIONS[-1] == "aidebot.cogs.panel_authority_v64"
    assert PUBLIC_SLASH_COMMANDS == {"setup", "buy"}


def test_v64_recognises_only_latest_enterprise_staff_panel():
    latest = staff_enterprise_embed()
    assert latest.title == CANONICAL_STAFF_TITLE
    assert is_latest_staff_embed(latest)

    older = staff_power_embed_v58()
    assert older.title == CANONICAL_STAFF_TITLE
    assert not is_latest_staff_embed(older)


def test_v64_marks_standalone_guardian_as_legacy_staff_surface():
    guardian = guardian_panel_embed()
    assert is_legacy_guardian_embed(guardian)
    assert not is_latest_staff_embed(guardian)
