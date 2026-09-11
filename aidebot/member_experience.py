from __future__ import annotations

from dataclasses import dataclass

from aidebot.catalog import INVITE_REWARDS


@dataclass(frozen=True)
class InviteProgress:
    total: int
    credits: int
    next_threshold: int | None
    next_reward: str | None
    remaining: int


def invite_progress(total: int, credits: int) -> InviteProgress:
    total = max(0, int(total))
    credits = max(0, int(credits))
    for threshold, reward in INVITE_REWARDS:
        if total < threshold:
            return InviteProgress(total, credits, threshold, reward, threshold - total)
    return InviteProgress(total, credits, None, None, 0)


def recommend_next_action(*, credits: int, reputation: int, helped: int, trainings: int, helper_available: bool) -> tuple[str, str]:
    if trainings <= 0 and credits <= 0:
        return (
            "Débloque ta première formation",
            "Obtiens 1 invitation valide, puis ouvre le panneau avec `/formation catalogue`. En attendant, utilise `/chercher` et `/challenge liste`.",
        )
    if trainings <= 0 and credits > 0:
        return (
            "Commence ta première formation",
            "Tu as déjà un crédit formation. Choisis ton parcours avec `/formation catalogue`.",
        )
    if trainings > 0 and helped <= 0:
        return (
            "Passe de l’apprentissage à la pratique",
            "Essaie un challenge avec `/challenge liste`, puis aide la communauté ou candidate avec `/candidature` si tu maîtrises un domaine.",
        )
    if helped > 0 and not helper_available:
        return (
            "Active ton statut Helper",
            "Si tu es disponible, utilise `/aide disponible actif:True` et renseigne tes compétences avec `/aide competence`.",
        )
    if reputation >= 500:
        return (
            "Transmets ton expérience",
            "Ton profil est déjà solide. Pense au mentorat, aux challenges avancés et à la candidature Formateur.",
        )
    return (
        "Continue à progresser",
        "Aide des membres, termine des challenges et développe tes compétences pour monter en réputation.",
    )


def progress_bar(current: int, target: int, width: int = 10) -> str:
    if target <= 0:
        return "█" * width
    current = max(0, min(current, target))
    filled = round(width * current / target)
    return "█" * filled + "░" * (width - filled)
