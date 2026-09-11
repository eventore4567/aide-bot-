from aidebot.blueprint import CATEGORY_SPECS, PERMANENT_CHANNEL_COUNT
from aidebot.permissions import CAPABILITIES, decide


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


def test_server_stays_compact():
    assert PERMANENT_CHANNEL_COUNT <= 15
    names = [name for _, channels in CATEGORY_SPECS for name in channels]
    assert len(names) == len(set(names))


def test_permissions_fail_closed():
    member = Member(99, ["👤・Membre"])
    assert decide(member, "unknown.capability").allowed is False


def test_helper_cannot_confirm_payment():
    helper = Member(99, ["🤝・Helper"])
    assert decide(helper, "help.claim").allowed is True
    assert decide(helper, "payment.confirm").allowed is False


def test_owner_bypass_is_explicit():
    owner = Member(1, [])
    for capability in CAPABILITIES:
        assert decide(owner, capability).allowed is True
