from aidebot.ops import format_operations, operations_health


def _stats(**overrides):
    base = {
        "open_requests": 0,
        "active_trainings": 0,
        "available_helpers": 0,
        "pending_applications": 0,
        "pending_challenges": 0,
        "open_mentorships": 0,
        "pending_reminders": 0,
        "reviews": 0,
        "avg_rating": 0.0,
    }
    base.update(overrides)
    return base


def test_ops_health_is_calm_when_queues_are_empty():
    state, _ = operations_health(_stats())
    assert state == "Calme"


def test_ops_health_warns_when_requests_wait_without_helpers():
    state, advice = operations_health(_stats(open_requests=6, available_helpers=0))
    assert state == "Attention"
    assert "aucun Helper" in advice


def test_ops_health_escalates_large_backlog():
    state, _ = operations_health(_stats(open_requests=11, pending_applications=8, pending_challenges=5))
    assert state == "À surveiller"


def test_ops_format_contains_key_work_queues():
    text = format_operations(_stats(open_requests=3, pending_applications=2, pending_reminders=4, avg_rating=4.75, reviews=8))
    assert "Demandes ouvertes :** 3" in text
    assert "Candidatures à traiter :** 2" in text
    assert "Rappels en attente :** 4" in text
    assert "4.8/5" in text
