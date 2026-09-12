from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs.center import (
    CenterView,
    GuideIndexView,
    HelpRequestModal,
    PremiumView,
    VideoView,
    center_embed,
    guide_index_embed,
    premium_embed,
    videos_embed,
)
from aidebot.cogs.training import PremiumPurchaseModal, TrainingPanel, TrainingRequestModal, TrainingSelect
from aidebot.cogs.training_experience_v42 import V42TrainingPanel, V42TrainingSelect
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed


# Compatibilité V40/V41 : les anciens panneaux persistants utilisent encore
# TrainingSelect. On remplace seulement leur callback et l'initialisation des
# nouveaux TrainingPanel afin que les anciens messages restent fonctionnels
# pendant que /setup publie l'expérience V42.
TrainingSelect.callback = V42TrainingSelect.callback


def _v42_training_panel_init(self: TrainingPanel, cog: commands.Cog) -> None:
    discord.ui.View.__init__(self, timeout=None)
    self.add_item(V42TrainingSelect(cog))


TrainingPanel.__init__ = _v42_training_panel_init


WELCOME_TITLE = "Bienvenue — Aide Bot"
SHOP_TITLE = "Aide Bot — Boutique & abonnement Premium"
TICKET_TITLE = "Aide Bot — Ouvrir une demande"
VIDEOS_TITLE = "Aide Bot — Vidéos & guides"


def welcome_embed() -> discord.Embed:
    e = discord.Embed(
        title=WELCOME_TITLE,
        description=(
            "Bienvenue sur **Aide Bot**. Ici, chaque salon a un rôle précis : tu n’as pas à deviner quelle commande utiliser.\n\n"
            "**Apprendre gratuitement** → `🎓・centre-aide`\n"
            "**Choisir une formation** → `🎓・formations`\n"
            "**Regarder des tutoriels** → `🎥・videos-guides`\n"
            "**Poser un problème précis** → `🎫・ouvrir-ticket`\n"
            "**Acheter Premium** → `🛒・shop` ou `/buy`\n\n"
            "Le bot fonctionne surtout avec **boutons, menus et formulaires**. Les deux seules commandes publiques restent `/setup` et `/buy`."
        ),
        color=0x5865F2,
    )
    e.add_field(
        name="Avant de commencer",
        value=(
            "Ne partage jamais de token, mot de passe, cookie ou code 2FA. Dans un ticket, explique le résultat attendu, ce qui bloque et ce que tu as déjà testé."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Un espace = une fonction • Navigation par panneaux")
    return e


def shop_embed(price_robux: int) -> discord.Embed:
    e = discord.Embed(
        title=SHOP_TITLE,
        description=(
            f"**Premium — {price_robux} Robux**\n"
            "Le gratuit reste utile. Premium ajoute surtout un **accompagnement humain personnalisé** et les parcours avancés.\n\n"
            "L’achat se fait **uniquement ici ou avec `/buy`**. Cliquer sur Premium ailleurs ne crée jamais un achat : sans rôle VIP, le bot affiche simplement que l’abonnement manque."
        ),
        color=0x9B59B6,
    )
    e.add_field(
        name="Ce que Premium débloque",
        value=(
            "• rôle **💎・VIP** après validation\n"
            "• accompagnement sur mesure\n"
            "• serveur professionnel\n"
            "• bot avancé\n"
            "• sécurité / audit avancé\n"
            "• suivi jusqu’au résultat final"
        ),
        inline=True,
    )
    e.add_field(
        name="Activation",
        value=(
            "**1.** Acheter Premium\n"
            "**2.** Remplir le formulaire d’achat\n"
            "**3.** Ticket privé de paiement\n"
            "**4.** Validation par la Direction\n"
            "**5.** Rôle VIP automatique\n"
            "**6.** Parcours Premium débloqués"
        ),
        inline=True,
    )
    e.add_field(
        name="Sécurité",
        value="Aucun membre du staff ne doit demander ton mot de passe, token Discord, cookie, code 2FA ou code de récupération.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Boutique = seul point d’achat Premium")
    return e


def ticket_embed() -> discord.Embed:
    e = discord.Embed(
        title=TICKET_TITLE,
        description=(
            "Un ticket sert à traiter **une demande réelle**, pas à afficher un pavé générique. Le formulaire résume ton problème et le ticket montre ensuite clairement "
            "qui le prend, son état, la première étape et la progression.\n\n"
            "**Aide gratuite** : problème précis, diagnostic et explication.\n"
            "**Premium** : uniquement pour les membres qui ont déjà **💎・VIP**. Pour acheter Premium, passe par `🛒・shop` ou `/buy`."
        ),
        color=0x3498DB,
    )
    e.add_field(
        name="Prépare ces informations",
        value="Résultat attendu • erreur exacte • ce que tu as essayé • capture utile si nécessaire • disponibilités.",
        inline=True,
    )
    e.add_field(
        name="Dans le ticket",
        value="Un seul staff est assigné • progression par étapes • fin claire • avis puis archivage.",
        inline=True,
    )
    e.add_field(
        name="Jamais dans un ticket",
        value="Token, mot de passe, cookie, code 2FA, code de récupération ou information bancaire.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Ticket clair → diagnostic clair → résultat clair")
    return e


def videos_panel_embed() -> discord.Embed:
    e = videos_embed()
    e.title = VIDEOS_TITLE
    e.description = (
        "Une vraie bibliothèque visuelle : Discord, permissions, bots, Developer Portal, Python, slash commands, boutons/formulaires, Railway, GitHub, tickets, sécurité, bases de données, tests et CI.\n\n"
        "Les vidéos servent à **voir les manipulations** ; les guides Aide Bot expliquent pourquoi les faire et ce qu’il faut vérifier.\n\n"
        + (e.description or "")
    )[:4000]
    return e


class WelcomeView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Centre d’aide", style=discord.ButtonStyle.primary, custom_id="aidebot:welcome:center")
    async def center(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        cog = interaction.client.get_cog("CenterCog")
        if cog is None:
            return await interaction.response.send_message("Centre d’aide indisponible.", ephemeral=True)
        await interaction.response.send_message(embed=center_embed(self.bot.settings.vip_price_robux), view=CenterView(cog), ephemeral=True)

    @discord.ui.button(label="Ouvrir un ticket", style=discord.ButtonStyle.success, custom_id="aidebot:welcome:ticket")
    async def ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        cog = interaction.client.get_cog("CenterCog")
        if cog is None:
            return await interaction.response.send_message("Centre d’aide indisponible.", ephemeral=True)
        await interaction.response.send_modal(HelpRequestModal(cog))

    @discord.ui.button(label="Boutique", style=discord.ButtonStyle.secondary, custom_id="aidebot:welcome:shop")
    async def shop(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=shop_embed(self.bot.settings.vip_price_robux), view=ShopView(self.bot), ephemeral=True)


class ShopView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Acheter Premium", style=discord.ButtonStyle.success, custom_id="aidebot:shop:premium")
    async def premium(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            return await interaction.response.send_message(embed=premium_member_embed(interaction.user), ephemeral=True)
        training = interaction.client.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_modal(PremiumPurchaseModal(training))

    @discord.ui.button(label="Mon statut Premium", style=discord.ButtonStyle.primary, custom_id="aidebot:shop:status")
    async def status(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        if has_premium(interaction.user):
            return await interaction.response.send_message(embed=premium_member_embed(interaction.user), ephemeral=True)
        shop = interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None
        await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)

    @discord.ui.button(label="Voir les détails", style=discord.ButtonStyle.secondary, custom_id="aidebot:shop:details")
    async def details(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        center = interaction.client.get_cog("CenterCog")
        if center is None:
            return await interaction.response.send_message("Centre d’aide indisponible.", ephemeral=True)
        await interaction.response.send_message(embed=premium_embed(self.bot.settings.vip_price_robux), ephemeral=True)

    @discord.ui.button(label="Guides gratuits", style=discord.ButtonStyle.secondary, custom_id="aidebot:shop:free")
    async def free(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=guide_index_embed(), view=GuideIndexView(), ephemeral=True)


class TicketEntryView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Aide gratuite", style=discord.ButtonStyle.primary, custom_id="aidebot:ticket-entry:free")
    async def free(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        center = interaction.client.get_cog("CenterCog")
        if center is None:
            return await interaction.response.send_message("Centre d’aide indisponible.", ephemeral=True)
        await interaction.response.send_modal(HelpRequestModal(center))

    @discord.ui.button(label="Premium", style=discord.ButtonStyle.success, custom_id="aidebot:ticket-entry:premium")
    async def premium(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        training = interaction.client.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_modal(TrainingRequestModal(training, "vip"))

    @discord.ui.button(label="Lire les guides d’abord", style=discord.ButtonStyle.secondary, custom_id="aidebot:ticket-entry:guides")
    async def guides(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=guide_index_embed(), view=GuideIndexView(), ephemeral=True)


class VideosPanelView(VideoView):
    def __init__(self) -> None:
        super().__init__()
        self.timeout = None
