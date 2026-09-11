from __future__ import annotations

import discord

# Structure V40 : peu de salons, chacun a un rôle clair. Les membres utilisent
# des panneaux/boutons ; les commandes slash restent volontairement minimales.
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

# Bienvenue, formations, vidéos, boutique et tickets ont chacun leur propre
# panneau. Aucun contenu de formation ne doit être recopié dans Bienvenue.
CATEGORY_SPECS = [
    ("━━ INFORMATIONS ━━", ["👋・bienvenue", "📜・règlement", "📢・annonces"]),
    ("━━ AIDE & FORMATIONS ━━", ["🎓・centre-aide", "🎓・formations", "🎥・videos-guides"]),
    ("━━ BOUTIQUE ━━", ["🛒・shop"]),
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
