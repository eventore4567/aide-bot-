from __future__ import annotations

from dataclasses import dataclass

import discord

CAPABILITIES: dict[str, tuple[str, ...]] = {
    "training.claim": ("🎓・Formateur", "📘・Responsable Formation", "👑・Direction"),
    "training.manage": ("📘・Responsable Formation", "👑・Direction"),
    "help.claim": ("🤝・Helper", "🎓・Formateur", "📘・Responsable Formation", "👑・Direction"),
    "payment.confirm": ("👑・Direction",),
    "applications.review": ("📘・Responsable Formation", "👑・Direction"),
    "config.manage": ("👑・Direction",),
}


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    capability: str
    allowed_roles: tuple[str, ...]
    reason: str


def decide(member: discord.Member, capability: str) -> PermissionDecision:
    roles = CAPABILITIES.get(capability)
    if roles is None:
        return PermissionDecision(False, capability, (), "Permission inconnue : refus par défaut (fail-closed).")

    if member.guild.owner_id == member.id:
        return PermissionDecision(True, capability, roles, "Propriétaire du serveur.")

    member_roles = {role.name for role in member.roles}
    matched = [role for role in roles if role in member_roles]
    if matched:
        return PermissionDecision(True, capability, roles, f"Autorisé via {matched[0]}.")

    return PermissionDecision(False, capability, roles, "Aucun rôle autorisé n’est présent.")


def can(member: discord.Member, capability: str) -> bool:
    return decide(member, capability).allowed
