from aidebot.blueprint import ROLE_SPECS
from aidebot.member_experience import invite_progress, progress_bar, recommend_next_action


def test_invite_progress_reports_next_reward():
    state = invite_progress(total=2, credits=1)
    assert state.next_threshold == 3
    assert state.remaining == 1
    assert state.next_reward == "Pack de presets bonus"


def test_invite_progress_caps_after_last_reward():
    state = invite_progress(total=12, credits=4)
    assert state.next_threshold is None
    assert state.remaining == 0


def test_new_member_gets_clear_first_action():
    title, advice = recommend_next_action(
        credits=0,
        reputation=0,
        helped=0,
        trainings=0,
        helper_available=False,
    )
    assert "première formation" in title
    assert "/chercher" in advice


def test_trained_member_is_encouraged_to_practice():
    title, advice = recommend_next_action(
        credits=0,
        reputation=100,
        helped=0,
        trainings=1,
        helper_available=False,
    )
    assert "pratique" in title
    assert "/challenge" in advice


def test_progress_bar_has_fixed_width():
    bar = progress_bar(3, 5, width=10)
    assert len(bar) == 10
    assert bar.count("█") == 6


def test_canonical_roles_never_receive_administrator_or_manage_guild():
    for name, _color, spec in ROLE_SPECS:
        assert not spec.get("administrator", False), name
        assert not spec.get("manage_guild", False), name


def test_helpers_and_trainers_have_no_native_moderation_power():
    specs = {name: spec for name, _color, spec in ROLE_SPECS}
    assert specs["🤝・Helper"] == {}
    assert specs["🎓・Formateur"] == {}
