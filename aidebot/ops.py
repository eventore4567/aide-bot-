from __future__ import annotations

from collections.abc import Mapping

OPS_DASHBOARD_MARKER = "AIDEBOT_OPS_DASHBOARD_V1"
MEMBER_HUB_MARKER = "AIDEBOT_MEMBER_HUB_V1"


def _as_int(stats: Mapping[str, int | float], key: str) -> int:
    return max(0, int(stats.get(key, 0)))


def operations_health(stats: Mapping[str, int | float]) -> tuple[str, str]:
    waiting = _as_int(stats, "open_requests")
    applications = _as_int(stats, "pending_applications")
    challenges = _as_int(stats, "pending_challenges")
    helpers = _as_int(stats, "available_helpers")

    backlog = waiting + applications + challenges
    if waiting >= 10 or backlog >= 20:
        return "À surveiller", "Beaucoup de demandes sont en attente. Priorise les tickets et les validations."
    if waiting >= 5 and helpers == 0:
        return "Attention", "Plusieurs demandes attendent et aucun Helper n'est disponible."
    if backlog == 0:
        return "Calme", "Aucune file d'attente importante détectée."
    return "Stable", "Les files d'attente restent à un niveau normal."


def format_operations(stats: Mapping[str, int | float]) -> str:
    health, advice = operations_health(stats)
    rating = float(stats.get("avg_rating", 0.0))
    return (
        f"**État :** {health}\n"
        f"**Demandes ouvertes :** {_as_int(stats, 'open_requests')}\n"
        f"**Formations / aides actives :** {_as_int(stats, 'active_trainings')}\n"
        f"**Helpers disponibles :** {_as_int(stats, 'available_helpers')}\n"
        f"**Candidatures à traiter :** {_as_int(stats, 'pending_applications')}\n"
        f"**Challenges à vérifier :** {_as_int(stats, 'pending_challenges')}\n"
        f"**Mentorats ouverts / actifs :** {_as_int(stats, 'open_mentorships')}\n"
        f"**Rappels en attente :** {_as_int(stats, 'pending_reminders')}\n"
        f"**Avis :** {_as_int(stats, 'reviews')} • moyenne **{rating:.1f}/5**\n\n"
        f"**Priorité suggérée :** {advice}"
    )
