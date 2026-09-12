from __future__ import annotations

from urllib.parse import quote_plus


def youtube_search(query: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote_plus(query)


# L'offre gratuite reste volontairement courte : documentation de référence +
# quelques vidéos réellement utiles. Le but est d'aider vite, pas d'afficher
# une bibliothèque géante qui donne l'impression d'être Premium gratuitement.
FREE_RESOURCE_LIBRARY: dict[str, tuple[dict[str, str], ...]] = {
    "fr": (
        {
            "title": "Centre d’aide Discord",
            "url": "https://support.discord.com/hc/fr",
            "kind": "Documentation officielle",
            "level": "Débutant",
            "note": "Référence fiable pour serveurs, salons, rôles, comptes et sécurité.",
        },
        {
            "title": "Documentation Python 3",
            "url": "https://docs.python.org/fr/3/",
            "kind": "Documentation officielle",
            "level": "Débutant → avancé",
            "note": "À utiliser quand tu veux comprendre le code au lieu de copier une solution.",
        },
        {
            "title": "Documentation GitHub",
            "url": "https://docs.github.com/fr",
            "kind": "Documentation officielle",
            "level": "Débutant → avancé",
            "note": "Branches, commits, pull requests, Actions et sécurité du dépôt.",
        },
        {
            "title": "Créer un bot sur le Developer Portal",
            "url": "https://www.youtube.com/watch?v=Atcxx0GdtFQ",
            "kind": "Vidéo sélectionnée",
            "level": "Débutant",
            "note": "Création de l’application, permissions, installation et intents.",
        },
        {
            "title": "Créer un bot Discord en Python — formation complète",
            "url": "https://www.youtube.com/watch?v=LHF1dgwW6aw",
            "kind": "Vidéo sélectionnée",
            "level": "Débutant → intermédiaire",
            "note": "Discord.py, événements, commandes slash, cogs et mise en ligne expliqués en français.",
        },
    ),
    "en": (
        {
            "title": "Discord Help Center",
            "url": "https://support.discord.com/hc/en-us",
            "kind": "Official documentation",
            "level": "Beginner",
            "note": "Reliable reference for servers, channels, roles, accounts and safety.",
        },
        {
            "title": "Discord Developer Documentation",
            "url": "https://discord.com/developers/docs/intro",
            "kind": "Official documentation",
            "level": "Intermediate",
            "note": "Applications, interactions, intents, OAuth2, permissions and API behavior.",
        },
        {
            "title": "discord.py documentation",
            "url": "https://discordpy.readthedocs.io/en/stable/",
            "kind": "Official documentation",
            "level": "Intermediate",
            "note": "Primary framework reference for events, commands, interactions and UI components.",
        },
        {
            "title": "Python Asyncio — full tutorial",
            "url": "https://www.youtube.com/watch?v=Qb9s3UiMSTA",
            "kind": "Selected video",
            "level": "Intermediate",
            "note": "Event loop, coroutines, tasks and synchronization explained clearly.",
        },
        {
            "title": "Git — full course for beginners",
            "url": "https://www.youtube.com/watch?v=zTjRZNkhiEU",
            "kind": "Selected video",
            "level": "Beginner",
            "note": "Commits, branches, merge, rebase, GitHub and pull requests in one course.",
        },
    ),
}


PREMIUM_CATEGORIES: dict[str, dict[str, str]] = {
    "architecture": {
        "fr": "Architecture & bot avancé",
        "en": "Architecture & advanced bot engineering",
        "fr_desc": "Structure du code, async, vues persistantes et limites API.",
        "en_desc": "Code architecture, async, persistent UI and API limits.",
    },
    "security": {
        "fr": "Sécurité & permissions",
        "en": "Security & permissions",
        "fr_desc": "Moindre privilège, OAuth2, secrets, anti-raid et incidents.",
        "en_desc": "Least privilege, OAuth2, secrets, anti-raid and incident response.",
    },
    "production": {
        "fr": "Production & hébergement",
        "en": "Production & hosting",
        "fr_desc": "Railway, Docker, PostgreSQL, CI/CD et observabilité.",
        "en_desc": "Railway, Docker, PostgreSQL, CI/CD and observability.",
    },
    "product": {
        "fr": "UX, support & communauté",
        "en": "UX, support & community",
        "fr_desc": "Onboarding, tickets, panels et expérience membre.",
        "en_desc": "Onboarding, tickets, panels and member experience.",
    },
    "quality": {
        "fr": "Qualité & fiabilité",
        "en": "Quality & reliability",
        "fr_desc": "Tests, concurrence, base de données, logs et performance.",
        "en_desc": "Testing, concurrency, databases, logging and performance.",
    },
}


def _video(title: str, url: str, note: str, *, direct: bool = False) -> dict[str, str | bool]:
    return {"title": title, "url": url, "note": note, "type": "video", "direct": direct}


def _docs(title: str, url: str, note: str) -> dict[str, str | bool]:
    return {"title": title, "url": url, "note": note, "type": "docs", "direct": True}


# Premium est séparé par langue. Les liens directs sont utilisés quand une vidéo
# stable et vérifiée est disponible ; les sujets très mouvants utilisent une
# recherche YouTube explicite, afin d'éviter un tutoriel figé devenu faux.
PREMIUM_RESOURCE_LIBRARY: dict[str, dict[str, tuple[dict[str, str | bool], ...]]] = {
    "fr": {
        "architecture": (
            _video(
                "Discord.py complet : architecture, commandes et cogs",
                "https://www.youtube.com/watch?v=LHF1dgwW6aw",
                "Base française solide avant d'aller vers les patterns avancés.",
                direct=True,
            ),
            _video(
                "Developer Portal : permissions et intents",
                "https://www.youtube.com/watch?v=Atcxx0GdtFQ",
                "Comprendre exactement ce que l'application demande à Discord.",
                direct=True,
            ),
            _video(
                "Vues persistantes discord.py — FR",
                youtube_search("discord.py vues persistantes boutons select modal tutoriel français"),
                "Recherche récente pour les composants qui survivent aux redémarrages.",
            ),
            _video(
                "Asyncio avancé pour bots — FR",
                youtube_search("Python asyncio avancé tâches locks concurrence tutoriel français"),
                "Tasks, locks, timeouts et conditions de course dans un bot réel.",
            ),
        ),
        "security": (
            _video(
                "Rôles et permissions Discord — FR",
                "https://www.youtube.com/watch?v=w7ju9b0C6bU",
                "Hiérarchie et permissions expliquées visuellement ; complète avec la documentation actuelle.",
                direct=True,
            ),
            _docs(
                "Discord Safety Center",
                "https://discord.com/safety",
                "Référence officielle pour sécurité, signalement et protections Discord.",
            ),
            _video(
                "Anti-raid & AutoMod — FR",
                youtube_search("Discord anti raid AutoMod sécurité serveur tutoriel français 2026"),
                "Recherche récente car les outils de sécurité Discord évoluent régulièrement.",
            ),
            _video(
                "OAuth2, scopes et permissions — FR",
                youtube_search("Discord OAuth2 scopes permissions bot tutoriel français"),
                "Comprendre le moindre privilège plutôt que demander Administrateur partout.",
            ),
        ),
        "production": (
            _docs(
                "Railway Docs",
                "https://docs.railway.com/",
                "Services, variables, volumes, logs et déploiements ; documentation de référence.",
            ),
            _video(
                "Déployer un bot Python sur Railway — FR",
                youtube_search("Railway déployer bot Discord Python français 2026 variables volume logs"),
                "Recherche récente pour éviter les anciens workflows Railway.",
            ),
            _video(
                "Docker pour application Python — FR",
                youtube_search("Docker Python production tutoriel français Dockerfile variables environnement"),
                "Créer une image reproductible et comprendre le démarrage en production.",
            ),
            _video(
                "GitHub Actions + pytest — FR",
                youtube_search("GitHub Actions Python pytest CI tutoriel français"),
                "Mettre une gate automatique avant merge et déploiement.",
            ),
        ),
        "product": (
            _video(
                "Onboarding Discord professionnel — FR",
                youtube_search("Discord onboarding serveur professionnel français rôles communauté"),
                "Réduire la confusion dès l'arrivée et guider vers une première action utile.",
            ),
            _video(
                "Tickets Discord : permissions et workflow — FR",
                youtube_search("Discord ticket système permissions workflow transcript tutoriel français"),
                "Confidentialité, prise en charge, statuts et fermeture propre.",
            ),
            _video(
                "Bot Discord panel-first : boutons, menus, formulaires — FR",
                youtube_search("discord.py boutons select modal interface tutoriel français"),
                "Construire une UX guidée sans multiplier les slash commands.",
            ),
            _docs(
                "Discord Community — documentation",
                "https://support.discord.com/hc/fr/categories/200404378",
                "Référence Discord pour les fonctions serveur et la gestion communautaire.",
            ),
        ),
        "quality": (
            _video(
                "Pytest + async Python — FR",
                youtube_search("pytest asyncio Python tests asynchrones tutoriel français"),
                "Tester coroutines, erreurs, timeouts et workflows critiques.",
            ),
            _video(
                "SQLite : transactions, WAL et concurrence — FR",
                youtube_search("SQLite WAL transactions concurrence Python français"),
                "Éviter doubles validations, verrous et écritures incohérentes.",
            ),
            _video(
                "Logging Python en production — FR",
                youtube_search("Python logging production logs structurés tutoriel français"),
                "Logs utiles, niveaux, contexte et diagnostic après déploiement.",
            ),
            _video(
                "Profiling & performance Python — FR",
                youtube_search("Python profiling performance mémoire tutoriel français"),
                "Mesurer CPU, mémoire et tâches lentes avant d'optimiser.",
            ),
        ),
    },
    "en": {
        "architecture": (
            _video(
                "Asyncio in Python — full tutorial",
                "https://www.youtube.com/watch?v=Qb9s3UiMSTA",
                "Event loop, coroutines, tasks and synchronization from a verified Python educator.",
                direct=True,
            ),
            _docs(
                "discord.py documentation",
                "https://discordpy.readthedocs.io/en/stable/",
                "Primary framework reference for interactions, events, UI and API objects.",
            ),
            _video(
                "discord.py persistent views & components",
                youtube_search("discord.py persistent views buttons select modal advanced tutorial English"),
                "Recent results for persistent component patterns and custom IDs.",
            ),
            _video(
                "Discord API rate limits & backoff",
                youtube_search("Discord API rate limits retries backoff bot tutorial English"),
                "Design retries without bursts, duplicate actions or accidental loops.",
            ),
        ),
        "security": (
            _docs(
                "Discord Developer Docs — OAuth2",
                "https://discord.com/developers/docs/topics/oauth2",
                "Official scopes, authorization flow and permission reference.",
            ),
            _video(
                "Discord bot security & least privilege",
                youtube_search("Discord bot security least privilege permissions tutorial English"),
                "Keep bot and staff permissions as narrow as possible.",
            ),
            _video(
                "Discord anti-raid & AutoMod",
                youtube_search("Discord AutoMod anti raid server security tutorial English 2026"),
                "Recent results for changing Discord safety features.",
            ),
            _video(
                "Secrets, tokens and environment variables",
                youtube_search("Python secrets environment variables token security production tutorial English"),
                "Prevent tokens and API keys from entering source control or logs.",
            ),
        ),
        "production": (
            _docs(
                "Railway Docs",
                "https://docs.railway.com/",
                "Official reference for services, variables, volumes, logs and deploys.",
            ),
            _video(
                "Railway + Python production deployment",
                youtube_search("Railway Python deploy production variables volume logs tutorial English"),
                "Recent deployment guidance for a production service.",
            ),
            _video(
                "Git — full course",
                "https://www.youtube.com/watch?v=zTjRZNkhiEU",
                "Branches, merge, rebase, GitHub and pull requests in one verified course.",
                direct=True,
            ),
            _video(
                "Docker + Python production",
                youtube_search("Docker Python production Dockerfile tutorial English"),
                "Build reproducible images and predictable startup behavior.",
            ),
        ),
        "product": (
            _video(
                "Discord onboarding & community UX",
                youtube_search("Discord community onboarding server design tutorial English"),
                "Make the first minute understandable and action-oriented.",
            ),
            _video(
                "Advanced ticket workflow design",
                youtube_search("Discord ticket workflow permissions transcript advanced tutorial English"),
                "Ownership, privacy, status transitions and clean closure.",
            ),
            _video(
                "Discord bot UI: buttons, selects and modals",
                youtube_search("discord.py buttons selects modals UI UX tutorial English"),
                "Build guided flows instead of command walls.",
            ),
            _docs(
                "Discord Help Center — Community",
                "https://support.discord.com/hc/en-us/categories/200404378",
                "Official reference for server and community features.",
            ),
        ),
        "quality": (
            _video(
                "Async testing with pytest",
                youtube_search("pytest asyncio async testing Python tutorial English"),
                "Test coroutines, timeouts, failures and critical workflows.",
            ),
            _video(
                "SQLite WAL, transactions and concurrency",
                youtube_search("SQLite WAL transactions concurrency locking tutorial English"),
                "Understand write contention and protect atomic operations.",
            ),
            _video(
                "Structured logging in Python",
                youtube_search("Python structured logging production tutorial English"),
                "Make production failures diagnosable instead of guessing from vague errors.",
            ),
            _video(
                "Python profiling & performance",
                youtube_search("Python profiling performance memory tutorial English"),
                "Measure CPU, memory and blocking work before optimizing.",
            ),
        ),
    },
}


def free_resources(language: str) -> tuple[dict[str, str], ...]:
    return FREE_RESOURCE_LIBRARY.get(language.casefold().strip(), FREE_RESOURCE_LIBRARY["en"])


def premium_resources(language: str, category: str) -> tuple[dict[str, str | bool], ...]:
    lang = language.casefold().strip()
    if lang not in PREMIUM_RESOURCE_LIBRARY:
        lang = "en"
    return PREMIUM_RESOURCE_LIBRARY[lang].get(category, ())
