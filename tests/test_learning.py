from aidebot.catalog import CHALLENGES, INVITE_REWARDS, invite_reward_for, search_knowledge
from aidebot.permissions import decide


class Role:
    def __init__(self, name: str):
        self.name = name


class Guild:
    owner_id = 1


class Member:
    def __init__(self, user_id: int, roles: list[str]):
        self.id = user_id
        self.guild = Guild()
        self.roles = [Role(name) for name in roles]


def test_knowledge_search_finds_token_security():
    results = search_knowledge("sécuriser token bot")
    keys = [key for key, _ in results]
    assert "bot-token" in keys


def test_knowledge_search_returns_empty_for_unrelated_words():
    assert search_knowledge("banane cosmique") == []


def test_invite_rewards_are_monotonic_and_expected():
    thresholds = [threshold for threshold, _ in INVITE_REWARDS]
    assert thresholds == sorted(thresholds)
    assert invite_reward_for(0) == "Aucune récompense débloquée"
    assert invite_reward_for(1) == "Formation classique débloquée"
    assert invite_reward_for(10) == "Badge Ambassadeur"
    assert invite_reward_for(999) == "Badge Ambassadeur"


def test_challenges_have_positive_rewards():
    assert CHALLENGES
    for challenge in CHALLENGES.values():
        assert challenge["reward"] > 0
        assert challenge["description"]


def test_helper_can_review_challenge_and_claim_mentorship_but_not_dashboard():
    helper = Member(42, ["🤝・Helper"])
    assert decide(helper, "challenge.review").allowed is True
    assert decide(helper, "mentorship.claim").allowed is True
    assert decide(helper, "dashboard.view").allowed is False


def test_training_manager_can_view_dashboard():
    manager = Member(42, ["📘・Responsable Formation"])
    assert decide(manager, "dashboard.view").allowed is True
