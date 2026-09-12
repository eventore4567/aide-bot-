from __future__ import annotations

import re
from dataclasses import dataclass

import discord
from discord.ext import commands

from aidebot.cogs.experience_v43 import member_space_embed
from aidebot.cogs.premium_v45 import (
    PREMIUM_CATEGORY,
    PREMIUM_HUB_CHANNEL,
    PREMIUM_VIDEO_CHANNEL,
    PremiumVideoLibraryView,
    premium_video_home_embed,
)
from aidebot.cogs.setup_server import SetupServerCog
from aidebot.experience_content import BANNER_URL
from aidebot.permissions import can
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed

PREMIUM_COLOR = 0xEB459E
SUCCESS = 0x57F287
WARNING = 0xF1C40F
SERVER_BUILD_KEY = "premium_server_build"

# Ces quatre ressources sont des vidéos directes et non des pages de recherche.
# La bibliothèque avancée de 25 sujets reste disponible à côté pour les thèmes
# qui évoluent rapidement.
DIRECT_PREMIUM_VIDEOS = {
    "persistent-ui": {
        "title": "discord.py — vues persistantes",
        "url": "https://www.youtube.com/watch?v=uXAmyH4UADY",
        "note": "Boutons persistants, setup_hook, custom_id et redémarrages propres.",
    },
    "oauth2": {
        "title": "Discord OAuth2 — autoriser un bot",
        "url": "https://www.youtube.com/watch?v=KxPaAGBLqWM",
        "note": "Comprendre l’autorisation d’un bot sur un serveur et les scopes OAuth2.",
    },
    "ci": {
        "title": "pytest + GitHub Actions — vraie CI Python",
        "url": "https://www.youtube.com/watch?v=DhUpxWjOhME",
        "note": "Tests, tox et GitHub Actions avant de déployer en production.",
    },
    "postgres": {
        "title": "Python + PostgreSQL — bases production",
        "url": "https://www.youtube.com/watch?v=2PDkXviEMD0",
        "note": "Connexion, requêtes, transactions et persistance côté PostgreSQL.",
    },
}

PREMIUM_SERVICE_FORMS = {
    "audit-server": {
        "label": "Audit complet serveur",
        "description": "Score, risques, priorités et plan d’amélioration personnalisé.",
        "questions": (
            ("Contexte du serveur", "Taille, public, objectif et état actuel", 300),
            ("Problèmes principaux", "Ce qui te gêne aujourd’hui", 550),
            ("Zones à auditer", "Rôles, permissions, onboarding, tickets, sécurité...", 350),
            ("Résultat attendu", "Ce que tu veux obtenir à la fin de l’audit", 500),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "improve-server": {
        "label": "Améliorer mon serveur",
        "description": "Refonte structure, rôles, onboarding, tickets et expérience membre.",
        "questions": (
            ("État actuel", "Nouveau / actif / public / en refonte", 180),
            ("Ce qui doit changer", "Structure, salons, rôles, design, parcours membre...", 600),
            ("Public visé", "Gaming, communauté, boutique, créateur, support...", 250),
            ("Priorité", "Le premier résultat que tu veux voir", 450),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "fix-bot": {
        "label": "Corriger / améliorer mon bot",
        "description": "Architecture, bugs, permissions, DB, logs, tests et déploiement.",
        "questions": (
            ("Stack actuelle", "Python/discord.py, DB, hébergement, GitHub...", 250),
            ("Problème exact", "Erreur, comportement ou dette technique", 650),
            ("Fonctions concernées", "Tickets, modération, économie, UI, DB...", 350),
            ("Résultat attendu", "Ce qui doit fonctionner à la fin", 500),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "security": {
        "label": "Sécuriser mon serveur",
        "description": "Audit permissions, bots, webhooks, anti-raid et plan d’urgence.",
        "questions": (
            ("Contexte / risque", "Taille du serveur et niveau de risque", 250),
            ("Incidents connus", "Raids, permissions, bots suspects... sans secret", 550),
            ("Zones sensibles", "Rôles, webhooks, bots, staff, permissions...", 350),
            ("Objectif sécurité", "Ce que tu veux protéger ou vérifier", 500),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "railway": {
        "label": "Optimiser Railway / production",
        "description": "Logs, variables, volume, DB, redémarrages et déploiement fiable.",
        "questions": (
            ("Service actuel", "Bot Python, API, base de données...", 250),
            ("Problème production", "Crash, données perdues, build, logs...", 650),
            ("Stockage", "SQLite, volume, PostgreSQL ou autre", 250),
            ("Résultat attendu", "Déploiement stable, persistance, monitoring...", 450),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "tickets": {
        "label": "Créer mon système de tickets",
        "description": "Formulaires, catégories, permissions, claim, suivi et logs.",
        "questions": (
            ("Type de serveur", "Communauté, shop, gaming, support...", 220),
            ("Types de tickets", "Aide, achat, recrutement, partenariat...", 500),
            ("Staff concerné", "Rôles qui doivent accéder aux tickets", 300),
            ("Workflow attendu", "Claim, paiement, fermeture, transcript...", 550),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "personal-plan": {
        "label": "Plan personnalisé",
        "description": "Objectif → diagnostic → étapes → exercices → validation finale.",
        "questions": (
            ("Ton niveau", "Débutant / intermédiaire / avancé", 150),
            ("Ton projet", "Serveur, bot, sécurité, business Discord...", 500),
            ("Objectif final", "Ce que tu veux savoir faire ou terminer", 600),
            ("Blocages actuels", "Ce qui t’empêche d’avancer", 450),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
}

SERVER_TEMPLATES = {
    "community": {
        "label": "Communauté",
        "description": "Accueil, discussions, médias, suggestions, support et staff.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ COMMUNAUTÉ ━━", (("text", "💬・général"), ("text", "📸・médias"), ("text", "💡・suggestions"), ("voice", "🔊・Général"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "⭐・avis"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"), ("voice", "🔒・Staff"))),
        ),
    },
    "gaming": {
        "label": "Gaming",
        "description": "Communauté gaming, recherche de joueurs, clips, vocal, support et staff.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ GAMING ━━", (("text", "🎮・général"), ("text", "🔎・recherche-joueurs"), ("text", "🎬・clips"), ("voice", "🔊・Gaming 1"), ("voice", "🔊・Gaming 2"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "💡・suggestions"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"))),
        ),
    },
    "shop": {
        "label": "Boutique / service",
        "description": "Catalogue, commandes, avis, support client et espace staff.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ BOUTIQUE ━━", (("text", "🛒・catalogue"), ("text", "📦・commandes"), ("text", "⭐・avis"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "❓・faq"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"))),
        ),
    },
    "creator": {
        "label": "Créateur / influenceur",
        "description": "Annonces, contenus, communauté, collaborations et support.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ CONTENU ━━", (("text", "🎬・nouveautés"), ("text", "💬・général"), ("text", "🤝・collaborations"), ("voice", "🔊・Communauté"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "💡・suggestions"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"))),
        ),
    },
    "support": {
        "label": "Support / assistance",
        "description": "FAQ, ressources, demandes privées, avis et organisation du staff.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ RESSOURCES ━━", (("text", "❓・faq"), ("text", "📚・guides"), ("text", "📌・statut-service"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "⭐・avis"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"), ("voice", "🔒・Staff"))),
        ),
    },
}


@dataclass(frozen=True)
class ServerBuildData:
    target_guild_id: int
    template_key: str
    requested_name: str
    purpose: str
    extras: str


def premium_v47_hub_embed(price: int) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Espace Premium",
        description=(
            f"**Premium — {price} Robux** n’est plus juste un rôle + quelques vidéos. C’est un **pack de service complet** : audit, configuration, "
            "support prioritaire, aide bot/production, sécurité, création de tickets et suivi personnalisé.\n\n"
            "Pour la création de serveur, Aide Bot peut même construire directement la structure sur ton serveur après paiement et autorisation Discord."
        ),
        color=PREMIUM_COLOR,
    )
    e.add_field(name="Audit personnalisé", value="Score du projet, risques, priorités, plan d’amélioration et vérification finale.", inline=True)
    e.add_field(name="Serveur construit pour toi", value="5 modèles + rôles + catégories + salons + permissions + accueil + tickets.", inline=True)
    e.add_field(name="Bot & production", value="Bugs, architecture, Railway, DB, logs, tests, GitHub et déploiement.", inline=True)
    e.add_field(name="Sécurité", value="Permissions, bots, webhooks, anti-raid et procédure d’urgence.", inline=True)
    e.add_field(name="Support prioritaire", value="Ticket dédié, responsable clair et suivi jusqu’à un résultat vérifiable.", inline=True)
    e.add_field(name="Vidéos VIP", value="Vidéos directes sélectionnées + bibliothèque avancée de 25 sujets techniques.", inline=True)
    e.add_field(
        name="Important — installation sur ton serveur",
        value="Après validation du paiement, Discord exige **une autorisation OAuth2 du propriétaire/administrateur**. Le bot ne peut pas s’ajouter tout seul sans ton clic. Une fois autorisé, la configuration peut être lancée depuis le ticket.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V47 • Premium = service concret + automatisation + suivi")
    return e


def premium_v47_video_embed() -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Vidéos Premium",
        description=(
            "Ici tu as maintenant des **vidéos directes configurées**, pas uniquement des recherches YouTube. "
            "La bibliothèque de 25 sujets avancés reste disponible en complément pour les thèmes qui changent vite."
        ),
        color=PREMIUM_COLOR,
    )
    for video in DIRECT_PREMIUM_VIDEOS.values():
        e.add_field(name=video["title"], value=video["note"], inline=True)
    e.add_field(name="Bibliothèque avancée", value="Architecture • sécurité • production • UX Discord • qualité/fiabilité — 25 sujets Premium supplémentaires.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V47 • Vidéos directes + bibliothèque avancée")
    return e


def server_template_embed() -> discord.Embed:
    e = discord.Embed(
        title="Premium — création automatique de serveur",
        description=(
            "Choisis le modèle qui ressemble le plus à ton projet. Ensuite un formulaire demande l’ID du serveur, le nom souhaité, ton objectif et les options à ajouter.\n\n"
            "**Si tu n’es pas encore VIP :** la demande ouvre un ticket de paiement. Après validation, tu autorises Aide Bot sur ton serveur puis tu cliques sur **Construire mon serveur**."
        ),
        color=PREMIUM_COLOR,
    )
    for data in SERVER_TEMPLATES.values():
        e.add_field(name=data["label"], value=data["description"], inline=True)
    e.set_image(url=BANNER_URL)
    return e


def _parse_build_data(objective: str) -> ServerBuildData | None:
    guild_match = re.search(r"Serveur cible ID\s*:\s*(\d{15,22})", objective)
    template_match = re.search(r"Modèle\s*:\s*([a-z-]+)", objective)
    if not guild_match or not template_match or template_match.group(1) not in SERVER_TEMPLATES:
        return None

    def value(label: str) -> str:
        match = re.search(rf"{re.escape(label)}\s*:\s*(.+)", objective)
        return match.group(1).strip() if match else ""

    return ServerBuildData(
        target_guild_id=int(guild_match.group(1)),
        template_key=template_match.group(1),
        requested_name=value("Nom souhaité"),
        purpose=value("Objectif"),
        extras=value("Options"),
    )


def _server_bot_permissions() -> discord.Permissions:
    perms = discord.Permissions.none()
    perms.update(
        view_channel=True,
        manage_channels=True,
        manage_roles=True,
        manage_guild=True,
        send_messages=True,
        manage_messages=True,
        embed_links=True,
        read_message_history=True,
    )
    return perms


def _oauth_url(bot: commands.Bot, target_guild_id: int) -> str | None:
    if bot.user is None:
        return None
    return discord.utils.oauth_url(
        bot.user.id,
        permissions=_server_bot_permissions(),
        guild=discord.Object(id=target_guild_id),
        scopes=("bot", "applications.commands"),
        disable_guild_select=True,
    )


async def _require_vip(interaction: discord.Interaction) -> bool:
    if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
        return True
    shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
    await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
    return False


class PremiumServiceModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, service_key: str) -> None:
        data = PREMIUM_SERVICE_FORMS[service_key]
        super().__init__(title=data["label"][:45])
        self.bot = bot
        self.service_key = service_key
        self.inputs: list[discord.ui.TextInput] = []
        for index, (label, placeholder, max_length) in enumerate(data["questions"]):
            item = discord.ui.TextInput(
                label=label[:45],
                placeholder=placeholder[:100],
                style=discord.TextStyle.paragraph if index in {1, 2, 3} else discord.TextStyle.short,
                max_length=max_length,
            )
            self.inputs.append(item)
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop")
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de tickets indisponible.", ephemeral=True)
        data = PREMIUM_SERVICE_FORMS[self.service_key]
        objective = "\n\n".join(
            f"{question[0]} : {str(item).strip()}" for question, item in zip(data["questions"], self.inputs)
        )[:3000]
        await training.create_request_channel(
            interaction,
            f"premium_service_{self.service_key.replace('-', '_')}",
            level="Service Premium personnalisé",
            objective=objective,
            availability=str(self.inputs[-1]).strip(),
            budget="Inclus dans l’abonnement Premium",
            status="open",
            payment_status="not_required",
            requires_invite=False,
        )


class ServerBuildRequestModal(discord.ui.Modal):
    target_server = discord.ui.TextInput(
        label="ID du serveur à configurer",
        placeholder="Active le mode développeur Discord puis Copier l’identifiant du serveur",
        max_length=22,
    )
    requested_name = discord.ui.TextInput(
        label="Nom souhaité du serveur",
        placeholder="Laisse le nom actuel ou indique le nouveau nom",
        required=False,
        max_length=100,
    )
    purpose = discord.ui.TextInput(
        label="Objectif du serveur",
        placeholder="Communauté, gaming, boutique, créateur, support...",
        style=discord.TextStyle.paragraph,
        max_length=500,
    )
    extras = discord.ui.TextInput(
        label="Options / demandes spéciales",
        placeholder="Rôles, salons, couleurs, tickets, vocaux, règles...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=600,
    )
    availability = discord.ui.TextInput(
        label="Tes disponibilités",
        placeholder="Ex: samedi 14h-20h",
        max_length=150,
    )

    def __init__(self, bot: commands.Bot, template_key: str) -> None:
        super().__init__(title=f"Serveur — {SERVER_TEMPLATES[template_key]['label']}"[:45])
        self.bot = bot
        self.template_key = template_key

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        raw = str(self.target_server).strip()
        if not raw.isdigit() or not 15 <= len(raw) <= 22:
            return await interaction.response.send_message(
                "L’ID du serveur n’est pas valide. Active le **mode développeur** Discord puis utilise **Copier l’identifiant du serveur**.",
                ephemeral=True,
            )
        target_guild_id = int(raw)
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de tickets indisponible.", ephemeral=True)
        existing = await self.bot.db.active_request_for_training(interaction.guild.id, interaction.user.id, SERVER_BUILD_KEY)
        if existing:
            channel = interaction.guild.get_channel(existing["channel_id"]) if existing["channel_id"] else None
            destination = channel.mention if isinstance(channel, discord.TextChannel) else f"demande #{existing['id']}"
            return await interaction.response.send_message(
                f"Tu as déjà une création de serveur active : {destination}.", ephemeral=True
            )

        vip = has_premium(interaction.user)
        objective = (
            f"Serveur cible ID : {target_guild_id}\n"
            f"Modèle : {self.template_key}\n"
            f"Nom souhaité : {str(self.requested_name).strip() or 'Conserver le nom actuel'}\n"
            f"Objectif : {str(self.purpose).strip()}\n"
            f"Options : {str(self.extras).strip() or 'Aucune option spéciale'}"
        )
        await training.create_request_channel(
            interaction,
            SERVER_BUILD_KEY,
            level=f"Modèle {SERVER_TEMPLATES[self.template_key]['label']}",
            objective=objective,
            availability=str(self.availability).strip(),
            budget=(
                "Service inclus — abonnement Premium actif"
                if vip
                else f"Pack Premium — {self.bot.settings.vip_price_robux} Robux"
            ),
            status="open" if vip else "payment_pending",
            payment_status="not_required" if vip else "pending",
            requires_invite=False,
        )


class ServerTemplateSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__(
            placeholder="Choisis le modèle du serveur",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=data["label"], value=key, description=data["description"][:100])
                for key, data in SERVER_TEMPLATES.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ServerBuildRequestModal(self.bot, self.values[0]))


class ServerTemplateChoiceView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=900)
        self.add_item(ServerTemplateSelect(bot))


class PremiumServiceSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(label="Créer mon serveur automatiquement", value="build-server", description="5 modèles + configuration directe par Aide Bot"),
            *[
                discord.SelectOption(label=data["label"], value=key, description=data["description"][:100])
                for key, data in PREMIUM_SERVICE_FORMS.items()
            ],
        ]
        super().__init__(
            placeholder="Choisis le service Premium dont tu as besoin",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:v47:premium:service",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await _require_vip(interaction):
            return
        key = self.values[0]
        if key == "build-server":
            return await interaction.response.send_message(
                embed=server_template_embed(), view=ServerTemplateChoiceView(self.bot), ephemeral=True
            )
        await interaction.response.send_modal(PremiumServiceModal(self.bot, key))


class DirectPremiumVideoView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        for video in DIRECT_PREMIUM_VIDEOS.values():
            self.add_item(discord.ui.Button(label=video["title"][:80], url=video["url"], style=discord.ButtonStyle.link))

    @discord.ui.button(
        label="Bibliothèque avancée — 25 sujets",
        style=discord.ButtonStyle.primary,
        custom_id="aidebot:v47:premium:video-library",
        row=1,
    )
    async def library(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_message(
            embed=premium_video_home_embed(), view=PremiumVideoLibraryView(), ephemeral=True
        )


class PremiumServiceHubView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(PremiumServiceSelect(bot))

    @discord.ui.button(label="Créer mon serveur", style=discord.ButtonStyle.success, custom_id="aidebot:v47:premium:server", row=1)
    async def build_server(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_message(embed=server_template_embed(), view=ServerTemplateChoiceView(self.bot), ephemeral=True)

    @discord.ui.button(label="Vidéos VIP directes", style=discord.ButtonStyle.primary, custom_id="aidebot:v47:premium:direct-videos", row=1)
    async def videos(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_message(embed=premium_v47_video_embed(), view=DirectPremiumVideoView(), ephemeral=True)

    @discord.ui.button(label="Mon espace", style=discord.ButtonStyle.secondary, custom_id="aidebot:v47:premium:space", row=1)
    async def space(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction) or not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=await member_space_embed(self.bot, interaction.user), ephemeral=True)

    @discord.ui.button(label="Statut VIP", style=discord.ButtonStyle.secondary, custom_id="aidebot:v47:premium:status", row=2)
    async def status(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction) or not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=premium_member_embed(interaction.user), ephemeral=True)


class OAuthInviteView(discord.ui.View):
    def __init__(self, url: str) -> None:
        super().__init__(timeout=900)
        self.add_item(discord.ui.Button(label="Autoriser Aide Bot sur mon serveur", url=url, style=discord.ButtonStyle.link))


def server_build_control_embed(req, ready: bool) -> discord.Embed:
    data = _parse_build_data(str(req["objective"]))
    template = SERVER_TEMPLATES[data.template_key]["label"] if data else "Inconnu"
    e = discord.Embed(
        title="Premium — création de serveur",
        description=(
            "Le paiement est validé et le service est **débloqué**. Autorise Aide Bot sur le serveur cible, puis lance la construction."
            if ready
            else "La demande est enregistrée mais la construction reste **verrouillée tant que le paiement Premium n’est pas validé**."
        ),
        color=SUCCESS if ready else WARNING,
    )
    if data:
        e.add_field(name="Serveur cible", value=f"`{data.target_guild_id}`", inline=True)
        e.add_field(name="Modèle", value=template, inline=True)
        e.add_field(name="Nom", value=data.requested_name[:200] or "Conserver le nom actuel", inline=True)
    e.add_field(
        name="Sécurité",
        value="Aide Bot ne supprime pas tes salons ou rôles existants. Il crée/réutilise uniquement les éléments du modèle et ne demande jamais ton token, mot de passe ou code 2FA.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V47 • paiement → OAuth2 → configuration automatique")
    return e


async def _request_for_ticket(bot: commands.Bot, interaction: discord.Interaction):
    if interaction.channel is None:
        return None
    return await bot.db.request_by_channel(interaction.channel.id)


async def _client_target_member(guild: discord.Guild, user_id: int) -> discord.Member | None:
    member = guild.get_member(user_id)
    if member is not None:
        return member
    try:
        return await guild.fetch_member(user_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


def _request_unlocked(req, service_member: discord.Member | None) -> bool:
    if str(req["payment_status"]) == "paid":
        return True
    return bool(str(req["payment_status"]) == "not_required" and service_member and has_premium(service_member))


class ServerBuildTicketView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Autoriser Aide Bot", style=discord.ButtonStyle.primary, custom_id="aidebot:v47:server:authorize")
    async def authorize(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        req = await _request_for_ticket(self.bot, interaction)
        if not req or str(req["training_key"]) != SERVER_BUILD_KEY:
            return await interaction.response.send_message("Ce bouton n’est pas lié à une création de serveur valide.", ephemeral=True)
        if interaction.user.id != int(req["user_id"]) and not can(interaction.user, "training.manage"):
            return await interaction.response.send_message("Seul le client ou un responsable peut utiliser ce bouton.", ephemeral=True)
        client = interaction.guild.get_member(int(req["user_id"]))
        if not _request_unlocked(req, client):
            return await interaction.response.send_message("Le paiement doit d’abord être validé par la Direction.", ephemeral=True)
        data = _parse_build_data(str(req["objective"]))
        if data is None:
            return await interaction.response.send_message("Les informations du serveur cible sont invalides.", ephemeral=True)
        url = _oauth_url(self.bot, data.target_guild_id)
        if url is None:
            return await interaction.response.send_message("Le lien OAuth2 n’est pas encore disponible. Réessaie dans quelques secondes.", ephemeral=True)
        e = discord.Embed(
            title="Autoriser Aide Bot",
            description=(
                "Discord exige ton autorisation avant qu’un bot rejoigne un serveur. Clique sur le bouton ci-dessous avec un compte propriétaire/administrateur du serveur cible.\n\n"
                "Après l’autorisation, reviens dans ce ticket et clique sur **Construire mon serveur**."
            ),
            color=PREMIUM_COLOR,
        )
        await interaction.response.send_message(embed=e, view=OAuthInviteView(url), ephemeral=True)

    @discord.ui.button(label="Construire mon serveur", style=discord.ButtonStyle.success, custom_id="aidebot:v47:server:build")
    async def build(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        req = await _request_for_ticket(self.bot, interaction)
        if not req or str(req["training_key"]) != SERVER_BUILD_KEY:
            return await interaction.response.send_message("Demande de serveur introuvable.", ephemeral=True)
        if interaction.user.id != int(req["user_id"]) and not can(interaction.user, "training.manage"):
            return await interaction.response.send_message("Seul le client ou un responsable peut lancer la configuration.", ephemeral=True)
        client = interaction.guild.get_member(int(req["user_id"]))
        if not _request_unlocked(req, client):
            return await interaction.response.send_message("La configuration est verrouillée jusqu’à la validation du paiement.", ephemeral=True)
        data = _parse_build_data(str(req["objective"]))
        if data is None:
            return await interaction.response.send_message("Les informations du serveur cible sont invalides.", ephemeral=True)
        target = self.bot.get_guild(data.target_guild_id)
        if target is None:
            return await interaction.response.send_message(
                "Aide Bot n’est pas encore présent sur le serveur cible. Clique d’abord sur **Autoriser Aide Bot**.", ephemeral=True
            )
        target_member = await _client_target_member(target, int(req["user_id"]))
        if target_member is None or not (
            target.owner_id == target_member.id
            or target_member.guild_permissions.administrator
            or target_member.guild_permissions.manage_guild
        ):
            return await interaction.response.send_message(
                "Pour lancer la construction, le client doit être propriétaire ou administrateur/Gérer le serveur sur le serveur cible.", ephemeral=True
            )
        me = target.me
        if me is None or not me.guild_permissions.manage_channels or not me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "Aide Bot est présent mais il lui manque **Gérer les salons** ou **Gérer les rôles**. Réautorise-le avec le bouton OAuth2.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            report = await build_client_server(self.bot, target, data)
        except (discord.Forbidden, discord.HTTPException) as exc:
            return await interaction.followup.send(
                f"Discord a bloqué une étape de configuration : `{type(exc).__name__}`. Vérifie la hiérarchie du rôle Aide Bot.", ephemeral=True
            )

        await interaction.followup.send(
            "Configuration terminée ✅\n"
            f"**Rôles créés :** {report['roles_created']} • **Catégories créées :** {report['categories_created']} • "
            f"**Salons créés :** {report['channels_created']} • **Panneaux installés :** {report['panels']}\n\n"
            "Aucun salon ou rôle utilisateur existant n’a été supprimé.",
            ephemeral=True,
        )
        training = self.bot.get_cog("TrainingCog")
        if training is not None:
            await training.log_action(
                interaction.guild,
                "Serveur Premium configuré",
                f"Ticket #{req['id']} • serveur cible `{target.id}` • modèle **{SERVER_TEMPLATES[data.template_key]['label']}**",
            )

    @discord.ui.button(label="Voir le plan", style=discord.ButtonStyle.secondary, custom_id="aidebot:v47:server:plan")
    async def plan(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await _request_for_ticket(self.bot, interaction)
        if not req or str(req["training_key"]) != SERVER_BUILD_KEY:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        data = _parse_build_data(str(req["objective"]))
        if data is None:
            return await interaction.response.send_message("Plan introuvable.", ephemeral=True)
        template = SERVER_TEMPLATES[data.template_key]
        lines = []
        for category, channels in template["categories"]:
            names = ", ".join(name for _kind, name in channels)
            lines.append(f"**{category}**\n{names}")
        e = discord.Embed(title=f"Plan — {template['label']}", description="\n\n".join(lines), color=PREMIUM_COLOR)
        e.add_field(name="Options demandées", value=data.extras[:1024], inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)


async def _ensure_role(guild: discord.Guild, name: str, permissions: discord.Permissions) -> tuple[discord.Role, bool]:
    role = discord.utils.get(guild.roles, name=name)
    if role is not None:
        return role, False
    role = await guild.create_role(name=name, permissions=permissions, reason="Aide Bot V47 — pack Premium serveur")
    return role, True


async def _ensure_category(guild: discord.Guild, name: str, overwrites: dict) -> tuple[discord.CategoryChannel, bool]:
    category = discord.utils.get(guild.categories, name=name)
    if category is not None:
        return category, False
    category = await guild.create_category(name, overwrites=overwrites, reason="Aide Bot V47 — pack Premium serveur")
    return category, True


async def _ensure_channel(category: discord.CategoryChannel, kind: str, name: str, overwrites: dict | None = None):
    if kind == "voice":
        existing = discord.utils.get(category.voice_channels, name=name)
        if existing is not None:
            return existing, False
        return await category.create_voice_channel(name, overwrites=overwrites, reason="Aide Bot V47 — pack Premium serveur"), True
    existing = discord.utils.get(category.text_channels, name=name)
    if existing is not None:
        return existing, False
    return await category.create_text_channel(name, overwrites=overwrites, reason="Aide Bot V47 — pack Premium serveur"), True


async def _has_bot_panel(channel: discord.TextChannel, bot_user_id: int, title: str) -> discord.Message | None:
    try:
        async for message in channel.history(limit=30):
            if message.author.id == bot_user_id and any(embed.title == title for embed in message.embeds):
                return message
    except (discord.Forbidden, discord.HTTPException):
        return None
    return None


class ClientSupportTicketCloseView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="aidebot:v47:client-ticket:close")
    async def close(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member) or not isinstance(interaction.channel, discord.TextChannel):
            return
        topic = interaction.channel.topic or ""
        match = re.search(r"aidebot-client-ticket:(\d+)", topic)
        owner_id = int(match.group(1)) if match else 0
        staff = any(role.name in {"🛡️・Modérateur", "🎫・Support"} for role in interaction.user.roles)
        if interaction.user.id != owner_id and not staff and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Tu ne peux pas fermer ce ticket.", ephemeral=True)
        owner = interaction.guild.get_member(owner_id)
        if owner:
            try:
                await interaction.channel.set_permissions(owner, view_channel=True, send_messages=False, read_message_history=True)
            except discord.HTTPException:
                pass
        try:
            await interaction.channel.edit(name=f"fermé-{interaction.channel.name}"[:95])
        except discord.HTTPException:
            pass
        await interaction.response.send_message("Ticket fermé en lecture seule.")


class ClientSupportView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Ouvrir un ticket", style=discord.ButtonStyle.primary, custom_id="aidebot:v47:client-ticket:open")
    async def open_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        for channel in interaction.guild.text_channels:
            if channel.topic == f"aidebot-client-ticket:{interaction.user.id}" and not channel.name.startswith("fermé-"):
                return await interaction.response.send_message(f"Tu as déjà un ticket actif : {channel.mention}", ephemeral=True)
        category = discord.utils.get(interaction.guild.categories, name="━━ SUPPORT ━━")
        if category is None:
            return await interaction.response.send_message("La catégorie Support est introuvable.", ephemeral=True)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if interaction.guild.me:
            overwrites[interaction.guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        for role_name in ("🛡️・Modérateur", "🎫・Support"):
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        try:
            channel = await interaction.guild.create_text_channel(
                f"ticket-{interaction.user.name}"[:90],
                category=category,
                topic=f"aidebot-client-ticket:{interaction.user.id}",
                overwrites=overwrites,
                reason="Aide Bot V47 — ticket client",
            )
        except (discord.Forbidden, discord.HTTPException):
            return await interaction.response.send_message("Impossible de créer le ticket. Vérifie les permissions d’Aide Bot.", ephemeral=True)
        e = discord.Embed(
            title="Support — ticket privé",
            description=f"{interaction.user.mention}, explique ton problème avec le résultat attendu et ce que tu as déjà essayé. Ne partage jamais de secret.",
            color=0x5865F2,
        )
        await channel.send(embed=e, view=ClientSupportTicketCloseView(), allowed_mentions=discord.AllowedMentions.none())
        await interaction.response.send_message(f"Ticket créé : {channel.mention}", ephemeral=True)


async def build_client_server(bot: commands.Bot, guild: discord.Guild, data: ServerBuildData) -> dict[str, int]:
    report = {"roles_created": 0, "categories_created": 0, "channels_created": 0, "panels": 0}

    member_perms = discord.Permissions.none()
    mod_perms = discord.Permissions.none()
    mod_perms.update(manage_messages=True, moderate_members=True, kick_members=True, view_audit_log=True)
    support_perms = discord.Permissions.none()
    support_perms.update(manage_messages=True, read_message_history=True)

    member_role, created = await _ensure_role(guild, "✅・Membre", member_perms)
    report["roles_created"] += int(created)
    mod_role, created = await _ensure_role(guild, "🛡️・Modérateur", mod_perms)
    report["roles_created"] += int(created)
    support_role, created = await _ensure_role(guild, "🎫・Support", support_perms)
    report["roles_created"] += int(created)
    notif_role, created = await _ensure_role(guild, "📢・Notifications", member_perms)
    report["roles_created"] += int(created)

    if data.requested_name and data.requested_name.casefold() != "conserver le nom actuel" and guild.me and guild.me.guild_permissions.manage_guild:
        try:
            await guild.edit(name=data.requested_name[:100], reason="Aide Bot V47 — nom demandé dans le pack Premium")
        except discord.HTTPException:
            pass

    template = SERVER_TEMPLATES[data.template_key]
    created_text: dict[str, discord.TextChannel] = {}
    for category_name, channels in template["categories"]:
        if category_name == "━━ STAFF ━━":
            category_overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                mod_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
        else:
            category_overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=True, read_message_history=True)}
        category, created = await _ensure_category(guild, category_name, category_overwrites)
        report["categories_created"] += int(created)

        for kind, channel_name in channels:
            overwrites = None
            if kind == "text" and channel_name in {"👋・bienvenue", "📜・règlement", "📢・annonces", "🎫・support", "⭐・avis", "❓・faq", "📚・guides", "📌・statut-service", "🛒・catalogue"}:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True),
                    mod_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                }
            channel, channel_created = await _ensure_channel(category, kind, channel_name, overwrites)
            report["channels_created"] += int(channel_created)
            if isinstance(channel, discord.TextChannel):
                created_text[channel_name] = channel

    if bot.user:
        welcome = created_text.get("👋・bienvenue")
        if welcome:
            title = "Bienvenue sur le serveur"
            existing = await _has_bot_panel(welcome, bot.user.id, title)
            e = discord.Embed(
                title=title,
                description="Bienvenue ! Commence par lire le règlement, regarde les annonces puis rejoins les espaces qui t’intéressent.",
                color=0x5865F2,
            )
            e.add_field(name="Serveur configuré", value=f"Modèle **{template['label']}** • structure créée avec Aide Bot Premium.", inline=False)
            if existing:
                await existing.edit(embed=e)
            else:
                await welcome.send(embed=e)
            report["panels"] += 1

        rules = created_text.get("📜・règlement")
        if rules:
            title = "Règlement"
            existing = await _has_bot_panel(rules, bot.user.id, title)
            e = discord.Embed(
                title=title,
                description="1. Respecte les membres.\n2. Pas de spam ni arnaque.\n3. Respecte les salons et le staff.\n4. Ne partage jamais de mot de passe, token, cookie ou code 2FA.\n5. Utilise le support pour les demandes privées.",
                color=0x2B2D31,
            )
            if existing:
                await existing.edit(embed=e)
            else:
                await rules.send(embed=e)
            report["panels"] += 1

        support = created_text.get("🎫・support")
        if support:
            title = "Support — ouvre un ticket"
            existing = await _has_bot_panel(support, bot.user.id, title)
            e = discord.Embed(
                title=title,
                description="Besoin d’aide ? Clique sur **Ouvrir un ticket**. Un salon privé sera créé avec toi et les rôles Support/Modérateur.",
                color=0x57F287,
            )
            if existing:
                await existing.edit(embed=e, view=ClientSupportView())
            else:
                await support.send(embed=e, view=ClientSupportView())
            report["panels"] += 1

    return report


def _install_setup_patch() -> None:
    if getattr(SetupServerCog, "_aidebot_v47_patched", False):
        return
    original_channel_permissions = SetupServerCog._reconcile_channel_permissions

    async def channel_permissions(self: SetupServerCog, guild: discord.Guild, channel: discord.TextChannel, roles: dict[str, discord.Role]) -> None:
        await original_channel_permissions(self, guild, channel, roles)
        if not channel.category or channel.category.name != PREMIUM_CATEGORY:
            return
        if channel.name == PREMIUM_HUB_CHANNEL:
            await self._upsert_panel(channel, premium_v47_hub_embed(self.bot.settings.vip_price_robux), PremiumServiceHubView(self.bot))
        elif channel.name == PREMIUM_VIDEO_CHANNEL:
            await self._upsert_panel(channel, premium_v47_video_embed(), DirectPremiumVideoView())

    SetupServerCog._reconcile_channel_permissions = channel_permissions
    SetupServerCog._aidebot_v47_patched = True


class PremiumServiceV47Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        _install_setup_patch()
        self.bot.add_view(PremiumServiceHubView(self.bot))
        self.bot.add_view(DirectPremiumVideoView())
        self.bot.add_view(ServerBuildTicketView(self.bot))
        self.bot.add_view(ClientSupportView())
        self.bot.add_view(ClientSupportTicketCloseView())

    async def unlock_server_build_ticket(self, channel: discord.TextChannel, req) -> None:
        try:
            await channel.send(
                embed=server_build_control_embed(req, True),
                view=ServerBuildTicketView(self.bot),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("ticket-"):
            return
        req = None
        for _ in range(10):
            req = await self.bot.db.request_by_channel(channel.id)
            if req is not None:
                break
            await discord.utils.sleep_until(discord.utils.utcnow()) if False else __import__("asyncio").sleep(0.35)
        if req is None or str(req["training_key"]) != SERVER_BUILD_KEY:
            return
        client = channel.guild.get_member(int(req["user_id"]))
        ready = _request_unlocked(req, client)
        try:
            await channel.send(
                embed=server_build_control_embed(req, ready),
                view=ServerBuildTicketView(self.bot),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PremiumServiceV47Cog(bot))
