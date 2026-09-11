from __future__ import annotations

from aidebot.catalog import FORMATIONS, RESOURCES


STEP_RESOURCES: dict[str, tuple[str, ...]] = {
    "discord": ("serveur", "serveur", "permissions", "permissions", "bot", "anti-raid"),
    "serveur": ("serveur", "serveur", "permissions", "permissions", "staff", "anti-raid", "lancement"),
    "permissions": ("permissions", "permissions", "permissions", "staff", "anti-raid", "permissions"),
    "bot": ("bot", "bot", "bot", "bot", "bot", "permissions", "lancement"),
    "vip": ("formation", "formation", "formation", "formation", "lancement"),
    "serveur-pro": ("serveur", "serveur", "permissions", "serveur", "tickets", "staff", "lancement"),
    "bot-avance": ("bot", "bot", "permissions", "bot", "bot", "bot", "lancement"),
    "securite-avancee": ("permissions", "permissions", "permissions", "bot", "anti-raid", "anti-raid", "lancement"),
}


def next_step_guidance(training_key: str, progress: int) -> tuple[str, str, str] | None:
    """Return (step label, resource key, resource text) for the next step."""
    formation = FORMATIONS.get(training_key)
    if not formation:
        return None
    steps = formation["steps"]
    if progress >= len(steps):
        return None

    step = steps[progress]
    mapping = STEP_RESOURCES.get(training_key, ())
    resource_key = mapping[progress] if progress < len(mapping) else "formation"
    resource = RESOURCES.get(resource_key, RESOURCES["formation"])
    return step, resource_key, resource


def format_guidance(training_key: str, progress: int) -> str | None:
    guidance = next_step_guidance(training_key, progress)
    if guidance is None:
        return None
    step, resource_key, resource = guidance
    return f"**Prochaine étape :** {step}\n**Ressource `{resource_key}` :** {resource}"
