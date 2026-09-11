from __future__ import annotations

DANGEROUS_PERMISSIONS = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "ban_members",
    "kick_members",
    "moderate_members",
    "manage_webhooks",
)

PERMISSION_LABELS = {
    "administrator": "Administrateur",
    "manage_guild": "Gérer le serveur",
    "manage_roles": "Gérer les rôles",
    "manage_channels": "Gérer les salons",
    "ban_members": "Bannir des membres",
    "kick_members": "Expulser des membres",
    "moderate_members": "Exclure temporairement des membres",
    "manage_webhooks": "Gérer les webhooks",
}


def dangerous_permissions(permissions: object) -> list[str]:
    return [name for name in DANGEROUS_PERMISSIONS if bool(getattr(permissions, name, False))]


def format_permission_names(names: list[str]) -> str:
    return ", ".join(PERMISSION_LABELS.get(name, name) for name in names)
