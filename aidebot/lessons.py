from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Lesson:
    title: str
    explanation: str
    exercise: str


@dataclass(frozen=True)
class QuizQuestion:
    question: str
    options: tuple[str, ...]
    correct: int
    explanation: str


LESSON_PATHS: dict[str, dict[str, object]] = {
    "discord": {
        "title": "Discord — les bases",
        "description": "Comprendre l'organisation de Discord avant de construire quoi que ce soit.",
        "lessons": (
            Lesson("Serveur, catégorie et salon", "Un serveur contient des catégories qui regroupent des salons texte ou vocaux. Une structure courte est plus facile à comprendre et à maintenir.", "Crée un serveur test avec 3 catégories maximum et explique le rôle de chaque salon."),
            Lesson("Rôles et hiérarchie", "Les rôles servent à organiser les membres et leurs droits. Un rôle placé plus haut peut gérer certains rôles placés plus bas, selon ses permissions.", "Crée Membre, Helper et Responsable, puis place-les dans un ordre logique."),
            Lesson("Permissions", "Les permissions viennent des rôles puis des overwrites de catégorie et de salon. Évite `Administrateur` quand une permission plus précise suffit.", "Crée un salon staff invisible pour le rôle Membre sans donner Administrateur au staff."),
            Lesson("Bots", "Un bot doit recevoir uniquement les permissions nécessaires. Son rôle doit être au-dessus des rôles qu'il doit attribuer ou modifier.", "Ajoute un bot de test et vérifie sa position dans la hiérarchie."),
            Lesson("Sécurité de base", "Les secrets ne se partagent jamais. Les rôles sensibles sont peu nombreux, les logs sont activés et les permissions sont testées avec un compte membre.", "Fais une checklist de 5 contrôles avant d'ouvrir ton serveur."),
        ),
    },
    "serveur": {
        "title": "Construire un serveur propre",
        "description": "Passer d'une idée à une structure compacte et exploitable.",
        "lessons": (
            Lesson("Définir l'objectif", "Chaque salon et chaque rôle doit servir l'objectif du serveur. Commence par définir ce que le membre doit pouvoir faire dans les premières minutes.", "Écris en une phrase la promesse de ton serveur et les 3 premières actions d'un nouveau membre."),
            Lesson("Architecture compacte", "Moins de salons permanents réduit la confusion. Les tickets, formulaires et panneaux interactifs permettent de garder une structure courte.", "Dessine une structure de 12 à 15 salons maximum."),
            Lesson("Onboarding", "Le membre doit trouver rapidement : ce que propose le serveur, les règles et où commencer.", "Prépare un message de bienvenue qui tient dans un seul embed."),
            Lesson("Support", "Un bon support sépare la question rapide, l'entraide communautaire et le ticket privé quand des informations sensibles ou un suivi sont nécessaires.", "Définis quand utiliser un salon public et quand ouvrir un ticket."),
            Lesson("Vérification finale", "Teste toujours le serveur comme un nouveau membre puis comme un Helper. Vérifie visibilité, envoi de messages, boutons et hiérarchie.", "Fais le test avec un compte sans rôle staff et relève tout accès inattendu."),
        ),
    },
    "permissions": {
        "title": "Permissions et sécurité",
        "description": "Comprendre précisément qui peut faire quoi et pourquoi.",
        "lessons": (
            Lesson("Principe du moindre privilège", "On donne uniquement les droits nécessaires à une tâche. Un Helper qui répond aux tickets n'a pas besoin de gérer le serveur.", "Liste les permissions strictement nécessaires à un Helper."),
            Lesson("Overwrites", "Un salon peut autoriser ou refuser des permissions indépendamment des permissions générales du rôle. Les exceptions doivent rester rares et documentées.", "Configure une catégorie privée puis une exception contrôlée sur un salon."),
            Lesson("Hiérarchie", "Même avec `Gérer les rôles`, un membre ou un bot ne peut pas gérer un rôle supérieur ou égal à son plus haut rôle.", "Explique pourquoi le rôle du bot doit être au-dessus d'un rôle qu'il distribue."),
            Lesson("Permissions dangereuses", "Administrateur, Gérer le serveur, Gérer les rôles, Gérer les webhooks et certaines permissions de modération doivent être limitées.", "Repère tous les rôles sensibles sur un serveur test."),
            Lesson("Fail-closed", "Si le système ne sait pas clairement si une action est autorisée, il la refuse. C'est plus sûr qu'une permission implicite.", "Écris une règle : que doit faire le bot si la configuration d'une permission est absente ?"),
        ),
    },
    "bot": {
        "title": "Premier bot Discord",
        "description": "Créer un bot simple sans mauvaises pratiques de sécurité.",
        "lessons": (
            Lesson("Projet et dépendances", "Sépare le point d'entrée, la configuration et les fonctionnalités. Garde un `requirements.txt` ou équivalent reproductible.", "Crée un dossier de projet avec `main.py`, un module de configuration et un dossier de commandes."),
            Lesson("Token", "Le token est un secret équivalent à un mot de passe du bot. Il doit rester dans une variable d'environnement, jamais dans GitHub.", "Configure `DISCORD_TOKEN` dans un fichier `.env` local ignoré par Git."),
            Lesson("Intentions Discord", "Les intents définissent les événements reçus par le bot. Certains sont privilégiés et doivent être activés dans le Developer Portal.", "Identifie si ton bot a vraiment besoin de Server Members Intent ou Message Content Intent."),
            Lesson("Commandes slash", "Les slash commands donnent une interface claire, typée et découvrable. Valide les permissions avant toute action sensible.", "Crée `/ping` puis une commande qui accepte un membre en paramètre."),
            Lesson("Erreurs et logs", "Une erreur utilisateur doit produire un message clair ; une erreur interne doit être loguée sans exposer de secret.", "Ajoute un gestionnaire global d'erreurs qui répond de façon générique au membre."),
            Lesson("Déploiement", "Avant de déployer : compilation, tests, variables d'environnement et stockage persistant si le bot garde des données.", "Écris une checklist de déploiement avant de lancer ton bot 24/7."),
        ),
    },
}


QUIZZES: dict[str, tuple[QuizQuestion, ...]] = {
    "discord": (
        QuizQuestion("À quoi sert principalement une catégorie Discord ?", ("À bannir des membres", "À regrouper des salons", "À héberger un bot", "À créer des invitations"), 1, "Une catégorie sert principalement à organiser plusieurs salons et leurs permissions."),
        QuizQuestion("Quelle pratique est la plus sûre ?", ("Donner Administrateur aux Helpers", "Tester les permissions avec un compte membre", "Partager un token en ticket privé", "Mettre tous les salons publics"), 1, "Tester les permissions avec un compte membre permet de voir ce qu'un utilisateur réel peut réellement faire."),
    ),
    "permissions": (
        QuizQuestion("Que signifie le principe du moindre privilège ?", ("Donner tous les droits au staff", "Donner uniquement les droits nécessaires", "Refuser tous les rôles", "Utiliser uniquement Administrateur"), 1, "On attribue seulement les capacités nécessaires à la tâche."),
        QuizQuestion("Un bot avec Gérer les rôles peut-il attribuer un rôle placé au-dessus de son propre rôle ?", ("Oui toujours", "Oui si le serveur est petit", "Non", "Seulement en vocal"), 2, "La hiérarchie Discord empêche le bot de gérer un rôle supérieur ou égal à son plus haut rôle."),
    ),
    "serveur": (
        QuizQuestion("Quel onboarding est le plus clair ?", ("50 salons dès l'arrivée", "Une entrée claire avec règles et action suivante", "Aucun message de bienvenue", "Tout expliquer uniquement en vocal"), 1, "Un nouveau membre doit comprendre rapidement le serveur et sa prochaine action."),
        QuizQuestion("Pourquoi limiter le nombre de salons permanents ?", ("Pour éviter Discord Nitro", "Pour réduire la confusion et la maintenance", "Pour empêcher les bots", "Pour supprimer les rôles"), 1, "Une structure compacte est plus facile à découvrir et à maintenir."),
    ),
    "bot": (
        QuizQuestion("Où stocker le token d'un bot ?", ("Dans le README", "Dans GitHub", "Dans une variable d'environnement", "Dans le nom du bot"), 2, "Les secrets doivent rester hors du code et du dépôt."),
        QuizQuestion("Pourquoi utiliser des tests avant un déploiement ?", ("Pour changer la couleur du bot", "Pour détecter des régressions avant la mise en ligne", "Pour obtenir plus de permissions", "Pour éviter les slash commands"), 1, "Les tests réduisent le risque de mettre en ligne une régression connue."),
    ),
}


GLOSSARY = {
    "intent": "Un intent indique à Discord quels événements le bot veut recevoir. Certains intents sont privilégiés et doivent aussi être activés dans le Developer Portal.",
    "overwrite": "Une permission spécifique appliquée à un rôle ou membre sur une catégorie ou un salon.",
    "hiérarchie": "Ordre vertical des rôles Discord. Il limite notamment quels rôles un membre ou un bot peut gérer.",
    "ephemeral": "Réponse Discord visible uniquement par la personne qui a lancé l'interaction.",
    "embed": "Bloc de message structuré avec titre, description, champs, image ou footer.",
    "webhook": "URL ou intégration permettant à une application d'envoyer des messages ou événements. Sa gestion est sensible.",
    "fail-closed": "Stratégie de sécurité : si l'autorisation n'est pas clairement établie, l'action est refusée.",
    "cooldown": "Limite temporaire empêchant une commande d'être utilisée trop fréquemment.",
}


def get_lesson(path: str, number: int) -> Lesson | None:
    data = LESSON_PATHS.get(path.casefold().strip())
    if not data:
        return None
    lessons = data["lessons"]
    if not isinstance(lessons, tuple) or number < 1 or number > len(lessons):
        return None
    return lessons[number - 1]


def path_size(path: str) -> int:
    data = LESSON_PATHS.get(path.casefold().strip())
    if not data:
        return 0
    lessons = data["lessons"]
    return len(lessons) if isinstance(lessons, tuple) else 0


def glossary_lookup(term: str) -> str | None:
    needle = term.casefold().strip()
    if needle in GLOSSARY:
        return GLOSSARY[needle]
    for key, value in GLOSSARY.items():
        if needle and (needle in key or needle in value.casefold()):
            return f"**{key}** — {value}"
    return None
