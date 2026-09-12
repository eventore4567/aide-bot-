from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

import aidebot.cogs.premium_service_v48 as v48
import aidebot.cogs.premium_service_v49 as v49
import aidebot.public_panels as public_panels
from aidebot.cogs.experience_v43 import member_space_embed
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed

ELITE_PRICE_ROBUX = 10_000
PREMIUM_COLOR = 0xEB459E
SUCCESS = 0x57F287
WARNING = 0xF1C40F
SHOP_CHANNEL = "🛒・shop"
SERVER_BUILD_KEY = v48.SERVER_BUILD_KEY

# V50 garde les custom_id V49 pour que les panneaux déjà publiés continuent
# de fonctionner, mais remplace leur logique par l'expérience finale.
_V48_HUB_VIEW = v49._V48_HUB_VIEW
_V48_SHOP_VIEW = v49._V48_SHOP_VIEW
_V48_SERVER_VIEW = v49._V48_SERVER_VIEW


def is_elite_key(training_key: str) -> bool:
    return training_key == SERVER_BUILD_KEY or training_key.startswith("premium_service_")


async def active_elite_request(bot: commands.Bot, guild_id: int, user_id: int):
    """Return the user's single active Elite delivery, if any.

    Premium access is broad, but execution stays clean: one implementation
    dossier at a time. Audits/resources remain available while a mission runs.
    """
    rows = await bot.db.active_requests_for_user(guild_id, user_id, limit=25)
    for row in rows:
        if is_elite_key(str(row["training_key"])):
            return row
    return None


def _destination(guild: discord.Guild, req) -> str:
    channel = guild.get_channel(req["channel_id"]) if req and req["channel_id"] else None
    return channel.mention if isinstance(channel, discord.TextChannel) else f"dossier #{req['id']}"


def elite_scope_embed(price: int) -> discord.Embed:
    price = max(price, ELITE_PRICE_ROBUX)
    display_price = f"{price:,}".replace(",", " ")
    e = discord.Embed(
        title="Premium Elite — Standard de service",
        description=(
            f"**{display_price} Robux** correspond à un **pack de réalisation accompagné**, pas à un simple rôle Discord. "
            "Le client garde l'accès à l'espace Elite, aux audits et aux ressources, tandis que les réalisations sont traitées **une mission active à la fois** pour garder un suivi propre."
        ),
        color=PREMIUM_COLOR,
    )
    e.add_field(
        name="Inclus",
        value=(
            "• Audit 360° et recommandations prioritaires\n"
            "• 15+ services spécialisés\n"
            "• 12 modèles de serveur + construction sécurisée\n"
            "• Academy Elite et vidéos VIP\n"
            "• Snapshot avant modification + dossier de livraison\n"
            "• Ajustements liés au cahier des charges de la mission"
        ),
        inline=False,
    )
    e.add_field(
        name="Méthode obligatoire",
        value="**Cahier des charges → Diagnostic → Plan → Mise en œuvre → Tests → Validation client → Dossier final.**",
        inline=False,
    )
    e.add_field(
        name="Cadre propre",
        value=(
            "Une seule mission de réalisation est active à la fois. Une fois terminée, le membre peut ouvrir la suivante. "
            "Les audits, l'Academy, les vidéos et l'espace membre restent disponibles pendant le suivi."
        ),
        inline=False,
    )
    e.add_field(
        name="Sécurité",
        value=(
            "Aide Bot ne demande jamais token, mot de passe, cookie, 2FA ou code de récupération. "
            "La construction ne supprime pas automatiquement le contenu existant, exporte un snapshot et exige `CONSTRUIRE`."
        ),
        inline=False,
    )
    e.add_field(
        name="Actions qui restent manuelles",
        value="La Direction valide le paiement et Discord impose l'autorisation OAuth2 d'un propriétaire/admin avant l'ajout du bot sur un serveur client.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V50 • Premium Elite • valeur claire, périmètre clair, livraison vérifiable")
    return e


def premium_v50_hub_embed(price: int) -> discord.Embed:
    e = v49.premium_v49_hub_embed(max(price, ELITE_PRICE_ROBUX))
    e.title = "Aide Bot — Premium Elite V50"
    e.description = (
        (e.description or "")
        + "\n\n**V50 ajoute un vrai standard de livraison :** cahier des charges avant achat, une mission active à la fois, critères d'acceptation, ajustements client et validation du résultat."
    )[:4000]
    e.add_field(
        name="Une mission = un dossier propre",
        value="Chaque réalisation possède un objectif, des livrables et des critères d'acceptation. Pas de tickets Elite lancés dans tous les sens.",
        inline=False,
    )
    e.set_footer(text="Aide Bot V50 • Elite = cadrage → exécution → validation → dossier final")
    return e


def premium_shop_embed(price: int) -> discord.Embed:
    price = max(price, ELITE_PRICE_ROBUX)
    e = v49.premium_shop_embed(price)
    e.title = "Aide Bot — Premium Elite 10K"
    e.description = (
        f"**Premium Elite — {price:,} Robux**\n\n".replace(",", " ")
        + "Avant le paiement, Aide Bot demande maintenant un **cahier des charges** : projet, situation actuelle, résultat attendu et critères d'acceptation. "
        "Le but est que le client sache exactement ce qu'il achète et que le staff sache exactement ce qu'il doit livrer."
    )
    e.add_field(name="Résultat, pas juste accès", value="Audit 360°, réalisation, tests, validation client et dossier final. Le rôle VIP n'est que la clé d'accès au service.", inline=False)
    e.add_field(name="Organisation", value="Une mission de réalisation active par membre. Les audits, vidéos et ressources Elite restent utilisables en parallèle.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V50 • 10 000 Robux • cahier des charges + réalisation + validation")
    return e


def active_project_embed(guild: discord.Guild, req) -> discord.Embed:
    if req is None:
        e = discord.Embed(
            title="Premium Elite — aucun projet actif",
            description="Tu peux démarrer une nouvelle mission depuis le sélecteur Elite. Les audits et ressources sont disponibles immédiatement.",
            color=SUCCESS,
        )
        e.set_footer(text="Aide Bot V50 • un projet actif à la fois")
        return e

    progress = int(req["progress"] or 0)
    total = int(req["total_steps"] or 1)
    e = discord.Embed(
        title=f"Premium Elite — dossier #{req['id']}",
        description=f"Ton projet actif est suivi dans {_destination(guild, req)}.",
        color=PREMIUM_COLOR,
    )
    e.add_field(name="Type", value=str(req["training_key"]).replace("premium_service_", "").replace("_", " ").title(), inline=True)
    e.add_field(name="État", value=str(req["status"]).replace("_", " ").title(), inline=True)
    e.add_field(name="Progression", value=f"**{progress}/{total}**", inline=True)
    e.add_field(name="Objectif", value=(str(req["objective"]).strip() or "Non précisé")[:1024], inline=False)
    e.set_footer(text="Aide Bot V50 • termine ce dossier avant d'ouvrir une nouvelle réalisation")
    return e


class ElitePurchaseModalV50(discord.ui.Modal, title="Premium Elite — cahier des charges"):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.project_type = discord.ui.TextInput(
            label="Type de projet",
            placeholder="Serveur, bot, sécurité, automatisation, migration...",
            max_length=120,
        )
        self.current_state = discord.ui.TextInput(
            label="Situation actuelle",
            placeholder="Ce qui existe déjà, ce qui marche et ce qui bloque",
            style=discord.TextStyle.paragraph,
            max_length=650,
        )
        self.goal = discord.ui.TextInput(
            label="Résultat principal attendu",
            placeholder="Le résultat concret que tu veux obtenir à la fin",
            style=discord.TextStyle.paragraph,
            max_length=650,
        )
        self.acceptance = discord.ui.TextInput(
            label="Critères d'acceptation",
            placeholder="Comment saura-t-on que la mission est réussie ?",
            style=discord.TextStyle.paragraph,
            max_length=600,
        )
        self.availability = discord.ui.TextInput(
            label="Disponibilités",
            placeholder="Ex: samedi 14h-20h",
            max_length=150,
        )
        for item in (self.project_type, self.current_state, self.goal, self.acceptance, self.availability):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if has_premium(interaction.user):
            return await interaction.response.send_message(
                embed=premium_member_embed(interaction.user),
                ephemeral=True,
            )
        existing = await self.bot.db.active_request_for_training(interaction.guild.id, interaction.user.id, "vip")
        if existing:
            return await interaction.response.send_message(
                f"Ton activation Premium Elite est déjà en cours dans {_destination(interaction.guild, existing)}.",
                ephemeral=True,
            )
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de tickets indisponible.", ephemeral=True)
        objective = (
            f"Type de projet : {str(self.project_type).strip()}\n\n"
            f"Situation actuelle : {str(self.current_state).strip()}\n\n"
            f"Résultat principal : {str(self.goal).strip()}\n\n"
            f"Critères d'acceptation : {str(self.acceptance).strip()}"
        )
        await training.create_request_channel(
            interaction,
            "vip",
            level="Premium Elite V50 — cahier des charges validé par le client",
            objective=objective,
            availability=str(self.availability).strip(),
            budget="Premium Elite — 10 000 Robux",
            status="payment_pending",
            payment_status="pending",
            requires_invite=False,
        )


class PremiumServiceModalV50(v49.PremiumServiceModalV49):
    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild and isinstance(interaction.user, discord.Member):
            existing = await active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
            if existing:
                return await interaction.response.send_message(
                    f"Tu as déjà une mission Elite active : {_destination(interaction.guild, existing)}. Termine-la avant d'en ouvrir une autre.",
                    ephemeral=True,
                )
        await super().on_submit(interaction)


class ServerBuildRequestModalV50(v49.ServerBuildRequestModalV49):
    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild and isinstance(interaction.user, discord.Member):
            existing = await active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
            if existing:
                return await interaction.response.send_message(
                    f"Tu as déjà une mission Elite active : {_destination(interaction.guild, existing)}. Termine-la avant de commander une autre réalisation.",
                    ephemeral=True,
                )
        await super().on_submit(interaction)


class ServerTemplateSelectV50(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__(
            placeholder="Choisis le modèle de départ",
            min_values=1,
            max_values=1,
            custom_id="aidebot:v49:server:template",
            options=[
                discord.SelectOption(label=data["label"][:100], value=key, description=data["description"][:100])
                for key, data in v48.SERVER_TEMPLATES.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ServerBuildRequestModalV50(self.bot, self.values[0]))


class ServerTemplateChoiceViewV50(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=900)
        self.add_item(ServerTemplateSelectV50(bot))


class PremiumServiceSelectV50(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(label="Serveur sur mesure", value="build-server", description="12 modèles + audit + snapshot + construction"),
            *[
                discord.SelectOption(label=data["label"][:100], value=key, description=data["description"][:100])
                for key, data in v48.PREMIUM_SERVICE_FORMS.items()
            ],
        ]
        super().__init__(
            placeholder="Choisis ta mission Premium Elite",
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id="aidebot:v49:premium:service",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        if not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name=SHOP_CHANNEL)
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        existing = await active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
        if existing:
            return await interaction.response.send_message(embed=active_project_embed(interaction.guild, existing), ephemeral=True)
        key = self.values[0]
        if key == "build-server":
            return await interaction.response.send_message(
                embed=v49.server_templates_v49_embed(),
                view=ServerTemplateChoiceViewV50(self.bot),
                ephemeral=True,
            )
        await interaction.response.send_modal(PremiumServiceModalV50(self.bot, key))


class EliteAdjustmentModal(discord.ui.Modal, title="Demander un ajustement Elite"):
    change = discord.ui.TextInput(
        label="Ajustement demandé",
        placeholder="Explique précisément ce qui ne correspond pas encore au cahier des charges",
        style=discord.TextStyle.paragraph,
        max_length=900,
    )

    def __init__(self, bot: commands.Bot, request_id: int) -> None:
        super().__init__()
        self.bot = bot
        self.request_id = request_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        req = await self.bot.db.request_by_id(self.request_id)
        if req is None or interaction.user.id != int(req["user_id"]):
            return await interaction.response.send_message("Cette action est réservée au client du dossier.", ephemeral=True)
        if str(req["status"]) in {"closed", "cancelled"}:
            return await interaction.response.send_message("Ce dossier est déjà archivé.", ephemeral=True)
        e = discord.Embed(
            title="Ajustement demandé par le client",
            description=str(self.change).strip()[:4000],
            color=WARNING,
        )
        e.add_field(name="Règle", value="L'ajustement doit rester lié au cahier des charges initial. Une nouvelle réalisation complète doit passer par un nouveau dossier.", inline=False)
        e.set_footer(text=f"Aide Bot V50 • Dossier #{req['id']} • retour client")
        if isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
        training = self.bot.get_cog("TrainingCog")
        if training and interaction.guild:
            await training.log_action(interaction.guild, "Ajustement Elite demandé", f"Dossier #{req['id']} • client {interaction.user.mention}")
        await interaction.response.send_message("Ajustement ajouté au dossier.", ephemeral=True)


class EliteDeliveryView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    async def _request(self, interaction: discord.Interaction):
        if interaction.channel is None:
            return None
        return await self.bot.db.request_by_channel(interaction.channel.id)

    @discord.ui.button(label="Voir les livrables", style=discord.ButtonStyle.secondary, custom_id="aidebot:v50:elite:deliverables")
    async def deliverables(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await self._request(interaction)
        if req is None or not is_elite_key(str(req["training_key"])):
            return await interaction.response.send_message("Ce salon n'est pas un dossier Premium Elite.", ephemeral=True)
        card = v49.mission_elite_embed(req) if str(req["training_key"]).startswith("premium_service_") else v49.server_build_control_embed(req, str(req["payment_status"]) != "pending")
        await interaction.response.send_message(embed=card, ephemeral=True)

    @discord.ui.button(label="Demander un ajustement", style=discord.ButtonStyle.primary, custom_id="aidebot:v50:elite:adjust")
    async def adjust(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await self._request(interaction)
        if req is None or interaction.user.id != int(req["user_id"]):
            return await interaction.response.send_message("Cette action est réservée au client du dossier.", ephemeral=True)
        await interaction.response.send_modal(EliteAdjustmentModal(self.bot, int(req["id"])))

    @discord.ui.button(label="Valider le résultat", style=discord.ButtonStyle.success, custom_id="aidebot:v50:elite:accept")
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await self._request(interaction)
        if req is None or interaction.user.id != int(req["user_id"]):
            return await interaction.response.send_message("Cette action est réservée au client du dossier.", ephemeral=True)
        if not is_elite_key(str(req["training_key"])):
            return await interaction.response.send_message("Ce salon n'est pas un dossier Premium Elite.", ephemeral=True)
        progress = int(req["progress"] or 0)
        total = int(req["total_steps"] or 1)
        if str(req["status"]) not in {"completed", "closed"} and progress < total:
            return await interaction.response.send_message(
                f"La livraison n'est pas encore au stade final (**{progress}/{total}**). Utilise ce bouton quand les étapes prévues sont terminées.",
                ephemeral=True,
            )
        e = discord.Embed(
            title="Livraison validée par le client",
            description=f"<@{req['user_id']}> confirme que le résultat présenté correspond au cahier des charges du dossier **#{req['id']}**.",
            color=SUCCESS,
        )
        e.add_field(name="Après validation", value="Le staff peut finaliser/archiver le dossier et conserver le rapport final comme référence.", inline=False)
        e.set_footer(text="Aide Bot V50 • validation client")
        if isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
        training = self.bot.get_cog("TrainingCog")
        if training and interaction.guild:
            await training.log_action(interaction.guild, "Livraison Elite validée", f"Dossier #{req['id']} • client {interaction.user.mention}")
        await interaction.response.send_message("Validation enregistrée dans le dossier.", ephemeral=True)


class PremiumHubV50View(v49.PremiumHubV49View):
    def __init__(self, bot: commands.Bot) -> None:
        discord.ui.View.__init__(self, timeout=None)
        self.bot = bot
        self.add_item(PremiumServiceSelectV50(bot))

    @discord.ui.button(label="Serveur sur mesure", style=discord.ButtonStyle.success, custom_id="aidebot:v49:premium:server", row=1)
    async def server(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        if not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name=SHOP_CHANNEL)
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        existing = await active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
        if existing:
            return await interaction.response.send_message(embed=active_project_embed(interaction.guild, existing), ephemeral=True)
        await interaction.response.send_message(embed=v49.server_templates_v49_embed(), view=ServerTemplateChoiceViewV50(self.bot), ephemeral=True)

    @discord.ui.button(label="Projet 360°", style=discord.ButtonStyle.secondary, custom_id="aidebot:v49:premium:project", row=2)
    async def project(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        if not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name=SHOP_CHANNEL)
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        existing = await active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
        if existing:
            return await interaction.response.send_message(embed=active_project_embed(interaction.guild, existing), ephemeral=True)
        await interaction.response.send_modal(PremiumServiceModalV50(self.bot, "project-360"))

    @discord.ui.button(label="Mon projet actif", style=discord.ButtonStyle.secondary, custom_id="aidebot:v50:premium:active", row=3)
    async def active(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        if not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name=SHOP_CHANNEL)
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        req = await active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
        await interaction.response.send_message(embed=active_project_embed(interaction.guild, req), ephemeral=True)

    @discord.ui.button(label="Standard Elite", style=discord.ButtonStyle.secondary, custom_id="aidebot:v50:premium:scope", row=3)
    async def scope(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=elite_scope_embed(self.bot.settings.vip_price_robux), ephemeral=True)


class ShopV50View(v49.ShopV49View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.bot = bot

    @discord.ui.button(label="Acheter Elite 10K", style=discord.ButtonStyle.success, custom_id="aidebot:shop:premium", row=0)
    async def premium(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            return await interaction.response.send_message(embed=premium_member_embed(interaction.user), ephemeral=True)
        await interaction.response.send_modal(ElitePurchaseModalV50(self.bot))

    @discord.ui.button(label="Ce que couvre 10K", style=discord.ButtonStyle.secondary, custom_id="aidebot:shop:details", row=0)
    async def details(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=elite_scope_embed(self.bot.settings.vip_price_robux), ephemeral=True)

    @discord.ui.button(label="Commander un serveur", style=discord.ButtonStyle.primary, custom_id="aidebot:v49:shop:server", row=1)
    async def server(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if isinstance(interaction.user, discord.Member) and interaction.guild and has_premium(interaction.user):
            existing = await active_elite_request(self.bot, interaction.guild.id, interaction.user.id)
            if existing:
                return await interaction.response.send_message(embed=active_project_embed(interaction.guild, existing), ephemeral=True)
        await interaction.response.send_message(embed=v49.server_templates_v49_embed(), view=ServerTemplateChoiceViewV50(self.bot), ephemeral=True)

    @discord.ui.button(label="Voir le pack 10K", style=discord.ButtonStyle.secondary, custom_id="aidebot:v49:shop:pack", row=1)
    async def pack(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            return await interaction.response.send_message(embed=premium_v50_hub_embed(self.bot.settings.vip_price_robux), view=PremiumHubV50View(self.bot), ephemeral=True)
        await interaction.response.send_message(embed=premium_v50_hub_embed(self.bot.settings.vip_price_robux), ephemeral=True)


class ServerBuildV50TicketView(v49.ServerBuildV49TicketView):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.bot = bot

    @discord.ui.button(label="Standard de livraison", style=discord.ButtonStyle.secondary, custom_id="aidebot:v50:server:scope", row=2)
    async def scope(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=elite_scope_embed(self.bot.settings.vip_price_robux), ephemeral=True)



def mission_elite_v50_embed(req) -> discord.Embed | None:
    e = v49.mission_elite_embed(req)
    if e is None:
        return None
    e.title = e.title.replace("Premium Elite", "Premium Elite V50")
    e.add_field(
        name="Validation client",
        value="À la fin, le client peut demander un ajustement lié au cahier des charges ou cliquer sur **Valider le résultat**.",
        inline=False,
    )
    e.set_footer(text=f"Aide Bot V50 • Dossier #{req['id']} • mission cadrée et vérifiable")
    return e


def server_build_control_embed(req, ready: bool) -> discord.Embed:
    e = v49.server_build_control_embed(req, ready)
    e.title = "Premium Elite V50 — livraison serveur"
    e.add_field(name="Standard V50", value="Une mission active à la fois • snapshot avant modification • confirmation explicite • rapport avant/après • validation client.", inline=False)
    e.set_footer(text="Aide Bot V50 • OAuth2 → audit → snapshot → plan → construction → validation")
    return e


def _patch_runtime() -> None:
    # Les patchers V48 pilotent /setup, /buy et le déblocage après paiement.
    # On leur injecte les composants V50 sans toucher au moteur de tickets.
    v49.ShopV49View = ShopV50View
    v49.PremiumHubV49View = PremiumHubV50View
    v49.ServerBuildV49TicketView = ServerBuildV50TicketView
    v49.premium_shop_embed = premium_shop_embed
    v49.premium_v49_hub_embed = premium_v50_hub_embed

    v48.ShopV48View = ShopV50View
    v48.PremiumHubV48View = PremiumHubV50View
    v48.premium_shop_embed = premium_shop_embed
    v48.premium_v48_hub_embed = premium_v50_hub_embed


class PremiumServiceV50Cog(commands.Cog, name="PremiumServiceV48Cog"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        _patch_runtime()
        v48._install_shop_patch()
        v48._install_setup_patch()
        v48._install_payment_patch()

        self.bot.add_view(PremiumHubV50View(self.bot))
        self.bot.add_view(ShopV50View(self.bot))
        self.bot.add_view(ServerBuildV50TicketView(self.bot))
        self.bot.add_view(EliteDeliveryView(self.bot))
        self.bot.add_view(v48.DirectPremiumVideoView())

        # Les anciens panneaux V48 conservent leurs anciens custom_id.
        self.bot.add_view(_V48_HUB_VIEW(self.bot))
        self.bot.add_view(_V48_SHOP_VIEW(self.bot))
        self.bot.add_view(_V48_SERVER_VIEW(self.bot))

    async def unlock_server_build_ticket(self, channel: discord.TextChannel, req) -> None:
        try:
            await channel.send(
                embed=server_build_control_embed(req, True),
                view=ServerBuildV50TicketView(self.bot),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("ticket-"):
            return
        req = None
        for _ in range(12):
            await asyncio.sleep(0.35)
            req = await self.bot.db.request_by_channel(channel.id)
            if req is not None:
                break
        if req is None:
            return
        key = str(req["training_key"])
        if key == SERVER_BUILD_KEY:
            client = channel.guild.get_member(int(req["user_id"]))
            ready = v48._request_unlocked(req, client)
            try:
                await channel.send(
                    embed=server_build_control_embed(req, ready),
                    view=ServerBuildV50TicketView(self.bot),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                await channel.send(
                    embed=discord.Embed(
                        title="Validation de livraison",
                        description="Quand la réalisation arrive à sa fin, utilise les boutons ci-dessous pour demander un ajustement ou valider le résultat.",
                        color=PREMIUM_COLOR,
                    ),
                    view=EliteDeliveryView(self.bot),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            return
        card = mission_elite_v50_embed(req)
        if card is not None:
            try:
                await channel.send(embed=card, view=EliteDeliveryView(self.bot), allowed_mentions=discord.AllowedMentions.none())
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PremiumServiceV50Cog(bot))
