from __future__ import annotations

BANNER_URL = "https://raw.githubusercontent.com/eventore4567/aide-bot-/main/assets/aidebot-banner.jpg"

VIDEO_LIBRARY = {
    "serveur": {
        "title": "Créer un serveur Discord complet — structure, rôles et permissions",
        "url": "https://www.youtube.com/watch?v=1xKPtNy1PjM",
        "note": "Vidéo complémentaire pour voir la création d’un serveur de A à Z. Utilise-la comme support visuel, puis reviens au guide Aide Bot pour vérifier ta configuration.",
    },
    "permissions": {
        "title": "Rôles et permissions Discord — guide administrateur",
        "url": "https://www.youtube.com/watch?v=-8oBZecjbv4",
        "note": "Support visuel pour revoir la hiérarchie, les rôles et les permissions de salons. Ne donne pas Administrateur par facilité : vérifie toujours le besoin réel.",
    },
    "bot": {
        "title": "Créer un bot Discord en Python — cours complet",
        "url": "https://www.youtube.com/watch?v=Y2-XYbVcqiQ",
        "note": "Cours vidéo long sur discord.py : Developer Portal, commandes, embeds, cogs et slash commands. Garde le token hors du code et de GitHub.",
    },
}

GUIDES = {
    "discord": {
        "title": "Discord — comprendre les bases correctement",
        "subtitle": "Un vrai point de départ pour comprendre ce que tu manipules avant de modifier des permissions ou d’ajouter des bots.",
        "sections": (
            (
                "1. Comment Discord est organisé",
                "Un serveur Discord est une structure composée de catégories, de salons texte ou vocaux, de rôles et de membres. Les catégories servent surtout à regrouper les salons et à appliquer des permissions communes. Un bon serveur n’a pas besoin de dizaines de salons : chaque espace doit avoir une utilité claire. Avant de créer quoi que ce soit, demande-toi ce qu’un nouveau membre doit comprendre et faire dans ses cinq premières minutes.",
            ),
            (
                "2. Rôles, hiérarchie et responsabilités",
                "Les rôles servent à organiser les membres et à leur attribuer des capacités. La position d’un rôle dans la liste est importante : un membre ne peut pas gérer un rôle placé au-dessus ou au même niveau que son rôle le plus haut. Pour un bot, c’est pareil. Si ton bot doit attribuer le rôle Membre ou Modérateur, son propre rôle doit être placé au-dessus de ces rôles. Évite de donner Administrateur si quelques permissions précises suffisent.",
            ),
            (
                "3. La règle à retenir",
                "Teste toujours ton serveur avec un compte ou un rôle de membre normal. Beaucoup d’erreurs de permissions ne se voient pas avec un compte propriétaire, car le propriétaire contourne une partie des restrictions. Vérifie la visibilité des salons, l’envoi de messages, les pièces jointes, les commandes de bots et les espaces staff avant d’ouvrir le serveur au public.",
            ),
        ),
        "example": "Exemple propre : 4 catégories — Accueil, Communauté, Aide, Staff. Le membre voit Accueil/Communauté/Aide. Le staff voit aussi Staff. Les tickets sont privés et créés uniquement quand ils sont nécessaires.",
        "mistakes": "Créer 40 salons dès le départ • donner Administrateur à tous les rôles staff • oublier de tester avec un membre normal • placer le rôle du bot sous les rôles qu’il doit gérer.",
        "video_key": "serveur",
    },
    "serveur": {
        "title": "Créer un serveur propre et professionnel",
        "subtitle": "Construire un serveur qui donne immédiatement une impression sérieuse, claire et facile à utiliser.",
        "sections": (
            (
                "1. Commence par le parcours du membre",
                "Ne commence pas par les noms de salons. Commence par le parcours : arrivée → règles → présentation du service → action principale → aide si besoin. Si ton serveur vend un service, l’utilisateur doit comprendre en quelques secondes ce qui est gratuit, ce qui est payant, comment commander et où poser une question. Un serveur propre guide le membre au lieu de lui demander de deviner quelle commande utiliser.",
            ),
            (
                "2. Fais une architecture courte",
                "Une structure professionnelle peut rester compacte : bienvenue, annonces, règlement, offres ou formations, ressources, entraide, avis et quelques salons staff. Les tickets permettent de créer des espaces temporaires au lieu de garder vingt salons support permanents. Les noms doivent être cohérents, lisibles et utiles sur téléphone comme sur ordinateur.",
            ),
            (
                "3. Termine par un vrai test",
                "Teste l’onboarding avec un compte sans rôle, puis avec un Helper, un Formateur et un Responsable. Vérifie que chaque rôle voit uniquement ce dont il a besoin. Clique sur tous les boutons, ouvre un ticket, ferme-le, teste les logs et vérifie que le bot continue à fonctionner après un redémarrage. Un serveur n’est pas prêt parce qu’il est joli : il est prêt quand le parcours complet fonctionne.",
            ),
        ),
        "example": "Un nouveau membre arrive, lit un seul panneau principal, clique sur « Commencer gratuitement », choisit un guide, puis ouvre un ticket seulement s’il reste bloqué. Aucun slash command n’est obligatoire pour commencer.",
        "mistakes": "Trop de salons • panneaux sans explication • offres Free/Premium mélangées • aucune procédure de ticket • permissions configurées uniquement depuis le compte propriétaire.",
        "video_key": "serveur",
    },
    "permissions": {
        "title": "Permissions Discord — comprendre avant d’autoriser",
        "subtitle": "La partie qui casse le plus souvent les serveurs : rôles, overwrites, hiérarchie et droits sensibles.",
        "sections": (
            (
                "1. Les permissions viennent de plusieurs niveaux",
                "Les permissions générales viennent des rôles. Une catégorie ou un salon peut ensuite ajouter des autorisations ou des refus spécifiques. C’est ce qu’on appelle souvent les overwrites. Pour éviter les configurations impossibles à comprendre, règle d’abord les permissions au niveau des rôles et des catégories, puis crée seulement quelques exceptions au niveau des salons.",
            ),
            (
                "2. Permissions dangereuses",
                "Administrateur contourne pratiquement toutes les restrictions et doit rester exceptionnel. Gérer les rôles, Gérer le serveur, Gérer les webhooks, Bannir des membres et certaines permissions de modération peuvent aussi provoquer de gros dégâts. Donne une capacité parce qu’elle est nécessaire à une tâche précise, pas parce que « ça marche mieux comme ça ».",
            ),
            (
                "3. Hiérarchie et bots",
                "Même si un bot possède Gérer les rôles, il ne peut pas attribuer ou modifier un rôle supérieur ou égal à son propre rôle le plus haut. Si une commande répond qu’elle n’a pas la permission alors que la case est cochée, regarde immédiatement la position du rôle du bot. C’est l’une des causes les plus fréquentes de systèmes de rôles qui semblent cassés.",
            ),
        ),
        "example": "Helper : Voir les tickets + répondre. Formateur : mêmes droits + gérer une formation. Responsable : superviser les tickets et les formations. Direction : configuration sensible. Aucun de ces rôles n’a besoin d’Administrateur par défaut.",
        "mistakes": "Empiler des refus/autorisations contradictoires • mettre Administrateur partout • oublier la hiérarchie • tester uniquement avec le propriétaire • laisser @everyone voir des salons staff.",
        "video_key": "permissions",
    },
    "bot": {
        "title": "Créer un vrai bot Discord en Python",
        "subtitle": "Du Developer Portal au déploiement : structure, token, slash commands, erreurs, données et hébergement.",
        "sections": (
            (
                "1. Crée l’application proprement",
                "Dans le Discord Developer Portal, crée une application puis son bot. Le token est le mot de passe du bot : il ne doit jamais être collé dans un message public, un fichier envoyé à quelqu’un ou un dépôt GitHub. En local, utilise une variable d’environnement. Sur Railway ou un autre hébergeur, configure le token dans les variables du service. Si un token a fuité, régénère-le immédiatement.",
            ),
            (
                "2. Structure ton code dès le début",
                "Garde un point d’entrée simple et sépare les fonctionnalités importantes dans des modules ou des cogs. Utilise les slash commands pour les actions destinées aux utilisateurs, valide les permissions avant toute modification sensible et renvoie des erreurs compréhensibles. Les logs internes doivent donner assez d’informations pour diagnostiquer un crash sans exposer de secrets.",
            ),
            (
                "3. Déployer ne veut pas dire sauvegarder",
                "Un bot hébergé 24/7 peut redémarrer ou être redéployé. Si tu utilises SQLite sans stockage persistant, ta base peut disparaître. Utilise un volume persistant ou une vraie base de données selon ton besoin. Avant chaque déploiement : lance les tests, vérifie les variables, la base, les intents Discord et les permissions du rôle du bot.",
            ),
        ),
        "example": "Flux recommandé : code sur une branche → tests automatiques → pull request → merge sur main → déploiement → vérification des logs → test d’une vraie commande sur Discord.",
        "mistakes": "Token dans GitHub • tout mettre dans main.py • aucune gestion d’erreur • base SQLite éphémère • déployer directement sans tests • donner Administrateur au bot sans raison.",
        "video_key": "bot",
    },
    "tickets": {
        "title": "Tickets support — fonctionner comme un vrai service",
        "subtitle": "Un ticket ne doit pas être juste un salon privé : il doit avoir un propriétaire, un statut, une procédure et une fin claire.",
        "sections": (
            (
                "1. À l’ouverture",
                "Le ticket doit expliquer ce que le membre a demandé, son objectif, son niveau, ses disponibilités et le type de service. Le bot doit rappeler ce que le membre peut envoyer : captures, messages d’erreur et contexte. Il doit aussi préciser de ne jamais envoyer de token, mot de passe ou autre secret.",
            ),
            (
                "2. Prise en charge",
                "Un Helper, Formateur, Responsable, Administrateur autorisé ou le propriétaire peut prendre le ticket selon le type de demande. L’attribution doit être atomique : deux personnes qui cliquent en même temps ne doivent jamais devenir propriétaires du même ticket. Après la prise en charge, le bot affiche clairement qui s’occupe du membre et quelle est la prochaine étape.",
            ),
            (
                "3. Résolution et fermeture",
                "Quand le problème est résolu, le staff marque la demande terminée. Le membre peut laisser un avis, puis le ticket passe en lecture seule ou est archivé. Les actions importantes sont journalisées. Pour une offre Premium, la prise en charge ne commence qu’après confirmation du paiement par le rôle autorisé.",
            ),
        ),
        "example": "Ticket #42 — Type : aide gratuite • Pris en charge par @Helper • Statut : diagnostic • Prochaine étape : vérifier les permissions du rôle du bot • Résultat final : corrigé + explication donnée au membre.",
        "mistakes": "Deux staff sur le même ticket • ticket sans contexte • fermeture brutale • paiement Premium non confirmé • aucune trace de qui a fait quoi • demander des secrets au membre.",
        "video_key": "serveur",
    },
}

FREE_DESCRIPTION = (
    "Aide Bot ne bloque pas les bases derrière un paiement. La partie gratuite contient des guides complets, "
    "des exemples, des vidéos, des quiz, des ressources et l’entraide communautaire. Le but est que tu puisses "
    "comprendre et refaire seul, pas seulement recopier une commande."
)

PREMIUM_DESCRIPTION = (
    "Le Premium vend surtout du temps humain et un accompagnement personnalisé : diagnostic, plan sur mesure, "
    "ticket privé, Formateur dédié, rendez-vous, audit, exercices, vérification finale et suivi. Le contenu gratuit "
    "reste utile même sans achat."
)
