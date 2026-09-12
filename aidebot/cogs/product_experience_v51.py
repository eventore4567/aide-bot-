from __future__ import annotations

import discord
from discord.ext import commands

import aidebot.public_panels as public_panels
import aidebot.cogs.center as center
import aidebot.cogs.center_autopost as center_autopost
import aidebot.cogs.storefront as storefront
import aidebot.cogs.premium_service_v48 as v48
import aidebot.cogs.premium_service_v49 as v49
import aidebot.cogs.premium_service_v50 as v50
from aidebot.cogs.experience_v43 import SupportRequestModal, member_space_embed
from aidebot.cogs.experience_v44 import SmartSupportView
from aidebot.cogs.help_center_v46 import HELP_TOPICS
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed
from aidebot.video_catalog import VIDEO_LIBRARY

COLOR = 0x5865F2
SUCCESS = 0x57F287
PREMIUM = 0xEB459E
WARNING = 0xF1C40F

WELCOME_TITLE = "Bienvenue — Aide Bot"
CENTER_TITLE = "Aide Bot — Centre d’aide"
SHOP_TITLE = "Aide Bot — Boutique Premium"
SHOP_CHANNEL = "🛒・shop"

PUBLIC_HELP_TOPIC_KEYS = (
    "discord",
    "server",
    "permissions",
    "security",
    "moderation",
    "tickets",
    "bot",
    "webhooks",
    "hosting",
    "database",
    "github",
    "other",
)

LEGACY_PANEL_TITLES = {
    "👋・bienvenue": {
        "Bienvenue sur Aide Bot",
        "Bienvenue — Aide Bot",
        "Aide Bot — Centre d’aide & formations",
    },
    "🎓・centre-aide": {
        "Aide Bot — Centre d’aide & formations",
        "Aide Bot — Centre d’aide • Tableau de bord",
        "Aide Bot — Centre d’aide",
    },
    "🛒・shop": {
        "Aide Bot — Boutique Premium",
        "Aide Bot — Premium Elite 10K",
        "Aide Bot — Boutique Premium Elite",
    },
}


def _format_robux(value: int) -> str:
    return f"{max(0, int(value)):,}".replace(",", " ")


def welcome_embed_v51() -> discord.Embed:
    e = discord.Embed(
        title=WELCOME_TITLE,
        description=(
            "Bienvenue sur **Aide Bot**. Choisis simplement ce que tu veux faire : "
            "trouver une réponse, apprendre avec un parcours guidé ou demander de l’aide."
        ),
        color=COLOR,
    )
    e.add_field(
        name="Besoin d’une réponse ?",
        value="Ouvre le **Centre d’aide** et choisis ton sujet. Tu verras les vérifications utiles avant d’ouvrir un ticket.",
        inline=False,
    )
    e.add_field(
        name="Tu veux apprendre ?",
        value="Les **Formations** proposent des parcours adaptés à ton niveau et à ton objectif.",
        inline=True,
    )
    e.add_field(
        name="Tu es bloqué ?",
        value="Le **Support** collecte le bon contexte avant de créer une demande.",
        inline=True,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Une action claire pour chaque besoin")
    return e


def help_center_embed_v51(_vip_price: int | None = None) -> discord.Embed:
    e = discord.Embed(
        title=CENTER_TITLE,
        description=(
            "Choisis ton sujet dans le menu. Aide Bot te donne une réponse courte, les vérifications à faire "
            "et les erreurs fréquentes. Si le problème continue, tu peux ouvrir un ticket avec le bon formulaire."
        ),
        color=COLOR,
    )
    e.add_field(
        name="Ce que tu peux résoudre ici",
        value=(
            "Discord • serveur • rôles et permissions • sécurité • modération • tickets • bots • "
            "webhooks • hébergement • base de données • GitHub et tests"
        ),
        inline=False,
    )
    e.add_field(
        name="Le principe",
        value="**Choisir → vérifier → appliquer → demander de l’aide seulement si nécessaire.**",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Centre d’aide")
    return e


def help_topic_embed_v51(topic: str) -> discord.Embed:
    data = HELP_TOPICS[topic]
    e = discord.Embed(title=data["label"], description=data["covers"], color=COLOR)
    e.add_field(
        name="À vérifier",
        value="\n".join(f"**{index}.** {step}" for index, step in enumerate(data["steps"], start=1)),
        inline=False,
    )
    e.add_field(name="À éviter", value=data["mistakes"], inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Si ça bloque encore, ouvre un ticket depuis le bouton ci-dessous.")
    return e


class HelpTopicDetailViewV51(discord.ui.View):
    def __init__(self, bot: commands.Bot, topic: str) -> None:
        super().__init__(timeout=900)
        self.bot = bot
        self.topic = topic
        data = HELP_TOPICS[topic]
        video_key = data.get("video_key")
        if video_key and video_key in VIDEO_LIBRARY:
            video = VIDEO_LIBRARY[video_key]
            self.add_item(discord.ui.Button(label="Voir le tutoriel", url=video["url"], style=discord.ButtonStyle.link, row=1))

    @discord.ui.button(label="Ouvrir un ticket", style=discord.ButtonStyle.primary, row=0)
    async def ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(SupportRequestModal(self.bot, HELP_TOPICS[self.topic]["support_type"]))

    @discord.ui.button(label="Retour", style=discord.ButtonStyle.secondary, row=0)
    async def back(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=help_center_embed_v51(), view=HelpCenterViewV51(self.bot))


class HelpTopicSelectV51(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__(
            placeholder="De quoi as-tu besoin ?",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=HELP_TOPICS[key]["label"][:100],
                    value=key,
                    description=HELP_TOPICS[key]["description"][:100],
                )
                for key in PUBLIC_HELP_TOPIC_KEYS
            ],
            custom_id="aidebot:v51:help:topic",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        topic = self.values[0]
        await interaction.response.send_message(
            embed=help_topic_embed_v51(topic),
            view=HelpTopicDetailViewV51(self.bot, topic),
            ephemeral=True,
        )


class HelpCenterViewV51(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(HelpTopicSelectV51(bot))

    @discord.ui.button(label="Guides", style=discord.ButtonStyle.secondary, custom_id="aidebot:v51:center:guides", row=1)
    async def guides(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=center.guide_index_embed(), view=center.GuideIndexView(), ephemeral=True)

    @discord.ui.button(label="Support", style=discord.ButtonStyle.primary, custom_id="aidebot:v51:center:support", row=1)
    async def support(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        e = discord.Embed(
            title="Support Aide Bot",
            description="Choisis la catégorie qui correspond à ton problème. Le formulaire demandera uniquement les informations utiles.",
            color=SUCCESS,
        )
        await interaction.response.send_message(embed=e, view=SmartSupportView(self.bot), ephemeral=True)


class WelcomeViewV51(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Centre d’aide", style=discord.ButtonStyle.primary, custom_id="aidebot:v51:welcome:center")
    async def help_center(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=help_center_embed_v51(), view=HelpCenterViewV51(self.bot), ephemeral=True)

    @discord.ui.button(label="Formations", style=discord.ButtonStyle.secondary, custom_id="aidebot:v51:welcome:training")
    async def training(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.training_experience_v42 import V42TrainingPanel, training_catalog_embed

        cog = interaction.client.get_cog("TrainingCog")
        if cog is None:
            return await interaction.response.send_message("Les formations sont temporairement indisponibles.", ephemeral=True)
        await interaction.response.send_message(embed=training_catalog_embed(), view=V42TrainingPanel(cog), ephemeral=True)

    @discord.ui.button(label="Support", style=discord.ButtonStyle.success, custom_id="aidebot:v51:welcome:support")
    async def support(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        e = discord.Embed(
            title="Besoin d’aide ?",
            description="Choisis ton type de problème. Aide Bot te pose ensuite les bonnes questions avant de créer le ticket.",
            color=SUCCESS,
        )
        await interaction.response.send_message(embed=e, view=SmartSupportView(self.bot), ephemeral=True)


def premium_details_embed_v51(price: int) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Premium",
        description=(
            f"**{_format_robux(price)} Robux**\n"
            "Premium est fait pour les membres qui veulent aller plus loin qu’un simple guide : "
            "un accompagnement suivi, des ressources avancées et des services adaptés à leur projet."
        ),
        color=PREMIUM,
    )
    e.add_field(name="Accompagnement", value="Serveur Discord, bot, permissions, sécurité, organisation, hébergement et fiabilité.", inline=True)
    e.add_field(name="Serveur sur mesure", value="Choix d’un modèle, vérifications avant modification, construction guidée et contrôle final.", inline=True)
    e.add_field(name="Ressources Premium", value="Tutoriels avancés et ressources techniques regroupés par objectif.", inline=True)
    e.add_field(name="Suivi", value="Chaque demande garde un objectif clair, une progression et un résultat vérifiable.", inline=True)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Premium")
    return e


def shop_embed_v51(price: int) -> discord.Embed:
    e = premium_details_embed_v51(price)
    e.title = SHOP_TITLE
    e.description = (
        f"**Premium — {_format_robux(price)} Robux**\n\n"
        "Débloque l’accompagnement Premium, les ressources avancées et les services personnalisés. "
        "Tu peux consulter les avantages avant de faire ta demande."
    )
    return e


class PremiumPurchaseModalV51(discord.ui.Modal, title="Premium — demande d’accompagnement"):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.project_type = discord.ui.TextInput(label="Ton projet", placeholder="Serveur, bot, sécurité, automatisation...", max_length=120)
        self.current_state = discord.ui.TextInput(
            label="Situation actuelle", placeholder="Ce qui existe déjà et ce qui te bloque", style=discord.TextStyle.paragraph, max_length=650
        )
        self.goal = discord.ui.TextInput(
            label="Résultat attendu", placeholder="Ce que tu veux obtenir à la fin", style=discord.TextStyle.paragraph, max_length=650
        )
        self.acceptance = discord.ui.TextInput(
            label="Comment valider le résultat ?",
            placeholder="Ex: serveur prêt, permissions testées, bot stable...",
            style=discord.TextStyle.paragraph,
            max_length=500,
        )
        self.availability = discord.ui.TextInput(label="Disponibilités", placeholder="Ex: samedi 14h-20h", max_length=150)
        for item in (self.project_type, self.current_state, self.goal, self.acceptance, self.availability):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if has_premium(interaction.user):
            return await interaction.response.send_message(embed=premium_member_embed(interaction.user), ephemeral=True)
        existing = await self.bot.db.active_request_for_training(interaction.guild.id, interaction.user.id, "vip")
        if existing:
            channel = interaction.guild.get_channel(existing["channel_id"]) if existing["channel_id"] else None
            destination = channel.mention if isinstance(channel, discord.TextChannel) else f"demande #{existing['id']}"
            return await interaction.response.send_message(f"Ta demande Premium est déjà en cours : {destination}.", ephemeral=True)
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Le module de tickets est temporairement indisponible.", ephemeral=True)
        objective = (
            f"Projet : {str(self.project_type).strip()}\n\n"
            f"Situation actuelle : {str(self.current_state).strip()}\n\n"
            f"Résultat attendu : {str(self.goal).strip()}\n\n"
            f"Validation attendue : {str(self.acceptance).strip()}"
        )
        await training.create_request_channel(
            interaction,
            "vip",
            level="Demande Premium",
            objective=objective,
            availability=str(self.availability).strip(),
            budget=f"Premium — {_format_robux(self.bot.settings.vip_price_robux)} Robux",
            status="payment_pending",
            payment_status="pending",
            requires_invite=False,
        )


def active_project_embed_v51(guild: discord.Guild, req) -> discord.Embed:
    if req is None:
        e = discord.Embed(title="Mon projet Premium", description="Tu n’as aucune réalisation Premium en cours.", color=SUCCESS)
        e.set_footer(text="Choisis un service dans le menu pour commencer.")
        return e
    progress = int(req["progress"] or 0)
    total = int(req["total_steps"] or 1)
    channel = guild.get_channel(req["channel_id"]) if req["channel_id"] else None
    destination = channel.mention if isinstance(channel, discord.TextChannel) else f"dossier #{req['id']}"
    key = str(req["training_key"]).replace("premium_service_", "").replace("_", " ").replace("-", " ").title()
    if str(req["training_key"]) == v48.SERVER_BUILD_KEY:
        key = "Création de serveur"
    e = discord.Embed(title="Mon projet Premium", description=f"Ton suivi continue dans {destination}.", color=PREMIUM)
    e.add_field(name="Service", value=key, inline=True)
    e.add_field(name="Progression", value=f"**{progress}/{total}**", inline=True)
    e.add_field(name="Objectif", value=(str(req["objective"]).strip() or "Non précisé")[:1024], inline=False)
    return e


def premium_resources_embed_v51() -> discord.Embed:
    e = discord.Embed(
        title="Ressources Premium",
        description="Des tutoriels avancés sur l’architecture de bot, la production, la sécurité, les permissions, les tests et la fiabilité.",
        color=PREMIUM,
    )
    e.set_image(url=BANNER_URL)
    return e


def server_templates_embed_v51() -> discord.Embed:
    e = discord.Embed(
        title="Créer un serveur avec Aide Bot",
        description=(
            "Choisis un modèle de départ. Le modèle sert de base : ton objectif et tes demandes restent prioritaires. "
            "Aide Bot vérifie le serveur avant de modifier quoi que ce soit et ne supprime pas automatiquement ton contenu existant."
        ),
        color=PREMIUM,
    )
    for data in v48.SERVER_TEMPLATES.values():
        e.add_field(name=data["label"], value=data["description"], inline=True)
    e.set_image(url=BANNER_URL)
    return e


class ServerBuildRequestModalV51(discord.ui.Modal):
    target_server = discord.ui.TextInput(label="ID du serveur à configurer", placeholder="Mode développeur → Copier l’identifiant du serveur", max_length=22)
    requested_name = discord.ui.TextInput(label="Nom souhaité du serveur", placeholder="Optionnel : conserver le nom actuel", required=False, max_length=100)
    purpose = discord.ui.TextInput(
        label="Objectif du serveur", placeholder="Public, activité, résultat attendu...", style=discord.TextStyle.paragraph, max_length=500
    )
    extras = discord.ui.TextInput(
        label="Demandes particulières", placeholder="Rôles, salons, style, tickets, vocaux...", style=discord.TextStyle.paragraph, required=False, max_length=600
    )
    availability = discord.ui.TextInput(label="Disponibilités", placeholder="Ex: samedi 14h-20h", max_length=150)

    def __init__(self, bot: commands.Bot, template_key: str) -> None:
        super().__init__(title=v48.SERVER_TEMPLATES[template_key]["label"][:45])
        self.bot = bot
        self.template_key = template_key

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        raw = str(self.target_server).strip()
        if not raw.isdigit() or not 15 <= len(raw) <= 22:
            return await interaction.response.send_message(
                "ID serveur invalide. Active le mode développeur puis copie l’identifiant du serveur.", ephemeral=True
            )
        existing_project = await v50.active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
        if existing_project:
            return await interaction.response.send_message(embed=active_project_embed_v51(interaction.guild, existing_project), ephemeral=True)
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Le module de tickets est temporairement indisponible.", ephemeral=True)
        target_id = int(raw)
        vip = has_premium(interaction.user)
        objective = (
            f"Serveur cible ID : {target_id}\n"
            f"Modèle : {self.template_key}\n"
            f"Nom souhaité : {str(self.requested_name).strip() or 'Conserver le nom actuel'}\n"
            f"Objectif : {str(self.purpose).strip()}\n"
            f"Options : {str(self.extras).strip() or 'Aucune demande particulière'}"
        )
        await v49._create_internal_request(
            training,
            interaction,
            v48.SERVER_BUILD_KEY,
            {
                "title": "Premium — création de serveur",
                "description": "Création guidée d’un serveur Discord avec vérification avant modification.",
                "steps": ["Validation", "Autorisation", "Audit", "Construction", "Vérification"],
                "vip": True,
                "kind": "vip",
                "difficulty": "Accompagné",
                "duration": "Selon le projet",
            },
            level=f"Modèle {v48.SERVER_TEMPLATES[self.template_key]['label']}",
            objective=objective,
            availability=str(self.availability).strip(),
            budget="Inclus avec Premium" if vip else f"Premium — {_format_robux(self.bot.settings.vip_price_robux)} Robux",
            status="open" if vip else "payment_pending",
            payment_status="not_required" if vip else "pending",
            requires_invite=False,
        )


class ServerTemplateSelectV51(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__(
            placeholder="Choisis un modèle de départ",
            min_values=1,
            max_values=1,
            custom_id="aidebot:v51:server:template",
            options=[
                discord.SelectOption(label=data["label"][:100], value=key, description=data["description"][:100])
                for key, data in v48.SERVER_TEMPLATES.items()
            ][:25],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ServerBuildRequestModalV51(self.bot, self.values[0]))


class ServerTemplateChoiceViewV51(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=900)
        self.add_item(ServerTemplateSelectV51(bot))


class PremiumServiceModalV51(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, service_key: str) -> None:
        data = v48.PREMIUM_SERVICE_FORMS[service_key]
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
            shop = discord.utils.get(interaction.guild.text_channels, name=SHOP_CHANNEL)
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        existing = await v50.active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
        if existing:
            return await interaction.response.send_message(embed=active_project_embed_v51(interaction.guild, existing), ephemeral=True)
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Le module de tickets est temporairement indisponible.", ephemeral=True)
        data = v48.PREMIUM_SERVICE_FORMS[self.service_key]
        objective = "\n\n".join(
            f"{question[0]} : {str(item).strip()}" for question, item in zip(data["questions"], self.inputs)
        )[:3000]
        key = f"premium_service_{self.service_key.replace('-', '_')}"
        await v49._create_internal_request(
            training,
            interaction,
            key,
            {
                "title": f"Premium — {data['label']}",
                "description": data["description"],
                "steps": ["Analyse", "Plan", "Mise en place", "Vérification", "Livraison"],
                "vip": True,
                "kind": "vip",
                "difficulty": "Sur mesure",
                "duration": "Selon le projet",
            },
            level="Service Premium",
            objective=objective,
            availability=str(self.inputs[-1]).strip(),
            budget="Inclus avec Premium",
            status="open",
            payment_status="not_required",
            requires_invite=False,
        )


class PremiumServiceSelectV51(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(label="Créer un serveur", value="build-server", description="Choisir un modèle puis lancer un accompagnement"),
            *[
                discord.SelectOption(label=data["label"][:100], value=key, description=data["description"][:100])
                for key, data in v48.PREMIUM_SERVICE_FORMS.items()
            ],
        ]
        super().__init__(
            placeholder="Choisis un service Premium",
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id="aidebot:v51:premium:service",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        if not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name=SHOP_CHANNEL)
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        existing = await v50.active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
        if existing:
            return await interaction.response.send_message(embed=active_project_embed_v51(interaction.guild, existing), ephemeral=True)
        key = self.values[0]
        if key == "build-server":
            return await interaction.response.send_message(
                embed=server_templates_embed_v51(), view=ServerTemplateChoiceViewV51(self.bot), ephemeral=True
            )
        await interaction.response.send_modal(PremiumServiceModalV51(self.bot, key))


def premium_hub_embed_v51(_price: int | None = None) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Espace Premium",
        description=(
            "Choisis le service qui correspond à ton projet. Les services sont regroupés dans un seul menu "
            "pour garder l’espace simple à utiliser."
        ),
        color=PREMIUM,
    )
    e.add_field(
        name="Services",
        value="Serveur • bot • sécurité • hébergement • organisation • automatisation • audit et amélioration.",
        inline=False,
    )
    e.add_field(name="Suivi", value="Une réalisation active à la fois pour garder un objectif et un responsable clairs.", inline=True)
    e.add_field(name="Ressources", value="Tutoriels avancés accessibles depuis le bouton **Ressources**.", inline=True)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Premium")
    return e


class PremiumHubViewV51(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(PremiumServiceSelectV51(bot))

    async def _require_premium(self, interaction: discord.Interaction) -> bool:
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            return True
        shop = discord.utils.get(interaction.guild.text_channels, name=SHOP_CHANNEL) if interaction.guild else None
        await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        return False

    @discord.ui.button(label="Mon projet", style=discord.ButtonStyle.primary, custom_id="aidebot:v51:premium:project", row=1)
    async def active(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._require_premium(interaction) or not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        req = await v50.active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
        await interaction.response.send_message(embed=active_project_embed_v51(interaction.guild, req), ephemeral=True)

    @discord.ui.button(label="Ressources", style=discord.ButtonStyle.secondary, custom_id="aidebot:v51:premium:resources", row=1)
    async def resources(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._require_premium(interaction):
            return
        await interaction.response.send_message(embed=premium_resources_embed_v51(), view=v48.DirectPremiumVideoView(), ephemeral=True)

    @discord.ui.button(label="Mon espace", style=discord.ButtonStyle.secondary, custom_id="aidebot:v51:premium:space", row=1)
    async def space(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._require_premium(interaction) or not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=await member_space_embed(self.bot, interaction.user), ephemeral=True)


class ShopViewV51(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Passer Premium", style=discord.ButtonStyle.success, custom_id="aidebot:v51:shop:buy")
    async def buy(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            return await interaction.response.send_message(embed=premium_hub_embed_v51(), view=PremiumHubViewV51(self.bot), ephemeral=True)
        await interaction.response.send_modal(PremiumPurchaseModalV51(self.bot))

    @discord.ui.button(label="Voir les avantages", style=discord.ButtonStyle.secondary, custom_id="aidebot:v51:shop:details")
    async def details(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=premium_details_embed_v51(self.bot.settings.vip_price_robux), ephemeral=True)

    @discord.ui.button(label="Continuer gratuitement", style=discord.ButtonStyle.secondary, custom_id="aidebot:v51:shop:free")
    async def free(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=center.guide_index_embed(), view=center.GuideIndexView(), ephemeral=True)


def server_build_control_embed_v51(req, ready: bool) -> discord.Embed:
    data = v48._parse_build_data(str(req["objective"]))
    template = v48.SERVER_TEMPLATES[data.template_key]["label"] if data else "Inconnu"
    e = discord.Embed(
        title="Création de serveur — suivi",
        description=(
            "Ton service est prêt. **Autorise Aide Bot → lance l’audit → vérifie le plan → confirme la construction.**"
            if ready
            else "Ta demande est enregistrée. Les étapes de construction seront disponibles quand ton accès Premium sera actif."
        ),
        color=SUCCESS if ready else WARNING,
    )
    if data:
        e.add_field(name="Serveur", value=f"`{data.target_guild_id}`", inline=True)
        e.add_field(name="Modèle", value=template, inline=True)
        e.add_field(name="Nom", value=(data.requested_name or "Conserver le nom actuel")[:200], inline=True)
    e.add_field(
        name="Avant toute modification",
        value=(
            "Aide Bot vérifie ses permissions, affiche le plan et exporte un état du serveur. "
            "Le contenu existant n’est pas supprimé automatiquement et la construction demande une confirmation explicite."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    return e


def training_embed_v51(self) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Formations",
        description="Choisis le parcours qui correspond à ce que tu veux apprendre. Chaque parcours utilise un formulaire adapté au sujet.",
        color=COLOR,
    )
    e.add_field(name="Parcours accessibles à tous", value="Discord • création de serveur • rôles et permissions • sécurité • premier bot.", inline=False)
    e.add_field(
        name="Parcours avancés",
        value="Les membres Premium disposent aussi de parcours et de ressources plus poussés dans leur espace dédié.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Choisis un parcours puis avance étape par étape")
    return e


async def _cleanup_panel_duplicates(bot: commands.Bot, channel: discord.TextChannel, current_title: str) -> None:
    if bot.user is None:
        return
    known_titles = LEGACY_PANEL_TITLES.get(channel.name)
    if not known_titles:
        return
    kept_current = False
    try:
        async for message in channel.history(limit=100):
            if message.author.id != bot.user.id or not message.embeds:
                continue
            titles = {embed.title for embed in message.embeds if embed.title}
            if current_title in titles and not kept_current:
                kept_current = True
                continue
            if titles & known_titles:
                try:
                    await message.delete()
                except (discord.Forbidden, discord.HTTPException):
                    pass
    except (discord.Forbidden, discord.HTTPException):
        pass


def _install_setup_cleanup() -> None:
    from aidebot.cogs.setup_server import SetupServerCog

    if getattr(SetupServerCog, "_aidebot_v51_panel_cleanup", False):
        return
    original_upsert = SetupServerCog._upsert_panel

    async def upsert(self, channel, embed, view=None):
        if isinstance(channel, discord.TextChannel) and embed.title:
            await _cleanup_panel_duplicates(self.bot, channel, embed.title)
        return await original_upsert(self, channel, embed, view)

    SetupServerCog._upsert_panel = upsert
    SetupServerCog._training_embed = training_embed_v51
    SetupServerCog._aidebot_v51_panel_cleanup = True


def _install_runtime() -> None:
    center.CenterView = HelpCenterViewV51
    center.center_embed = help_center_embed_v51
    center_autopost.CenterView = HelpCenterViewV51
    center_autopost.center_embed = help_center_embed_v51
    center_autopost.CENTER_TITLE = CENTER_TITLE

    public_panels.WelcomeView = WelcomeViewV51
    public_panels.welcome_embed = welcome_embed_v51
    public_panels.ShopView = ShopViewV51
    public_panels.shop_embed = shop_embed_v51
    public_panels.premium_embed = premium_details_embed_v51

    storefront.WelcomeView = WelcomeViewV51
    storefront.ShopView = ShopViewV51
    storefront.shop_embed = shop_embed_v51

    v48.ShopV48View = ShopViewV51
    v48.PremiumHubV48View = PremiumHubViewV51
    v48.premium_shop_embed = shop_embed_v51
    v48.premium_v48_hub_embed = premium_hub_embed_v51

    v49.ShopV49View = ShopViewV51
    v49.PremiumHubV49View = PremiumHubViewV51
    v49.premium_shop_embed = shop_embed_v51
    v49.premium_v49_hub_embed = premium_hub_embed_v51
    v49.server_build_control_embed = server_build_control_embed_v51

    v50.ShopV50View = ShopViewV51
    v50.PremiumHubV50View = PremiumHubViewV51
    v50.premium_shop_embed = shop_embed_v51
    v50.premium_v50_hub_embed = premium_hub_embed_v51
    v50.server_build_control_embed = server_build_control_embed_v51
    v50.ServerBuildV50TicketView = v49.ServerBuildV49TicketView

    import aidebot.cogs.setup_server as setup_server

    setup_server.WelcomeView = WelcomeViewV51
    setup_server.welcome_embed = welcome_embed_v51
    setup_server.CenterView = HelpCenterViewV51
    setup_server.center_embed = help_center_embed_v51
    setup_server.ShopView = ShopViewV51
    setup_server.shop_embed = shop_embed_v51

    _install_setup_cleanup()


class ProductExperienceV51Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._reconciled_guilds: set[int] = set()

    async def cog_load(self) -> None:
        _install_runtime()
        self.bot.add_view(WelcomeViewV51(self.bot))
        self.bot.add_view(HelpCenterViewV51(self.bot))
        self.bot.add_view(ShopViewV51(self.bot))
        self.bot.add_view(PremiumHubViewV51(self.bot))

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        setup_cog = self.bot.get_cog("SetupServerCog")
        if setup_cog is None:
            return
        for guild in self.bot.guilds:
            if guild.id in self._reconciled_guilds:
                continue
            self._reconciled_guilds.add(guild.id)

            bienvenue = discord.utils.get(guild.text_channels, name="👋・bienvenue")
            centre = discord.utils.get(guild.text_channels, name="🎓・centre-aide")
            shop = discord.utils.get(guild.text_channels, name=SHOP_CHANNEL)
            premium_hub = discord.utils.get(guild.text_channels, name=v48.PREMIUM_HUB_CHANNEL)

            if bienvenue is not None:
                await setup_cog._upsert_panel(bienvenue, welcome_embed_v51(), WelcomeViewV51(self.bot))
            if centre is not None:
                await setup_cog._upsert_panel(centre, help_center_embed_v51(), HelpCenterViewV51(self.bot))
            if shop is not None:
                await setup_cog._upsert_panel(shop, shop_embed_v51(self.bot.settings.vip_price_robux), ShopViewV51(self.bot))
            if premium_hub is not None:
                await setup_cog._upsert_panel(premium_hub, premium_hub_embed_v51(), PremiumHubViewV51(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProductExperienceV51Cog(bot))
