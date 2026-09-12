from __future__ import annotations

import re
from dataclasses import dataclass

import discord
from discord.ext import commands

import aidebot.cogs.center_autopost as center_autopost
import aidebot.cogs.product_experience_v51 as product_v51
import aidebot.cogs.setup_server as setup_server
from aidebot.cogs.assistant_guardian_v52 import AskAIModal
from aidebot.experience_content import BANNER_URL

COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F

CENTER_CHANNEL = "🎓・centre-aide"
QUICK_CHANNEL = "🆘・aide-rapide"
GUIDES_CHANNEL = "📚・guides"
AI_CHANNEL = "🤖・assistant-aide"
HELP_CATEGORY = "━━ AIDE & FORMATIONS ━━"
CENTER_TITLE = "Aide Bot — Centre d’aide"
QUICK_TITLE = "Aide Bot — Aide rapide"
GUIDES_TITLE = "Aide Bot — Guides"


@dataclass(frozen=True)
class HelpCard:
    key: str
    category: str
    label: str
    description: str
    keywords: tuple[str, ...]
    checks: tuple[str, ...]
    fixes: tuple[str, ...]
    support_type: str


HELP_CATEGORIES: dict[str, tuple[str, str]] = {
    "discord": ("Discord", "Interface, compte, notifications et comportement du client Discord."),
    "permissions": ("Rôles & permissions", "Accès aux salons, héritage, hiérarchie et permissions effectives."),
    "server": ("Serveur", "Structure, onboarding, catégories, rôles et organisation générale."),
    "tickets": ("Tickets & support", "Ouverture, doublons, accès, suivi et problèmes de prise en charge."),
    "bots": ("Bots & commandes", "Bot hors ligne, commandes absentes, intents, invitations et permissions."),
    "hosting": ("Hébergement", "Railway, redémarrages, variables, volumes et déploiements."),
    "code": ("Code & données", "Python, discord.py, erreurs, GitHub, SQLite et dépendances."),
    "security": ("Sécurité", "Raid, token, webhooks, bots suspects et permissions dangereuses."),
}


def _card(
    key: str,
    category: str,
    label: str,
    description: str,
    keywords: tuple[str, ...],
    checks: tuple[str, ...],
    fixes: tuple[str, ...],
    support_type: str,
) -> HelpCard:
    return HelpCard(key, category, label, description, keywords, checks, fixes, support_type)


HELP_CARDS: dict[str, HelpCard] = {
    "cant_see_channel": _card(
        "cant_see_channel", "permissions", "Je ne vois pas un salon", "Un salon ou une catégorie est invisible alors qu’il devrait être accessible.",
        ("vois pas", "voir salon", "invisible", "salon cache", "salon caché", "acces salon", "accès salon"),
        ("Vérifie `Voir le salon` sur @everyone puis sur ton rôle.", "Vérifie les overwrites de la catégorie ET du salon.", "Vérifie qu’un autre rôle ne pose pas un deny explicite."),
        ("Corrige d’abord la catégorie puis synchronise le salon si elle porte la règle.", "Évite les denies inutiles sur plusieurs rôles.", "Teste avec un vrai membre qui possède exactement les rôles concernés."),
        "serveur",
    ),
    "cant_send": _card(
        "cant_send", "permissions", "Je peux voir mais pas écrire", "Le salon est visible mais l’envoi de messages est bloqué.",
        ("pas ecrire", "pas écrire", "envoyer message", "send messages", "lecture seule", "read only"),
        ("Contrôle `Envoyer des messages` sur la catégorie.", "Contrôle l’overwrite du salon pour ton rôle.", "Vérifie si le salon est volontairement en lecture seule."),
        ("Autorise l’écriture uniquement au rôle nécessaire.", "Garde les salons d’information en lecture seule.", "Évite d’accorder `Administrateur` juste pour contourner un deny."),
        "serveur",
    ),
    "role_hierarchy": _card(
        "role_hierarchy", "permissions", "Je ne peux pas gérer un rôle", "Un bot ou un membre staff n’arrive pas à attribuer/modifier un rôle.",
        ("gerer role", "gérer rôle", "role hierarchy", "hierarchie", "hiérarchie", "attribuer role", "attribuer rôle"),
        ("Compare la position du rôle du bot/staff avec le rôle cible.", "Vérifie `Gérer les rôles`.", "Vérifie que le rôle cible n’est pas un rôle géré par une intégration."),
        ("Place le rôle du bot au-dessus des rôles qu’il doit gérer.", "N’accorde pas Administrateur si `Gérer les rôles` suffit.", "Teste ensuite l’attribution sur un rôle non géré."),
        "serveur",
    ),
    "category_inheritance": _card(
        "category_inheritance", "permissions", "Permissions différentes de la catégorie", "Un salon n’hérite plus des permissions attendues de sa catégorie.",
        ("categorie", "catégorie", "synchroniser", "heritage", "héritage", "overwrite"),
        ("Compare les overwrites du salon et de la catégorie.", "Repère les permissions ajoutées directement sur le salon.", "Vérifie les denies issus des rôles cumulés."),
        ("Synchronise le salon si aucune exception n’est voulue.", "Garde les exceptions uniquement sur les salons qui en ont réellement besoin.", "Documente les exceptions staff importantes."),
        "serveur",
    ),
    "bot_offline": _card(
        "bot_offline", "bots", "Le bot est hors ligne", "Le bot ne se connecte plus ou disparaît juste après le démarrage.",
        ("hors ligne", "offline", "bot off", "bot crash", "deconnecte", "déconnecte"),
        ("Regarde les logs de démarrage sur l’hébergeur.", "Vérifie que le token est présent sans l’envoyer dans Discord.", "Vérifie les intents requis dans le Developer Portal."),
        ("Corrige la première erreur fatale des logs avant le reste.", "Redémarre seulement après la correction.", "Si le token a été exposé, régénère-le immédiatement."),
        "bot",
    ),
    "command_missing": _card(
        "command_missing", "bots", "Une commande n’apparaît pas", "Une slash command ou interaction attendue n’est pas visible.",
        ("commande absente", "commande apparait pas", "commande apparaît pas", "slash", "sync command", "synchronisee", "synchronisée"),
        ("Vérifie que la commande est bien synchronisée dans les logs.", "Vérifie que le bot a été invité avec `applications.commands`.", "Vérifie si la commande est globale ou limitée à un serveur de test."),
        ("Resynchronise une seule fois après la modification.", "Évite de recréer plusieurs commandes identiques.", "Attends la propagation des commandes globales si nécessaire."),
        "bot",
    ),
    "bot_permissions": _card(
        "bot_permissions", "bots", "Le bot répond permission refusée", "Le bot fonctionne mais une action précise est refusée par Discord.",
        ("permission bot", "forbidden", "missing permissions", "403", "pas la permission"),
        ("Lis la permission exacte manquante dans l’erreur.", "Vérifie les permissions du rôle du bot.", "Vérifie aussi la hiérarchie des rôles pour les actions de rôle/modération."),
        ("Accorde uniquement la permission nécessaire.", "Place le rôle bot correctement dans la hiérarchie.", "Relance l’action sans réinviter le bot si les permissions suffisent."),
        "bot",
    ),
    "intents": _card(
        "intents", "bots", "Le bot ne voit pas les membres/événements", "Certaines fonctionnalités ne reçoivent pas les événements Discord attendus.",
        ("intent", "members intent", "message content", "voit pas membre", "event marche pas"),
        ("Vérifie les intents demandés dans le code.", "Vérifie les Privileged Gateway Intents dans le Developer Portal.", "Confirme que la fonctionnalité dépend réellement de cet intent."),
        ("Active seulement les intents nécessaires.", "Redémarre le bot après modification du Developer Portal.", "Ne contourne pas un intent manquant avec des permissions Administrateur."),
        "bot",
    ),
    "railway_restart": _card(
        "railway_restart", "hosting", "Railway redémarre le bot", "Le service redémarre, crash ou boucle après le lancement.",
        ("railway restart", "railway redemarre", "railway redémarre", "restart", "crash loop", "container"),
        ("Lis les deploy logs juste avant le redémarrage.", "Vérifie le start command.", "Vérifie si l’application quitte volontairement avec une exception."),
        ("Corrige l’exception avant de redeployer.", "Garde un restart policy raisonnable, pas une boucle infinie masquant le bug.", "Teste le même point d’entrée localement ou en CI."),
        "bot",
    ),
    "railway_volume": _card(
        "railway_volume", "hosting", "Mes données disparaissent après un restart", "Une DB ou des fichiers semblent revenir à zéro après redémarrage.",
        ("donnees perdues", "données perdues", "volume", "sqlite perdu", "reset db", "restart data"),
        ("Vérifie qu’un volume est monté.", "Vérifie que le chemin DB pointe DANS le volume.", "Vérifie les logs de montage au démarrage."),
        ("Utilise un chemin persistant comme `/data/...` sur Railway.", "Ne stocke pas les données critiques uniquement dans le filesystem éphémère.", "Sauvegarde avant toute migration de schéma."),
        "bot",
    ),
    "env_missing": _card(
        "env_missing", "hosting", "Une variable d’environnement manque", "Le bot démarre mal ou une fonction reste désactivée faute de configuration.",
        ("env", "variable", "api key", "missing variable", "absent", "openai_api_key"),
        ("Identifie le NOM de variable demandé par le log.", "Vérifie qu’elle existe dans le bon service/environnement.", "Ne colle jamais sa valeur dans un salon Discord."),
        ("Ajoute la variable dans l’hébergeur puis redeploie si nécessaire.", "Utilise des valeurs différentes entre test et production.", "Régénère tout secret déjà exposé."),
        "bot",
    ),
    "python_traceback": _card(
        "python_traceback", "code", "J’ai une erreur Python", "Une exception ou traceback empêche une fonctionnalité de marcher.",
        ("traceback", "python error", "exception", "typeerror", "attributeerror", "nameerror", "importerror"),
        ("Lis la dernière exception du traceback avant les lignes internes.", "Repère le fichier et la ligne de ton code.", "Reproduis le bug avec l’entrée minimale."),
        ("Corrige la cause, pas seulement le message visible.", "Ajoute un test qui reproduit le bug.", "Évite les `except Exception: pass` qui cachent l’erreur."),
        "bot",
    ),
    "dependency": _card(
        "dependency", "code", "Module Python introuvable", "Le déploiement échoue avec ModuleNotFoundError ou dépendance absente.",
        ("modulenotfound", "module not found", "requirements", "pip", "dependency", "dependance", "dépendance"),
        ("Vérifie le nom importé.", "Vérifie `requirements.txt`.", "Vérifie que la version Python est compatible."),
        ("Ajoute la dépendance réellement utilisée avec une version compatible.", "Relance la CI avant le déploiement.", "Supprime les dépendances inutilisées plutôt que d’empiler des packages."),
        "bot",
    ),
    "database_locked": _card(
        "database_locked", "code", "SQLite est locked / lent", "La base SQLite retourne locked, timeout ou comportements concurrents étranges.",
        ("database locked", "sqlite locked", "db locked", "database is locked", "sqlite"),
        ("Vérifie les écritures concurrentes.", "Vérifie que les transactions sont fermées/commit correctement.", "Vérifie que le fichier DB est sur un stockage persistant approprié."),
        ("Sérialise les écritures critiques ou utilise une couche async adaptée.", "Ajoute des timeouts raisonnables.", "Passe à Postgres si la charge multi-instance dépasse SQLite."),
        "bot",
    ),
    "git_conflict": _card(
        "git_conflict", "code", "Git / GitHub bloque mon push", "Push refusé, branche en retard ou conflit de fusion.",
        ("git conflict", "merge conflict", "push rejected", "non fast forward", "github push", "branche"),
        ("Vérifie ta branche actuelle.", "Vérifie `git status` avant toute manipulation.", "Compare le commit local au remote avant de forcer quoi que ce soit."),
        ("Récupère les changements puis résous le conflit fichier par fichier.", "Évite `--force` sur main sauf cas maîtrisé.", "Passe par une branche + PR pour les changements importants."),
        "bot",
    ),
    "ticket_cant_open": _card(
        "ticket_cant_open", "tickets", "Je n’arrive pas à ouvrir un ticket", "Le panneau ticket ne crée rien ou refuse la demande.",
        ("ticket marche pas", "ticket ne s'ouvre pas", "ouvrir ticket", "ticket refuse", "support bloque"),
        ("Vérifie si tu as déjà une demande active.", "Vérifie que le bot peut créer et gérer des salons.", "Vérifie que le module de tickets est chargé."),
        ("Ferme/réutilise le ticket existant plutôt que d’en créer plusieurs.", "Corrige uniquement la permission manquante du bot.", "Utilise le bon type de support pour obtenir le bon formulaire."),
        "other",
    ),
    "ticket_duplicate": _card(
        "ticket_duplicate", "tickets", "J’ai plusieurs tickets pour le même problème", "Des demandes en double rendent le suivi confus.",
        ("ticket doublon", "duplicate ticket", "deux tickets", "plusieurs tickets", "ticket double"),
        ("Cherche la demande active existante.", "Vérifie si le premier ticket est encore ouvert.", "Vérifie si le bouton a été cliqué plusieurs fois pendant un délai réseau."),
        ("Garde un seul dossier par problème.", "Ajoute les nouvelles informations dans le ticket existant.", "Utilise un verrou anti-double création côté bot."),
        "other",
    ),
    "onboarding": _card(
        "onboarding", "server", "Les nouveaux membres sont perdus", "L’arrivée sur le serveur manque de parcours clair.",
        ("onboarding", "nouveau membre", "bienvenue", "membres perdus", "arrivee", "arrivée"),
        ("Vérifie qu’un nouveau membre comprend quoi faire en moins d’une minute.", "Vérifie que les salons importants sont visibles sans bruit inutile.", "Vérifie que les rôles initiaux ne bloquent pas le parcours."),
        ("Garde un accueil court avec 2-3 actions maximum.", "Sépare information, aide et services.", "Teste l’arrivée avec un compte sans rôle staff."),
        "serveur",
    ),
    "server_clutter": _card(
        "server_clutter", "server", "Le serveur a trop de salons", "La structure est difficile à comprendre ou contient trop de doublons.",
        ("trop de salon", "trop de salons", "serveur charge", "serveur chargé", "organisation", "clutter"),
        ("Liste les salons qui ont exactement la même fonction.", "Repère les catégories avec un seul salon inutile.", "Vérifie les anciens panneaux encore présents."),
        ("Fusionne les fonctions proches via menus plutôt que via salons.", "Garde quelques salons spécialisés uniquement quand leur usage est vraiment différent.", "Archive ou supprime seulement après vérification."),
        "serveur",
    ),
    "raid": _card(
        "raid", "security", "Raid / spam en cours", "Plusieurs comptes ou messages arrivent rapidement et perturbent le serveur.",
        ("raid", "spam massif", "mass join", "attaque", "flood"),
        ("Identifie si le problème vient des arrivées, messages, mentions ou webhooks.", "Vérifie les rôles ayant des permissions sensibles.", "Conserve les logs avant nettoyage si possible."),
        ("Active temporairement des protections proportionnées.", "Réduis les permissions @everyone et vérifie les invitations/bots.", "Évite les actions destructrices massives sans snapshot."),
        "security",
    ),
    "token_leak": _card(
        "token_leak", "security", "J’ai exposé un token ou une clé", "Un secret a été envoyé dans un message, un log ou un dépôt.",
        ("token leak", "token expose", "token exposé", "api key leak", "secret leak", "cle api", "clé api"),
        ("Considère le secret comme compromis immédiatement.", "Identifie le service concerné sans republier la valeur.", "Vérifie où le secret a été copié ou commité."),
        ("Révoque/régénère le secret immédiatement.", "Supprime-le des variables/fichiers publics puis redéploie.", "Nettoie l’historique Git si le secret a été commité publiquement."),
        "security",
    ),
    "suspicious_bot": _card(
        "suspicious_bot", "security", "Un bot a trop de permissions", "Une intégration ou un bot possède Administrateur ou des permissions sensibles inutiles.",
        ("bot suspect", "administrateur bot", "admin bot", "permissions dangereuses", "integration"),
        ("Vérifie qui a ajouté le bot et pourquoi.", "Liste ses permissions réellement nécessaires.", "Vérifie les webhooks et rôles gérés associés."),
        ("Retire les permissions inutiles selon le moindre privilège.", "Retire le bot si sa provenance est inconnue ou non fiable.", "Utilise Guardian pour comparer ensuite la configuration."),
        "security",
    ),
    "webhook_abuse": _card(
        "webhook_abuse", "security", "Webhook inconnu ou compromis", "Des messages arrivent via webhook ou une URL de webhook a été exposée.",
        ("webhook", "webhook leak", "webhook spam", "webhook compromis"),
        ("Identifie le salon et le webhook concernés.", "Vérifie l’auteur/usage attendu du webhook.", "Considère une URL exposée comme compromise."),
        ("Supprime ou régénère le webhook compromis.", "Limite `Gérer les webhooks` aux rôles nécessaires.", "Surveille les créations/modifications futures dans les logs."),
        "security",
    ),
    "notifications": _card(
        "notifications", "discord", "Je reçois trop/pas assez de notifications", "Les notifications Discord ne correspondent pas au comportement attendu.",
        ("notification", "ping", "mention", "mute salon", "silencieux", "pas de notif"),
        ("Vérifie les réglages du serveur puis du salon.", "Vérifie si le rôle est réellement mentionné ou seulement affiché.", "Vérifie les paramètres personnels Discord."),
        ("Configure les notifications au niveau le plus spécifique nécessaire.", "Évite les @everyone/@here inutiles.", "Utilise des rôles de notification opt-in quand c’est pertinent."),
        "discord",
    ),
    "discord_cache": _card(
        "discord_cache", "discord", "Discord affiche un ancien état", "Un rôle, nom, panneau ou permission semble ne pas s’être mis à jour.",
        ("cache", "ancien panneau", "pas mis a jour", "pas mis à jour", "discord bug affichage"),
        ("Recharge Discord ou change de salon puis reviens.", "Vérifie l’état réel avec un autre client si possible.", "Vérifie que le bot a réellement édité le bon message/salon."),
        ("Évite de recréer un panneau si une simple édition suffit.", "Nettoie les anciens panneaux en double.", "Si le problème est serveur-side, vérifie les logs du bot plutôt que le cache client."),
        "discord",
    ),
}

QUICK_KEYS = (
    "cant_see_channel", "cant_send", "role_hierarchy", "bot_offline", "command_missing", "bot_permissions",
    "railway_restart", "railway_volume", "python_traceback", "ticket_cant_open", "raid", "token_leak",
)


def _normalize(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"[^a-z0-9àâäéèêëïîôöùûüç' -]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def classify_problem(text: str) -> HelpCard | None:
    normalized = _normalize(text)
    if not normalized:
        return None
    best: tuple[int, HelpCard] | None = None
    for card in HELP_CARDS.values():
        score = 0
        for keyword in card.keywords:
            keyword_n = _normalize(keyword)
            if keyword_n and keyword_n in normalized:
                score += max(2, len(keyword_n.split()))
        for token in _normalize(card.label).split():
            if len(token) >= 4 and token in normalized:
                score += 1
        if score and (best is None or score > best[0]):
            best = (score, card)
    return best[1] if best else None


def help_home_embed() -> discord.Embed:
    e = discord.Embed(
        title=CENTER_TITLE,
        description=(
            "Le Centre d’aide sert d’**orientation**, pas de mur de boutons. Choisis une catégorie : "
            "Aide Bot te montre ensuite uniquement les problèmes et solutions utiles.\n\n"
            "Si tu ne sais pas dans quelle catégorie chercher, utilise **Décrire mon problème**."
        ),
        color=COLOR,
    )
    e.add_field(
        name="Parcours conseillé",
        value="**1.** Identifier le problème → **2.** suivre le diagnostic → **3.** tester la correction → **4.** ticket seulement si ça bloque encore.",
        inline=False,
    )
    e.add_field(
        name="Espaces spécialisés",
        value="`🆘・aide-rapide` pour les pannes courantes • `🤖・assistant-aide` pour une question libre • `📚・guides` pour apprendre en détail.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Une route claire, pas dix boutons identiques")
    return e


def quick_help_embed() -> discord.Embed:
    e = discord.Embed(
        title=QUICK_TITLE,
        description=(
            "Tu as un problème précis maintenant ? Choisis le symptôme le plus proche. "
            "Aide Bot te donne une checklist courte et une correction sûre avant d’escalader au support."
        ),
        color=SUCCESS,
    )
    e.add_field(name="Rapide", value="12 pannes fréquentes couvrent permissions, bots, Railway, code, tickets et sécurité.", inline=True)
    e.add_field(name="Sans spam", value="Le résultat est privé ; le salon reste propre pour tout le monde.", inline=True)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide rapide • symptôme → diagnostic → correction")
    return e


def guides_home_embed() -> discord.Embed:
    e = discord.Embed(
        title=GUIDES_TITLE,
        description=(
            "Bibliothèque de guides Aide Bot. Choisis un domaine puis un problème précis. "
            "Les guides expliquent quoi vérifier, quoi corriger et quelles mauvaises pratiques éviter."
        ),
        color=0xE67E22,
    )
    for key, (label, description) in HELP_CATEGORIES.items():
        count = sum(1 for card in HELP_CARDS.values() if card.category == key)
        e.add_field(name=f"{label} • {count}", value=description, inline=True)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Guides structurés par problème réel")
    return e


def category_embed(category: str) -> discord.Embed:
    label, description = HELP_CATEGORIES[category]
    cards = [card for card in HELP_CARDS.values() if card.category == category]
    e = discord.Embed(title=f"Aide — {label}", description=description, color=COLOR)
    e.add_field(
        name="Problèmes couverts",
        value="\n".join(f"• **{card.label}** — {card.description}" for card in cards)[:1024],
        inline=False,
    )
    e.set_footer(text="Choisis un problème précis dans le menu.")
    return e


def card_embed(card: HelpCard) -> discord.Embed:
    e = discord.Embed(title=card.label, description=card.description, color=COLOR)
    e.add_field(
        name="À vérifier d’abord",
        value="\n".join(f"**{index}.** {item}" for index, item in enumerate(card.checks, start=1)),
        inline=False,
    )
    e.add_field(
        name="Correction recommandée",
        value="\n".join(f"**{index}.** {item}" for index, item in enumerate(card.fixes, start=1)),
        inline=False,
    )
    e.set_footer(text="Teste dans cet ordre. Si ça bloque encore, escalade avec le contexte déjà identifié.")
    return e


class EscalationModal(discord.ui.Modal, title="Escalader au support"):
    problem = discord.ui.TextInput(label="Ce qui bloque encore", style=discord.TextStyle.paragraph, min_length=15, max_length=900)
    context = discord.ui.TextInput(label="Contexte utile", style=discord.TextStyle.paragraph, required=False, max_length=500)
    availability = discord.ui.TextInput(label="Disponibilités", placeholder="Ex: aujourd’hui 18h-21h", max_length=140)

    def __init__(self, bot: commands.Bot, card: HelpCard) -> None:
        super().__init__()
        self.bot = bot
        self.card = card

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Le support est temporairement indisponible.", ephemeral=True)
        existing = await self.bot.db.active_request_for_training(interaction.guild.id, interaction.user.id, "community_help")
        if existing:
            channel = interaction.guild.get_channel(existing["channel_id"]) if existing["channel_id"] else None
            destination = channel.mention if isinstance(channel, discord.TextChannel) else f"ticket #{existing['id']}"
            return await interaction.response.send_message(f"Tu as déjà une demande d’aide active : {destination}.", ephemeral=True)

        objective = (
            f"**Diagnostic automatique :** {self.card.label}\n"
            f"**Catégorie :** {HELP_CATEGORIES[self.card.category][0]}\n"
            f"**Blocage restant :** {str(self.problem).strip()}\n\n"
            f"**Contexte :** {str(self.context).strip() or 'Non précisé'}\n\n"
            "**Vérifications proposées avant escalade :**\n"
            + "\n".join(f"• {item}" for item in self.card.checks)
        )
        await training.create_request_channel(
            interaction,
            "community_help",
            level=f"Diagnostic V54 — {self.card.label}",
            objective=objective,
            availability=str(self.availability).strip(),
            budget="Aide gratuite",
            status="open",
            payment_status="not_required",
            requires_invite=False,
        )


class HelpResultView(discord.ui.View):
    def __init__(self, bot: commands.Bot, card: HelpCard) -> None:
        super().__init__(timeout=900)
        self.bot = bot
        self.card = card

    @discord.ui.button(label="Autre diagnostic", style=discord.ButtonStyle.secondary)
    async def another(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=quick_help_embed(), view=QuickHelpView(self.bot))

    @discord.ui.button(label="Demander à l’IA", style=discord.ButtonStyle.primary)
    async def ai(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        cog = interaction.client.get_cog("AssistantGuardianV52Cog")
        if cog is None or not cog.ai.configured:
            return await interaction.response.send_message(
                "L’assistant IA n’est pas disponible actuellement. Tu peux continuer avec le ticket support.", ephemeral=True
            )
        await interaction.response.send_modal(AskAIModal(cog))

    @discord.ui.button(label="Toujours bloqué → ticket", style=discord.ButtonStyle.success)
    async def ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(EscalationModal(self.bot, self.card))


class QuickSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(label=HELP_CARDS[key].label[:100], value=key, description=HELP_CARDS[key].description[:100])
            for key in QUICK_KEYS
        ]
        super().__init__(
            placeholder="Quel symptôme ressemble au tien ?",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:v54:quick:symptom",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        card = HELP_CARDS[self.values[0]]
        await interaction.response.send_message(embed=card_embed(card), view=HelpResultView(self.bot, card), ephemeral=True)


class DescribeProblemModal(discord.ui.Modal, title="Décrire mon problème"):
    problem = discord.ui.TextInput(
        label="Explique ce qui ne marche pas",
        placeholder="Ex: mon rôle modo voit le salon mais ne peut pas écrire",
        style=discord.TextStyle.paragraph,
        min_length=8,
        max_length=1200,
    )

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        card = classify_problem(str(self.problem))
        if card is None:
            e = discord.Embed(
                title="Je n’ai pas identifié le problème avec assez de certitude",
                description=(
                    "Je préfère ne pas inventer un diagnostic. Essaie `🆘・aide-rapide` avec un symptôme proche, "
                    "pose la question à l’assistant IA, ou ouvre un ticket avec le contexte exact."
                ),
                color=WARNING,
            )
            return await interaction.response.send_message(embed=e, view=FallbackHelpView(self.bot), ephemeral=True)
        await interaction.response.send_message(embed=card_embed(card), view=HelpResultView(self.bot, card), ephemeral=True)


class FallbackHelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=900)
        self.bot = bot

    @discord.ui.button(label="Voir l’aide rapide", style=discord.ButtonStyle.secondary)
    async def quick(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=quick_help_embed(), view=QuickHelpView(self.bot))

    @discord.ui.button(label="Demander à l’IA", style=discord.ButtonStyle.primary)
    async def ai(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        cog = interaction.client.get_cog("AssistantGuardianV52Cog")
        if cog is None or not cog.ai.configured:
            return await interaction.response.send_message("L’assistant IA n’est pas disponible actuellement.", ephemeral=True)
        await interaction.response.send_modal(AskAIModal(cog))


class QuickHelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.add_item(QuickSelect(bot))
        self.bot = bot

    @discord.ui.button(label="Décrire mon problème", style=discord.ButtonStyle.primary, custom_id="aidebot:v54:quick:describe", row=1)
    async def describe(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(DescribeProblemModal(self.bot))


class CategorySelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, *, custom_id: str) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(label=label, value=key, description=description[:100])
            for key, (label, description) in HELP_CATEGORIES.items()
        ]
        super().__init__(placeholder="Choisis un domaine", min_values=1, max_values=1, options=options, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction) -> None:
        category = self.values[0]
        await interaction.response.send_message(embed=category_embed(category), view=CategoryTopicView(self.bot, category), ephemeral=True)


class TopicSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, category: str) -> None:
        self.bot = bot
        self.category = category
        cards = [card for card in HELP_CARDS.values() if card.category == category]
        super().__init__(
            placeholder="Choisis le problème précis",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=card.label[:100], value=card.key, description=card.description[:100]) for card in cards],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        card = HELP_CARDS[self.values[0]]
        await interaction.response.send_message(embed=card_embed(card), view=HelpResultView(self.bot, card), ephemeral=True)


class CategoryTopicView(discord.ui.View):
    def __init__(self, bot: commands.Bot, category: str) -> None:
        super().__init__(timeout=900)
        self.add_item(TopicSelect(bot, category))


class HelpHomeView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(CategorySelect(bot, custom_id="aidebot:v54:center:category"))

    @discord.ui.button(label="Décrire mon problème", style=discord.ButtonStyle.primary, custom_id="aidebot:v54:center:describe", row=1)
    async def describe(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(DescribeProblemModal(self.bot))


class GuidesView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.add_item(CategorySelect(bot, custom_id="aidebot:v54:guides:category"))


class HelpSystemV54Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._ready_guilds: set[int] = set()

    async def cog_load(self) -> None:
        self.bot.add_view(HelpHomeView(self.bot))
        self.bot.add_view(QuickHelpView(self.bot))
        self.bot.add_view(GuidesView(self.bot))

        # Les anciens boutons qui ouvraient le Centre d'aide continuent de
        # fonctionner, mais ouvrent désormais le moteur V54.
        product_v51.help_center_embed_v51 = lambda _vip_price=None: help_home_embed()
        product_v51.HelpCenterViewV51 = lambda _bot: HelpHomeView(self.bot)

        # Les deux chemins historiques de publication du panneau principal
        # utilisent aussi V54, y compris après /setup.
        center_autopost.center_embed = lambda _price=None: help_home_embed()
        center_autopost.CenterView = lambda _center_cog: HelpHomeView(self.bot)
        setup_server.center_embed = lambda _price=None: help_home_embed()
        setup_server.CenterView = lambda _center_cog: HelpHomeView(self.bot)

    async def _configure_channel(self, channel: discord.TextChannel) -> None:
        guild = channel.guild
        try:
            await channel.set_permissions(
                guild.default_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True,
                reason="Aide Bot V54 — aide publique en lecture seule",
            )
            for role_name in ("👑・Direction", "📘・Responsable Formation", "🎓・Formateur", "🤝・Helper"):
                role = discord.utils.get(guild.roles, name=role_name)
                if role is not None:
                    await channel.set_permissions(
                        role,
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_messages=role_name in {"👑・Direction", "📘・Responsable Formation"},
                        reason="Aide Bot V54 — équipe d'aide",
                    )
        except (discord.Forbidden, discord.HTTPException):
            return

    async def _upsert(self, channel: discord.TextChannel, embed: discord.Embed, view: discord.ui.View) -> None:
        setup_cog = self.bot.get_cog("SetupServerCog")
        if setup_cog is None:
            return
        await setup_cog._upsert_panel(channel, embed, view)

    async def _ensure_help_channels(self, guild: discord.Guild) -> None:
        category = discord.utils.get(guild.categories, name=HELP_CATEGORY)
        if category is None:
            return
        wanted = (QUICK_CHANNEL, GUIDES_CHANNEL)
        for name in wanted:
            channel = discord.utils.get(guild.text_channels, name=name)
            if channel is None:
                try:
                    channel = await guild.create_text_channel(name, category=category, reason="Aide Bot V54 — système d'aide")
                except (discord.Forbidden, discord.HTTPException):
                    continue
            elif channel.category_id != category.id:
                try:
                    await channel.edit(category=category, reason="Aide Bot V54 — catégorie d'aide canonique")
                except (discord.Forbidden, discord.HTTPException):
                    pass
            await self._configure_channel(channel)

        center = discord.utils.get(guild.text_channels, name=CENTER_CHANNEL)
        quick = discord.utils.get(guild.text_channels, name=QUICK_CHANNEL)
        guides = discord.utils.get(guild.text_channels, name=GUIDES_CHANNEL)
        if center is not None:
            await self._configure_channel(center)
            await self._upsert(center, help_home_embed(), HelpHomeView(self.bot))
        if quick is not None:
            await self._upsert(quick, quick_help_embed(), QuickHelpView(self.bot))
        if guides is not None:
            await self._upsert(guides, guides_home_embed(), GuidesView(self.bot))

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            if guild.id in self._ready_guilds:
                continue
            self._ready_guilds.add(guild.id)
            await self._ensure_help_channels(guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.TextChannel):
            return
        if channel.name in {CENTER_CHANNEL, QUICK_CHANNEL, GUIDES_CHANNEL}:
            await self._configure_channel(channel)
            if channel.name == CENTER_CHANNEL:
                await self._upsert(channel, help_home_embed(), HelpHomeView(self.bot))
            elif channel.name == QUICK_CHANNEL:
                await self._upsert(channel, quick_help_embed(), QuickHelpView(self.bot))
            elif channel.name == GUIDES_CHANNEL:
                await self._upsert(channel, guides_home_embed(), GuidesView(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpSystemV54Cog(bot))
