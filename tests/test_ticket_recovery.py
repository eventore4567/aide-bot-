from types import SimpleNamespace

from aidebot.cogs.ticket_recovery import matching_ticket_channels


def channel(name: str, channel_id: int):
    return SimpleNamespace(name=name, id=channel_id)


def test_matching_ticket_channels_uses_exact_request_prefix():
    channels = [
        channel("ticket-12-jayden", 1),
        channel("ticket-123-other", 2),
        channel("ticket-12-second", 3),
        channel("general", 4),
    ]
    matches = matching_ticket_channels(12, channels)
    assert [item.id for item in matches] == [1, 3]


def test_matching_ticket_channels_returns_empty_when_channel_was_never_created():
    channels = [channel("ticket-2-user", 1), channel("ticket-3-user", 2)]
    assert matching_ticket_channels(1, channels) == []


def test_matching_ticket_channels_handles_missing_name_safely():
    channels = [SimpleNamespace(id=1), channel("ticket-7-user", 2)]
    matches = matching_ticket_channels(7, channels)
    assert [item.id for item in matches] == [2]
