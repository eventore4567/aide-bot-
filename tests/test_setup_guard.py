from aidebot.setup_guard import canonical_collisions, format_collisions


def test_no_collision_for_unique_canonical_objects():
    collisions = canonical_collisions(
        role_names=["👑・Direction", "👤・Membre", "Random"],
        category_names=["━━ STAFF ━━", "Other"],
        channel_names=["🧾・logs", "💬・général", "chat-2"],
    )
    assert collisions == []


def test_detects_duplicate_role_category_and_channel():
    collisions = canonical_collisions(
        role_names=["👑・Direction", "👑・Direction", "👤・Membre"],
        category_names=["━━ STAFF ━━", "━━ STAFF ━━"],
        channel_names=["🧾・logs", "🧾・logs", "🧾・logs"],
    )
    compact = {(item.kind, item.name): item.count for item in collisions}
    assert compact[("rôle", "👑・Direction")] == 2
    assert compact[("catégorie", "━━ STAFF ━━")] == 2
    assert compact[("salon", "🧾・logs")] == 3


def test_ignores_duplicate_names_outside_aidebot_blueprint():
    collisions = canonical_collisions(
        role_names=["Gaming", "Gaming"],
        category_names=["Games", "Games"],
        channel_names=["clips", "clips"],
    )
    assert collisions == []


def test_format_collision_is_actionable():
    collisions = canonical_collisions(
        role_names=["🤝・Helper", "🤝・Helper"],
        category_names=[],
        channel_names=[],
    )
    text = format_collisions(collisions)
    assert "rôle" in text
    assert "🤝・Helper" in text
    assert "×2" in text
