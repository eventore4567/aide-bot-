from aidebot.catalog import FORMATIONS, INVITE_REWARDS


def test_training_catalog_fits_discord_select_limit():
    assert len(FORMATIONS) <= 25


def test_every_training_has_member_facing_metadata():
    for key, data in FORMATIONS.items():
        assert data["title"], key
        assert data["description"], key
        assert data["steps"], key
        assert data["difficulty"], key
        assert data["duration"], key
        assert data["kind"] in {"classique", "vip", "extension"}, key


def test_classic_and_paid_paths_both_exist():
    assert any(not data["vip"] for data in FORMATIONS.values())
    assert any(data["vip"] for data in FORMATIONS.values())
    assert any(data["kind"] == "extension" for data in FORMATIONS.values())


def test_invite_rewards_are_sorted_and_unique():
    thresholds = [threshold for threshold, _ in INVITE_REWARDS]
    assert thresholds == sorted(thresholds)
    assert len(thresholds) == len(set(thresholds))
