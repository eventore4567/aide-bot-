from __future__ import annotations

import discord

# Structure compacte : chaque salon permanent a un rôle clair. Les membres
# utilisent surtout des panneaux, menus et formulaires plutôt qu'une longue
# liste de commandes slash.
ROLE_SPECS = [
    ("👑・Direction", 0xF1C40F, dict(manage_channels=True, manage_roles=True, manage_messages=True)),
    ("📘・Responsable Formation", 0xE67E22, dict(manage_messages=True)),
    ("🎓・Formateur", 0x5865F2, dict()),
    ("🤝・Helper", 0x57F287, dict()),
    ("🌟・Ambassadeur", 0xFEE75C, dict()),
    ("✅・Apprenant certifié", 0x3498DB, dict()),
    ("💎・VIP", 0xEB459E, dict()),
    ("🛡️・Expert Sécurité", 0xE74C3C, dict()),
    ("🤖・Expert Bots", 0x9B59B6, dict()),
    ("👤・Membre", 0x95A5A6, dict()),
]

# V52 garde 15 salons permanents : l'ancien salon vidéo public est remplacé
# par un assistant d'aide spécialisé. Les tutoriels restent accessibles depuis
# le Centre d'aide et l'espace Premium sans monopoliser un salon supplémentaire.
CATEGORY_SPECS = [
    ("━━ INFORMATIONS ━━", ["👋・bienvenue", "📜・règlement", "📢・annonces"]),
    ("━━ AIDE & FORMATIONS ━━", ["🎓・centre-aide", "🤖・assistant-aide", "🎓・formations"]),
    ("━━ BOUTIQUE ━━", ["🛒・shop"]),
    ("━━ PREMIUM ━━", ["💎・espace-premium", "🎬・videos-premium"]),
    ("━━ SERVICES ━━", ["🎫・ouvrir-ticket", "⭐・avis", "🧑‍🏫・recrutement"]),
    ("━━ STAFF ━━", ["📋・staff", "🧾・logs", "🧠・suivi-formations"]),
]

PERMANENT_CHANNEL_COUNT = sum(len(channels) for _, channels in CATEGORY_SPECS)
assert PERMANENT_CHANNEL_COUNT <= 15


def role_permissions(spec: dict[str, bool]) -> discord.Permissions:
    permissions = discord.Permissions.none()
    for name, value in spec.items():
        setattr(permissions, name, value)
    return permissions
