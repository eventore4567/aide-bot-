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
from aidebot.cogs.training import PremiumPurchaseModal, TrainingRequestModal
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium, missing_premium_message


WELCOME_TITLE = "Bienvenue — Aide Bot"
SHOP_TITLE = "Aide Bot — Boutique & abonnement Premium"
TICKET_TITLE = "Aide Bot — Ouvrir une demande"
VIDEOS_TITLE = "Aide Bot — Vidéos & guides"


def welcome_embed() -> discord.Embed:
    e = discord.Embed(
        title=WELCOME_TITLE,
        description=(
            "Bienvenue sur **Aide Bot**. Ce salon sert uniquement à t’accueillir et à t’expliquer où aller. "
            "Il ne contient pas le catalogue des formations : chaque espace du serveur a une fonction différente.\n\n"
            "**Tu veux apprendre ?** Va dans `🎓・centre-aide` pour les guides gratuits, les vidéos et les explications.\n"
            "**Tu veux une formation ?** Va dans `🎓・formations` pour choisir un parcours et remplir le formulaire adapté au sujet.\n"
            "**Tu as un problème précis ?** Va dans `🎫・ouvrir-ticket` et décris-le dans le formulaire.\n"
            "**Tu veux Premium ?** L’achat se fait uniquement dans `🛒・shop` ou avec `/buy`.\n\n"
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
            "La partie gratuite reste utile. La boutique sert à activer **Aide Bot Premium** et son accompagnement humain.\n\n"
            f"**Abonnement Premium : {price_robux} Robux**\n"
            "Une fois le paiement validé par le staff, le bot ajoute automatiquement le rôle **💎・VIP**. Ce rôle débloque ensuite "
            "les boutons Premium, les parcours avancés, les audits et l’accompagnement personnalisé."
        ),
        color=0x9B59B6,
    )
    e.add_field(
        name="Activation en 4 étapes",
        value=(
            "1. Clique sur **Acheter Premium** dans ce salon ou avec `/buy`.\n"
            "2. Remplis le formulaire d’achat : projet, résultat attendu et disponibilités.\n"
            "3. Le bot crée un ticket privé **en attente de paiement**.\n"
            "4. Après validation par la Direction, le rôle **💎・VIP** est ajouté automatiquement."
        ),
        inline=False,
    )
    e.add_field(
        name="Après l’activation",
        value=(
            "Les boutons Premium ne servent plus à acheter : ils servent à **utiliser ton abonnement**. Si tu cliques dessus sans le rôle VIP, "
            "le bot affiche `Abonnement Premium manquant` et te renvoie vers cette boutique."
        ),
        inline=False,
    )
    e.add_field(
        name="Sécurité",
        value=(
            "Ne donne jamais de mot de passe, token Discord, cookie, code 2FA ou code de récupération. Le staff ne doit vérifier que les éléments "
            "publics nécessaires au paiement."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Achat uniquement via la boutique • Premium débloqué après validation")
    return e


def ticket_embed() -> discord.Embed:
    e = discord.Embed(
        title=TICKET_TITLE,
        description=(
            "Ce salon sert aux **problèmes précis**. Tu remplis un formulaire, puis le bot crée un ticket privé avec un résumé clair : "
            "ta demande, ton niveau, tes disponibilités, l’état du ticket et la prochaine étape.\n\n"
            "Pour acheter Premium, n’utilise pas ce panneau : passe par `🛒・shop` ou `/buy`. Le bouton Premium ici est réservé aux abonnés déjà activés."
        ),
        color=0x3498DB,
    )
    e.add_field(
        name="Aide gratuite",
        value="Explique ton problème, ce que tu as déjà essayé et quand tu es disponible. Un Helper/Formateur pourra ensuite prendre la demande.",
        inline=True,
    )
    e.add_field(
        name="Premium",
        value="Réservé aux membres avec le rôle **💎・VIP**. Sans abonnement actif, le bot te renvoie vers la boutique.",
        inline=True,
    )
    e.add_field(
        name="Ne partage jamais",
        value="Token de bot, mot de passe, cookie, code 2FA, code de récupération ou information bancaire.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Un ticket clair = une prise en charge claire")
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
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            return await interaction.response.send_message(
                "Ton abonnement Premium est déjà actif. Utilise le bouton **Premium** du centre ou choisis directement un parcours Premium dans `🎓・formations`.",
                ephemeral=True,
            )
        training = interaction.client.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_modal(PremiumPurchaseModal(training))

    @discord.ui.button(label="Voir les détails", style=discord.ButtonStyle.primary, custom_id="aidebot:shop:details")
    async def details(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        center = interaction.client.get_cog("CenterCog")
        if center is None:
            return await interaction.response.send_message("Centre d’aide indisponible.", ephemeral=True)
        await interaction.response.send_message(
            embed=premium_embed(self.bot.settings.vip_price_robux),
            view=None,
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
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            return await interaction.response.send_message(missing_premium_message(), ephemeral=True)
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
