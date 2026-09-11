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
from aidebot.cogs.training import TrainingRequestModal
from aidebot.experience_content import BANNER_URL


WELCOME_TITLE = "Bienvenue — Aide Bot"
SHOP_TITLE = "Aide Bot — Boutique & accompagnement"
TICKET_TITLE = "Aide Bot — Ouvrir une demande"
VIDEOS_TITLE = "Aide Bot — Vidéos & guides"


def welcome_embed() -> discord.Embed:
    e = discord.Embed(
        title=WELCOME_TITLE,
        description=(
            "Bienvenue sur **Aide Bot**. Ce salon sert uniquement à t’accueillir et à t’expliquer où aller. "
            "Il ne contient pas le catalogue des formations : chaque espace du serveur a maintenant une fonction différente.\n\n"
            "**Tu veux apprendre ?** Va dans `🎓・centre-aide` pour les guides gratuits, les vidéos et les explications.\n"
            "**Tu veux une formation ?** Va dans `🎓・formations` pour choisir un parcours et ouvrir une demande.\n"
            "**Tu as un problème précis ?** Va dans `🎫・ouvrir-ticket` et décris-le dans le formulaire.\n"
            "**Tu veux un accompagnement Premium ?** Va dans `🛒・shop` ou utilise `/buy`.\n\n"
            "Tu n’as pas besoin de mémoriser des dizaines de commandes : les boutons et menus du serveur sont faits pour tout faire."
        ),
        color=0x5865F2,
    )
    e.add_field(
        name="Avant de commencer",
        value=(
            "Lis le règlement, ne partage jamais de token, mot de passe ou code de récupération, et donne un maximum de contexte "
            "quand tu ouvres un ticket."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Bienvenue ≠ Formations • Utilise les panneaux du serveur")
    return e


def shop_embed(price_robux: int) -> discord.Embed:
    e = discord.Embed(
        title=SHOP_TITLE,
        description=(
            "La partie gratuite d’Aide Bot reste complète pour apprendre les bases. La boutique sert uniquement à acheter "
            "du **temps humain, du suivi et un accompagnement personnalisé**.\n\n"
            f"**Formule Premium principale : {price_robux} Robux**\n"
            "Diagnostic de ton besoin, plan personnalisé, ticket privé, Formateur assigné, rendez-vous, audit, corrections, "
            "exercices et vérification finale."
        ),
        color=0x9B59B6,
    )
    e.add_field(
        name="Comment l’achat fonctionne",
        value=(
            "1. Clique sur **Acheter Premium**.\n"
            "2. Remplis ton objectif et tes disponibilités.\n"
            "3. Un ticket privé est créé en attente de paiement.\n"
            "4. La Direction vérifie le paiement manuellement.\n"
            "5. Après validation, un Formateur peut prendre la demande."
        ),
        inline=True,
    )
    e.add_field(
        name="Sécurité",
        value=(
            "Le bot ne doit jamais te demander ton mot de passe, ton token Discord ou tes codes de récupération. "
            "Un paiement non confirmé ne débloque jamais automatiquement la prestation."
        ),
        inline=True,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Le gratuit reste utile • Premium = accompagnement personnalisé")
    return e


def ticket_embed() -> discord.Embed:
    e = discord.Embed(
        title=TICKET_TITLE,
        description=(
            "Ouvre une demande uniquement quand tu as un problème réel ou quand un guide ne suffit pas. Le formulaire te demande "
            "le problème, ce que tu as déjà essayé et tes disponibilités afin que le staff puisse comprendre rapidement.\n\n"
            "Une fois le ticket créé, un Helper, Formateur, responsable, administrateur ou propriétaire autorisé peut le prendre. "
            "Une seule personne est assignée à la fois pour éviter les réponses contradictoires."
        ),
        color=0x3498DB,
    )
    e.add_field(
        name="Dans ton ticket, envoie",
        value="Le message d’erreur exact, les étapes déjà testées, une capture si utile et le résultat que tu veux obtenir.",
        inline=True,
    )
    e.add_field(
        name="N’envoie jamais",
        value="Token de bot, mot de passe, cookie, code 2FA, code de récupération ou information bancaire.",
        inline=True,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Ticket clair = aide plus rapide")
    return e


def videos_panel_embed() -> discord.Embed:
    e = videos_embed()
    e.title = VIDEOS_TITLE
    e.description = (
        "Ici tu trouves uniquement les **supports visuels**. Les vidéos montrent les écrans et les manipulations ; les guides du "
        "centre d’aide restent la référence pour comprendre pourquoi on fait chaque étape et éviter les erreurs de sécurité.\n\n"
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
        await interaction.response.send_message(
            embed=center_embed(self.bot.settings.vip_price_robux),
            view=CenterView(cog),
            ephemeral=True,
        )

    @discord.ui.button(label="Ouvrir un ticket", style=discord.ButtonStyle.success, custom_id="aidebot:welcome:ticket")
    async def ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        cog = interaction.client.get_cog("CenterCog")
        if cog is None:
            return await interaction.response.send_message("Centre d’aide indisponible.", ephemeral=True)
        await interaction.response.send_modal(HelpRequestModal(cog))

    @discord.ui.button(label="Boutique", style=discord.ButtonStyle.secondary, custom_id="aidebot:welcome:shop")
    async def shop(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            embed=shop_embed(self.bot.settings.vip_price_robux),
            view=ShopView(self.bot),
            ephemeral=True,
        )


class ShopView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Acheter Premium", style=discord.ButtonStyle.success, custom_id="aidebot:shop:premium")
    async def premium(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        training = interaction.client.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_modal(TrainingRequestModal(training, "vip"))

    @discord.ui.button(label="Voir les détails", style=discord.ButtonStyle.primary, custom_id="aidebot:shop:details")
    async def details(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        center = interaction.client.get_cog("CenterCog")
        if center is None:
            return await interaction.response.send_message("Centre d’aide indisponible.", ephemeral=True)
        await interaction.response.send_message(
            embed=premium_embed(self.bot.settings.vip_price_robux),
            view=PremiumView(center),
            ephemeral=True,
        )

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
