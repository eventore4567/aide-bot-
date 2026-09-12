from aidebot.v54_manifest import V54_CAPABILITIES


def test_v54_manifest_lists_only_unique_shipped_capabilities():
    assert len(V54_CAPABILITIES) >= 40
    assert len(V54_CAPABILITIES) == len(set(V54_CAPABILITIES))
    assert "help.ai.contextual-handoff" in V54_CAPABILITIES
    assert "ux.no-owner-dashboard-runtime" in V54_CAPABILITIES
