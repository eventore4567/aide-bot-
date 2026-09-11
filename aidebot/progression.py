from __future__ import annotations


def community_level(reputation: int) -> str:
    if reputation >= 1000:
        return "Pilier"
    if reputation >= 500:
        return "Expert"
    if reputation >= 250:
        return "Confirmé"
    if reputation >= 100:
        return "Contributeur"
    return "Nouveau"


def profile_badges(*, reputation: int, helped: int, trainings: int, reviews: int, average: float) -> list[str]:
    badges: list[str] = []
    if helped >= 1:
        badges.append("🤝 Premier coup de main")
    if helped >= 10:
        badges.append("🧭 Helper confirmé")
    if trainings >= 1:
        badges.append("🎓 Première formation")
    if trainings >= 5:
        badges.append("📘 Formateur actif")
    if reviews >= 5 and average >= 4.5:
        badges.append("⭐ Très bien noté")
    if reputation >= 500:
        badges.append("🏆 Expert communauté")
    if reputation >= 1000:
        badges.append("💠 Pilier Aide Bot")
    return badges or ["🌱 Nouveau"]
