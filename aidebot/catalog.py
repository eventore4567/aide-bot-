from __future__ import annotations

FORMATIONS = {
    "discord": {
        "title": "Débuter sur Discord",
        "description": "Comprendre l’interface, les salons, rôles, messages, sécurité et bonnes pratiques.",
        "steps": ["Découvrir Discord", "Salons et catégories", "Rôles", "Permissions", "Bots", "Sécurité"],
        "vip": False,
    },
    "serveur": {
        "title": "Créer son premier serveur",
        "description": "Construire un serveur propre, logique, sécurisé et prêt à accueillir une communauté.",
        "steps": ["Objectif", "Structure", "Rôles", "Permissions", "Modération", "Sécurité", "Vérification finale"],
        "vip": False,
    },
    "permissions": {
        "title": "Permissions, modération et sécurité",
        "description": "Comprendre les permissions Discord, la hiérarchie et les protections anti-abus.",
        "steps": ["Hiérarchie", "Permissions salon", "Permissions rôle", "Modération", "Audit", "Exercice pratique"],
        "vip": False,
    },
    "bot": {
        "title": "Créer son premier bot Discord",
        "description": "Découvrir Python/discord.py et créer un petit bot propre avec commandes slash.",
        "steps": ["Préparer le projet", "Token et sécurité", "Premier démarrage", "Commande /ping", "Embeds", "Permissions", "Déploiement"],
        "vip": False,
    },
    "vip": {
        "title": "Formation VIP / accompagnement",
        "description": "Accompagnement personnalisé, vocal, audit, sécurité avancée, bot ou serveur selon le besoin.",
        "steps": ["Diagnostic", "Plan personnalisé", "Accompagnement", "Vérification finale"],
        "vip": True,
    },
}

RESOURCES = {
    "permissions": "Checklist : ne jamais donner Administrateur par facilité ; tester la hiérarchie ; vérifier les overwrites salon/rôle ; documenter les rôles sensibles.",
    "serveur": "Checklist : objectif -> catégories -> rôles -> permissions -> sécurité -> tickets -> logs -> test avec un compte membre.",
    "bot": "Checklist : secrets en variables d’environnement, commandes slash, gestion d’erreurs, permissions explicites, logs et tests avant déploiement.",
    "staff": "Checklist : responsabilités écrites, permissions minimales, procédure de sanction, procédure ticket et journalisation des actions sensibles.",
}
