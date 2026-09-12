from __future__ import annotations

from aidebot.experience_content import VIDEO_LIBRARY as BASE_VIDEO_LIBRARY


# Les liens de recherche YouTube sont volontaires pour les sujets qui évoluent vite :
# l’utilisateur obtient des tutoriels récents au lieu d’un ID de vidéo mort ou obsolète.
VIDEO_LIBRARY = {
    **BASE_VIDEO_LIBRARY,
    "developer-portal": {
        "title": "Discord Developer Portal — créer et inviter un bot",
        "url": "https://www.youtube.com/results?search_query=discord+developer+portal+creer+bot+tutoriel+francais",
        "note": "Créer l’application, activer les intents nécessaires, générer le lien d’invitation et comprendre les permissions demandées.",
    },
    "python": {
        "title": "Python débutant — bases utiles pour discord.py",
        "url": "https://www.youtube.com/results?search_query=python+debutant+cours+francais+variables+fonctions+async",
        "note": "Variables, fonctions, conditions, boucles et bases de l’asynchrone avant d’attaquer un bot Discord plus sérieux.",
    },
    "webhooks": {
        "title": "Webhooks & embeds Discord — guide visuel",
        "url": "https://www.youtube.com/results?search_query=discord+webhook+embed+tutoriel+francais",
        "note": "Créer un webhook, comprendre les embeds et construire des annonces ou logs lisibles sans exposer de secret.",
    },
    "railway": {
        "title": "Railway — héberger un bot Python proprement",
        "url": "https://www.youtube.com/results?search_query=railway+deploy+discord+bot+python+tutorial",
        "note": "Déploiement, variables d’environnement et redémarrages. Pour SQLite, pense au stockage persistant ou à une vraie base.",
    },
    "slash": {
        "title": "discord.py — commandes slash / app_commands",
        "url": "https://www.youtube.com/results?search_query=discord.py+app_commands+slash+commands+tutorial",
        "note": "Comprendre les slash commands, les groupes, la synchronisation et les réponses éphémères.",
    },
    "ui": {
        "title": "discord.py UI — boutons, menus et formulaires",
        "url": "https://www.youtube.com/results?search_query=discord.py+buttons+select+modal+tutorial",
        "note": "Créer une vraie expérience panel-first avec boutons, select menus et modals au lieu de multiplier les commandes slash.",
    },
    "tickets": {
        "title": "Système de tickets Discord — bonnes pratiques",
        "url": "https://www.youtube.com/results?search_query=discord+tickets+bot+tutoriel+francais+permissions",
        "note": "Compare plusieurs systèmes de tickets et vérifie surtout confidentialité, permissions, attribution et fermeture propre.",
    },
    "roles": {
        "title": "Rôles & hiérarchie Discord — comprendre les blocages",
        "url": "https://www.youtube.com/results?search_query=discord+roles+hierarchie+permissions+tutoriel+francais",
        "note": "Utile quand un bot possède Gérer les rôles mais n’arrive toujours pas à attribuer un rôle placé trop haut.",
    },
    "onboarding": {
        "title": "Onboarding Discord — rendre un serveur simple à rejoindre",
        "url": "https://www.youtube.com/results?search_query=discord+onboarding+server+guide+tutorial",
        "note": "Accueil, règles, choix de rôles et parcours membre. L’objectif est qu’un nouveau comprenne quoi faire en quelques secondes.",
    },
    "moderation": {
        "title": "Modération Discord — organisation et permissions",
        "url": "https://www.youtube.com/results?search_query=discord+moderation+permissions+guide+francais",
        "note": "Structurer un staff sans donner Administrateur partout et garder des procédures compréhensibles.",
    },
    "security": {
        "title": "Sécurité / anti-raid Discord — tutoriels récents",
        "url": "https://www.youtube.com/results?search_query=discord+securite+anti+raid+tutoriel+francais",
        "note": "Sécurité serveur, anti-raid, rôles sensibles et procédure d’urgence. Vérifie toujours les permissions avant de copier une configuration.",
    },
    "database": {
        "title": "SQLite / bases de données pour un bot Discord",
        "url": "https://www.youtube.com/results?search_query=discord.py+sqlite+database+tutorial",
        "note": "Comprendre persistance, tables, lectures/écritures et pourquoi une base locale sans volume peut disparaître après redéploiement.",
    },
    "github": {
        "title": "Git & GitHub — branches, commits et pull requests",
        "url": "https://www.youtube.com/results?search_query=git+github+debutant+branches+pull+request+tutoriel+francais",
        "note": "Apprendre à travailler sur une branche, tester, ouvrir une pull request puis merger sans modifier directement la production.",
    },
    "testing": {
        "title": "Python pytest — tester son bot avant production",
        "url": "https://www.youtube.com/results?search_query=python+pytest+tutorial+francais",
        "note": "Tests unitaires, régressions et automatisation CI pour éviter de découvrir les bugs uniquement après le déploiement.",
    },
    "github-actions": {
        "title": "GitHub Actions — CI automatique",
        "url": "https://www.youtube.com/results?search_query=github+actions+python+pytest+ci+tutorial",
        "note": "Lancer compilation et tests automatiquement à chaque push ou pull request avant de toucher à la production.",
    },
}
