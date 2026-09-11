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
    "tickets": "Checklist : catégories privées, permissions minimales, transcript ou résumé de fin, propriétaire clair, logs et fermeture propre.",
    "anti-raid": "Checklist : permissions minimales, verification level adapté, limites de création, logs, rôles sensibles séparés et plan d’urgence.",
}

KNOWLEDGE_BASE = {
    "roles": {
        "title": "Créer et organiser les rôles",
        "tags": ("rôle", "role", "hiérarchie", "couleur", "permissions"),
        "summary": "Place les rôles selon leur responsabilité, évite Administrateur par facilité et garde le rôle du bot au-dessus des rôles qu’il doit gérer.",
    },
    "channels": {
        "title": "Salons et catégories",
        "tags": ("salon", "channel", "catégorie", "organisation"),
        "summary": "Commence par l’objectif du serveur, limite les salons permanents et utilise les permissions de catégorie avant les exceptions par salon.",
    },
    "permissions": {
        "title": "Comprendre les permissions Discord",
        "tags": ("permission", "overwrite", "administrateur", "modération", "sécurité"),
        "summary": "Les permissions viennent des rôles puis des overwrites de catégorie/salon. Teste toujours avec un compte membre et applique le minimum nécessaire.",
    },
    "bot-token": {
        "title": "Sécuriser le token d’un bot",
        "tags": ("bot", "token", "secret", "railway", "github"),
        "summary": "Ne mets jamais le token dans GitHub. Utilise une variable d’environnement et régénère immédiatement tout token exposé.",
    },
    "slash": {
        "title": "Premières commandes slash",
        "tags": ("bot", "slash", "commande", "discord.py", "python"),
        "summary": "Déclare tes commandes avec app_commands, synchronise l’arbre de commandes et valide les permissions avant les actions sensibles.",
    },
    "tickets": {
        "title": "Construire un système de tickets propre",
        "tags": ("ticket", "support", "formulaire", "staff"),
        "summary": "Crée un ticket privé avec le demandeur et les rôles strictement nécessaires, conserve un statut clair et archive ou ferme proprement à la fin.",
    },
    "raid": {
        "title": "Préparer un serveur contre les raids",
        "tags": ("raid", "anti-raid", "sécurité", "modération"),
        "summary": "Réduis les permissions dangereuses, protège les rôles supérieurs, active des logs exploitables et garde une procédure d’urgence simple.",
    },
}

CHALLENGES = {
    "permissions-1": {
        "title": "Permissions propres",
        "difficulty": "Débutant",
        "description": "Crée Membre, Modérateur et Administrateur sans donner Administrateur au rôle Modérateur, puis configure un salon staff privé.",
        "reward": 40,
    },
    "serveur-1": {
        "title": "Serveur compact",
        "difficulty": "Débutant",
        "description": "Construis un serveur test avec 4 catégories maximum et explique l’utilité de chaque salon.",
        "reward": 35,
    },
    "bot-1": {
        "title": "Premier bot slash",
        "difficulty": "Intermédiaire",
        "description": "Crée un bot avec /ping et /userinfo, sans token dans le code, avec une gestion d’erreur simple.",
        "reward": 70,
    },
    "security-1": {
        "title": "Audit sécurité",
        "difficulty": "Intermédiaire",
        "description": "Analyse un serveur test et relève au moins cinq risques de permissions ou d’organisation, puis propose une correction pour chacun.",
        "reward": 80,
    },
}

INVITE_REWARDS = (
    (1, "Formation classique débloquée"),
    (3, "Pack de presets bonus"),
    (5, "Mini-formation bonus"),
    (10, "Badge Ambassadeur"),
)


def search_knowledge(query: str, limit: int = 5) -> list[tuple[str, dict]]:
    terms = {part.casefold() for part in query.split() if len(part.strip()) >= 2}
    scored: list[tuple[int, str, dict]] = []
    for key, item in KNOWLEDGE_BASE.items():
        haystack = " ".join((item["title"], item["summary"], *item["tags"])).casefold()
        score = sum(1 for term in terms if term in haystack)
        if score:
            scored.append((score, key, item))
    scored.sort(key=lambda entry: (-entry[0], entry[1]))
    return [(key, item) for _, key, item in scored[:limit]]


def invite_reward_for(count: int) -> str:
    unlocked = [label for threshold, label in INVITE_REWARDS if count >= threshold]
    return unlocked[-1] if unlocked else "Aucune récompense débloquée"
