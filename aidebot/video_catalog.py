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


# Bibliothèque avancée réservée à l'expérience Premium. Les recherches sont plus
# techniques et servent de complément au suivi humain, pas de remplacement.
PREMIUM_VIDEO_LIBRARY = {
    "p-architecture": {
        "title": "Architecture discord.py — cogs, services et séparation du code",
        "url": "https://www.youtube.com/results?search_query=discord.py+advanced+architecture+cogs+services+tutorial",
        "note": "Structurer un gros bot en modules maintenables, éviter les fichiers géants et séparer UI, logique métier et accès aux données.",
    },
    "p-async": {
        "title": "Asyncio avancé — tâches, verrous et concurrence",
        "url": "https://www.youtube.com/results?search_query=python+asyncio+locks+tasks+concurrency+advanced+tutorial",
        "note": "Comprendre les tâches concurrentes, locks, timeouts et conditions de course qui apparaissent dans les tickets, paiements et workers.",
    },
    "p-persistent-ui": {
        "title": "discord.py — vues persistantes et composants avancés",
        "url": "https://www.youtube.com/results?search_query=discord.py+persistent+views+buttons+select+modal+advanced",
        "note": "Construire des boutons et menus qui continuent de fonctionner après redémarrage et organiser proprement les custom_id.",
    },
    "p-rate-limits": {
        "title": "Discord API — rate limits, retries et backoff",
        "url": "https://www.youtube.com/results?search_query=discord+api+rate+limits+retry+backoff+bot",
        "note": "Éviter les rafales d’appels, comprendre les limites Discord et concevoir des retries sans créer de doublons.",
    },
    "p-logging": {
        "title": "Logging Python avancé — diagnostiquer un bot en production",
        "url": "https://www.youtube.com/results?search_query=python+logging+structured+logging+production+tutorial",
        "note": "Logs structurés, niveaux, corrélation d’erreurs et informations réellement utiles quand un déploiement casse.",
    },
    "p-oauth": {
        "title": "Discord OAuth2 & permissions — modèle de sécurité",
        "url": "https://www.youtube.com/results?search_query=discord+oauth2+permissions+scopes+security+tutorial",
        "note": "Scopes, permissions d’invitation, principe du moindre privilège et différence entre permissions serveur et accès applicatif.",
    },
    "p-secrets": {
        "title": "Secrets & variables d’environnement — protéger un bot",
        "url": "https://www.youtube.com/results?search_query=python+environment+variables+secrets+security+production",
        "note": "Tokens, secrets Railway/GitHub, rotation et bonnes pratiques pour ne jamais stocker une clé sensible dans le dépôt.",
    },
    "p-antiraid": {
        "title": "Anti-raid Discord avancé — stratégie et limites",
        "url": "https://www.youtube.com/results?search_query=discord+anti+raid+automod+advanced+security+bot",
        "note": "Combiner AutoMod, permissions, limites d’action, journaux et procédures humaines au lieu de dépendre d’un seul filtre.",
    },
    "p-webhook-security": {
        "title": "Webhooks Discord — sécurité, rotation et incidents",
        "url": "https://www.youtube.com/results?search_query=discord+webhook+security+rotate+token+incident",
        "note": "Comprendre pourquoi une URL de webhook est un secret et comment réagir si elle est exposée ou détournée.",
    },
    "p-incident": {
        "title": "Incident response — logs, containment et récupération",
        "url": "https://www.youtube.com/results?search_query=incident+response+logging+containment+recovery+beginner",
        "note": "Méthode simple pour contenir un incident, conserver les preuves utiles, corriger l’accès puis restaurer le service proprement.",
    },
    "p-railway-volume": {
        "title": "Railway — volumes persistants et données",
        "url": "https://www.youtube.com/results?search_query=railway+volume+persistent+storage+database+tutorial",
        "note": "Monter un volume, choisir un chemin stable et comprendre ce qui disparaît ou non lors d’un redéploiement.",
    },
    "p-postgres": {
        "title": "PostgreSQL pour bot Python — modèle production",
        "url": "https://www.youtube.com/results?search_query=python+postgresql+asyncpg+discord+bot+tutorial",
        "note": "Passer d’une base locale à PostgreSQL, gérer les connexions et préparer une vraie persistance multi-instance.",
    },
    "p-docker": {
        "title": "Dockeriser un bot Python proprement",
        "url": "https://www.youtube.com/results?search_query=docker+python+discord+bot+production+tutorial",
        "note": "Image reproductible, dépendances, variables et démarrage fiable pour éviter les différences entre local et production.",
    },
    "p-monitoring": {
        "title": "Monitoring & alertes — savoir qu’un bot est cassé",
        "url": "https://www.youtube.com/results?search_query=python+application+monitoring+logs+alerts+uptime+tutorial",
        "note": "Surveiller disponibilité, crashs, latence et erreurs importantes plutôt que découvrir un problème uniquement via les utilisateurs.",
    },
    "p-cicd": {
        "title": "CI/CD avancée — tests avant déploiement",
        "url": "https://www.youtube.com/results?search_query=github+actions+python+ci+cd+deployment+advanced",
        "note": "Construire une gate de tests, protéger la branche principale et ne déployer qu’un commit vérifié.",
    },
    "p-discord-ux": {
        "title": "UX Discord — concevoir une expérience panel-first",
        "url": "https://www.youtube.com/results?search_query=discord+bot+ui+ux+buttons+menus+design",
        "note": "Réduire les commandes, guider l’utilisateur, limiter les choix inutiles et rendre chaque écran compréhensible en quelques secondes.",
    },
    "p-ticket-architecture": {
        "title": "Tickets avancés — workflow, attribution et historique",
        "url": "https://www.youtube.com/results?search_query=discord+ticket+system+advanced+workflow+permissions+transcript",
        "note": "Concevoir prise en charge atomique, transfert, statuts, transcript et permissions sans transformer le ticket en chaos.",
    },
    "p-onboarding": {
        "title": "Onboarding avancé — conversion et activation membre",
        "url": "https://www.youtube.com/results?search_query=discord+community+onboarding+advanced+server+design",
        "note": "Faire comprendre la valeur du serveur dès l’arrivée et conduire le membre vers une première action utile rapidement.",
    },
    "p-accessibility": {
        "title": "Accessibilité UI — textes, contraste et composants",
        "url": "https://www.youtube.com/results?search_query=ui+accessibility+buttons+forms+contrast+ux+tutorial",
        "note": "Écrire des boutons explicites, éviter les murs de texte et construire des interfaces lisibles sur mobile comme sur PC.",
    },
    "p-community-systems": {
        "title": "Systèmes communautaires — rôles, progression et rétention",
        "url": "https://www.youtube.com/results?search_query=discord+community+engagement+roles+progression+retention",
        "note": "Créer une progression utile autour de l’apprentissage et du support sans tomber dans le spam ou les mécaniques artificielles.",
    },
    "p-async-pytest": {
        "title": "Pytest async — tester du code asynchrone",
        "url": "https://www.youtube.com/results?search_query=pytest+asyncio+advanced+tutorial",
        "note": "Tester coroutines, timeouts, erreurs et branches critiques d’un bot Discord sans dépendre du serveur réel.",
    },
    "p-integration": {
        "title": "Tests d’intégration Python — DB, services et workflows",
        "url": "https://www.youtube.com/results?search_query=python+integration+testing+database+services+tutorial",
        "note": "Vérifier plusieurs modules ensemble, notamment ticket + DB + paiement + permissions, avant la production.",
    },
    "p-sqlite-concurrency": {
        "title": "SQLite concurrence — transactions, WAL et verrous",
        "url": "https://www.youtube.com/results?search_query=sqlite+wal+transactions+concurrency+locking+tutorial",
        "note": "Comprendre les écritures concurrentes et protéger les opérations sensibles contre les doubles prises ou doubles validations.",
    },
    "p-migrations": {
        "title": "Migrations de base de données — faire évoluer le schéma",
        "url": "https://www.youtube.com/results?search_query=python+database+migrations+alembic+tutorial",
        "note": "Ajouter tables et colonnes sans casser les données déjà présentes, avec migrations versionnées et réversibles.",
    },
    "p-profiling": {
        "title": "Profiling Python — trouver lenteurs et surconsommation",
        "url": "https://www.youtube.com/results?search_query=python+profiling+performance+memory+tutorial",
        "note": "Mesurer avant d’optimiser : CPU, mémoire, tâches lentes et appels bloquants qui dégradent la réactivité du bot.",
    },
}
