from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PersistenceCheck:
    ok: bool
    message: str


def persistence_check(db_path: str, railway: bool) -> PersistenceCheck:
    path = Path(db_path)
    normalized = path.as_posix()
    if not railway:
        return PersistenceCheck(True, f"SQLite local : `{normalized}`")

    if normalized == "/data/aidebot.db" or normalized.startswith("/data/"):
        return PersistenceCheck(True, f"Chemin Railway prévu pour volume persistant : `{normalized}`")

    return PersistenceCheck(
        False,
        f"SQLite Railway utilise `{normalized}`. Sans volume persistant, les données peuvent disparaître lors d’un redéploiement.",
    )


def required_guild_permissions() -> tuple[tuple[str, str], ...]:
    return (
        ("manage_roles", "Gérer les rôles"),
        ("manage_channels", "Gérer les salons"),
        ("manage_guild", "Gérer le serveur (lecture des invitations)"),
        ("send_messages", "Envoyer des messages"),
        ("embed_links", "Intégrer des liens/embeds"),
    )


def missing_permission_labels(permissions: object) -> list[str]:
    missing: list[str] = []
    for attr, label in required_guild_permissions():
        if not bool(getattr(permissions, attr, False)):
            missing.append(label)
    return missing
