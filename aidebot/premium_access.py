from __future__ import annotations

import discord


PREMIUM_ROLE_NAMES = ("💎・VIP", "💎・Premium")


def premium_role(guild: discord.Guild) -> discord.Role | None:
    for name in PREMIUM_ROLE_NAMES:
        role = discord.utils.get(guild.roles, name=name)
        if role is not None:
            return role
    return None


def has_premium(member: discord.Member) -> bool:
    return any(role.name in PREMIUM_ROLE_NAMES for role in member.roles)


def missing_premium_message() -> str:
    return (
        "**Abonnement Premium manquant.**\n"
        "L’espace Premium est réservé aux membres qui possèdent le rôle **💎・VIP**. "
        "Pour l’obtenir, ouvre `🛒・shop` ou utilise `/buy`, clique sur **Acheter Premium**, "
        "puis attends la validation du paiement dans ton ticket."
    )
