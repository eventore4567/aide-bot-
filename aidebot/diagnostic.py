from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class DiagnosticRoute:
    key: str
    title: str
    keywords: tuple[str, ...]
    learning_path: str | None
    training_key: str | None
    resource_key: str | None
    challenge_key: str | None
    help_hint: str


@dataclass(frozen=True)
class DiagnosticResult:
    route: DiagnosticRoute
    confidence: str
    score: int
    secondary: DiagnosticRoute | None
    urgent_security: bool


ROUTES: tuple[DiagnosticRoute, ...] = (
    DiagnosticRoute(
        key="discord",
        title="Débuter sur Discord",
        keywords=(
            "discord", "debutant", "debuter", "salon", "message", "categorie",
            "interface", "mention", "vocal", "serveur discord",
        ),
        learning_path="discord",
        training_key="discord",
        resource_key=None,
        challenge_key=None,
        help_hint="Commence par le mini-parcours Discord. Si une notion reste floue, demande ensuite un Helper.",
    ),
    DiagnosticRoute(
        key="serveur",
        title="Créer et organiser un serveur",
        keywords=(
            "creer serveur", "creation serveur", "organiser serveur", "structure", "onboarding",
            "categorie", "salons", "reglement", "bienvenue", "communaute", "serveur pro",
        ),
        learning_path="serveur",
        training_key="serveur",
        resource_key="serveur",
        challenge_key="serveur-1",
        help_hint="Travaille d’abord la structure, puis teste les rôles et permissions avec un compte membre.",
    ),
    DiagnosticRoute(
        key="permissions",
        title="Permissions, modération et sécurité",
        keywords=(
            "permission", "permissions", "role", "roles", "hierarchie", "administrateur",
            "admin", "moderation", "securite", "raid", "anti raid", "kick", "ban",
            "overwrite", "staff prive", "salon prive", "hack", "compromis",
        ),
        learning_path="permissions",
        training_key="permissions",
        resource_key="permissions",
        challenge_key="permissions-1",
        help_hint="Ne donne pas Administrateur par facilité. Vérifie la hiérarchie et les overwrites avant toute autre correction.",
    ),
    DiagnosticRoute(
        key="bot",
        title="Créer ou corriger un bot Discord",
        keywords=(
            "bot", "python", "discord.py", "commande slash", "slash", "code", "github",
            "railway", "token", "deploy", "deploiement", "database", "base de donnees",
            "erreur bot", "intents", "api",
        ),
        learning_path="bot",
        training_key="bot",
        resource_key="bot",
        challenge_key="bot-1",
        help_hint="Commence par isoler l’erreur exacte et ne partage jamais le token du bot.",
    ),
    DiagnosticRoute(
        key="support",
        title="Tickets, support et organisation du staff",
        keywords=(
            "ticket", "support", "helper", "formateur", "staff", "recrutement", "candidature",
            "prise en charge", "logs", "avis", "planning", "middle man", "moderateur",
        ),
        learning_path=None,
        training_key="serveur-pro",
        resource_key="tickets",
        challenge_key="helper-1",
        help_hint="Commence par clarifier qui peut voir, prendre, traiter et fermer chaque type de demande.",
    ),
)

_SECURITY_URGENT_PHRASES = (
    "token expose", "token leak", "token vole", "token compromis", "bot hack",
    "compte hack", "serveur raid", "en train de raid", "compromis", "pirate",
)


def _normalize(text: str) -> str:
    raw = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(ch for ch in raw if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents).strip()


def _score(text: str, route: DiagnosticRoute) -> int:
    tokens = set(re.findall(r"[a-z0-9.+#-]{2,}", text))
    score = 0
    for keyword in route.keywords:
        normalized = _normalize(keyword)
        if " " in normalized:
            if normalized in text:
                score += 5
        elif normalized in tokens:
            score += 3
        elif normalized in text and len(normalized) >= 5:
            score += 1
    return score


def diagnose(problem: str) -> DiagnosticResult:
    text = _normalize(problem)
    ranked = sorted(((_score(text, route), route) for route in ROUTES), key=lambda item: (-item[0], item[1].key))
    best_score, best_route = ranked[0]
    second_score, second_route = ranked[1]

    if best_score <= 0:
        best_route = ROUTES[0]
        second_route = None
        confidence = "faible"
    elif best_score >= 8 and best_score - second_score >= 3:
        confidence = "élevée"
    elif best_score >= 4:
        confidence = "moyenne"
    else:
        confidence = "faible"

    secondary = second_route if second_score > 0 and second_score >= best_score - 2 else None
    urgent = any(phrase in text for phrase in _SECURITY_URGENT_PHRASES)
    if urgent:
        security = next(route for route in ROUTES if route.key == "permissions")
        best_route = security
        best_score = max(best_score, 10)
        confidence = "élevée"
        secondary = None

    return DiagnosticResult(
        route=best_route,
        confidence=confidence,
        score=best_score,
        secondary=secondary,
        urgent_security=urgent,
    )


def recommended_commands(result: DiagnosticResult) -> list[str]:
    route = result.route
    commands: list[str] = []
    if route.learning_path:
        commands.append(f"`/apprendre reprendre` ou `/apprendre lecon sujet:{route.learning_path} numero:1`")
    if route.resource_key:
        commands.append(f"`/ressource nom:{route.resource_key}`")
    if route.challenge_key:
        commands.append(f"Challenge conseillé : `{route.challenge_key}` via `/challenge liste`")
    commands.append("`/chercher question:...` pour vérifier la base de connaissances")
    commands.append("`/aide demander question:...` si tu as besoin d’un Helper")
    if route.training_key:
        commands.append(f"Formation accompagnée : `/parcours formation:{route.training_key}`")
    return commands
