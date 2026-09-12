from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs.center import (
    CenterView,
    GuideIndexView,
    PremiumView,
    center_embed,
    guide_index_embed,
    premium_embed,
)
from aidebot.cogs.experience_v43 import (
    TicketPortalView,
    VideoLibraryView,
    member_space_embed,
    video_home_embed,
)
from aidebot.cogs.training import PremiumPurchaseModal, TrainingPanel, TrainingSelect
from aidebot.cogs.training_experience_v42 import V42TrainingSelect
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed


# Compatibilité avec les anciens messages persistants déjà publiés.
# Ils gardent leur custom_id historique, mais ouvrent maintenant l’expérience
# détaillée V42/V43 au lieu du formulaire générique d’origine.
TrainingSelect.callback = V42TrainingSelect.callback


def _modern_training_panel_init(self: TrainingPanel, cog: commands.Cog) -> None:
    discord.ui.View.__init__(self, timeout=None)
    self.add_item(V42TrainingSelect(cog))


TrainingPanel.__init__ = _modern_training_panel_init


WELCOME_TITLE = "Bienvenue — Aide Bot"
SHOP_TITLE = "Aide Bot — Boutique Premium"
TICKET_TITLE = "Aide Bot — Centre de support"
VIDEOS_TITLE = "Aide Bot — Bibliothèque vidéo"


def welcome_embed() -> discord.Embed:
    e = discord.Embed(
        title=WELCOME_TITLE,
        description=(
            "Bienvenue sur **Aide Bot**. Ce salon **sert uniquement à t’accueillir** et à t’orienter. "
            "Tu n’as pas besoin de retenir une liste de commandes : le serveur fonctionne comme un vrai produit, avec des panneaux, menus et formulaires.\n\n"
            "**Apprendre gratuitement** → `🎓・centre-aide`\n"
            "**Suivre une formation structurée** → `🎓・formations`\n"
            "**Regarder des tutoriels classés** → `🎥・videos-guides`\n"
            "**Résoudre un problème précis** → `🎫・ouvrir-ticket`\n"
            "**Activer Premium** → `🛒・shop` ou `/buy`"
        ),
        color=0x5865F2,
    )
    e.add_field(
        name="Ton parcours est simple",
        value=(
            "**1.** Choisis ton besoin.  **2.** Lis la fiche ou remplis le formulaire adapté.  **3.** Le bot crée le bon espace.  "
            "**4.** Le staff suit la demande jusqu’au résultat."
        ),
        inline=False,
    )
    e.add_field(
        name="Sécurité",
        value="Ne partage jamais de token, mot de passe, cookie, code 2FA ou code de récupération. Aide Bot n’en a jamais besoin pour t’aider.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V43 • Un espace = une fonction • Navigation sans commandes inutiles")
    return e


def shop_embed(price_robux: int) -> discord.Embed:
    e = discord.Embed(
        title=SHOP_TITLE,
        description=(
            f"**Aide Bot Premium — {price_robux} Robux**\n"
            "Premium ne remplace pas le gratuit : il ajoute un **accompagnement humain personnalisé**, les parcours avancés et les audits.\n\n"
            "L’achat se fait **uniquement dans cette boutique ou avec `/buy`**. Tous les autres boutons Premium servent seulement à utiliser un abonnement déjà actif."
        ),
        color=0x9B59B6,
    )
    e.add_field(
        name="Inclus avec Premium",
        value=(
            "**Accompagnement sur mesure**\nDiagnostic du projet, plan d’action, suivi et vérification finale.\n\n"
            "**Parcours avancés**\nServeur professionnel, bot avancé, sécurité et audit."
        ),
        inline=True,
    )
    e.add_field(
        name="Activation automatique",
        value=(
            "**1.** Acheter\n**2.** Ticket privé\n**3.** Validation Direction\n"
            "**4.** Rôle `💎・VIP` automatique\n**5.** Accès Premium débloqué"
        ),
        inline=True,
    )
    e.add_field(
        name="Avant de payer",
        value=(
            "Le prix et la formule sont affichés avant l’ouverture du ticket. Aucun mot de passe, token, cookie, code 2FA ou code de récupération ne doit être envoyé."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V43 • Boutique = seul point d’achat • VIP attribué après validation")
    return e


def ticket_embed() -> discord.Embed:
    e = discord.Embed(
        title=TICKET_TITLE,
        description=(
            "Ici tu ne remplis plus un formulaire générique pour tout. **Choisis d’abord le type de problème** : Discord, serveur/permissions, bot/code, sécurité ou autre. "
            "Aide Bot adapte ensuite les questions au sujet et crée un ticket privé déjà compréhensible par le staff."
        ),
        color=0x3498DB,
    )
    e.add_field(
        name="Comment ça marche ?",
        value=(
            "**1.** Choisis une catégorie dans le menu.\n"
            "**2.** Remplis le formulaire adapté.\n"
            "**3.** Un ticket privé est créé avec ton contexte et ton objectif.\n"
            "**4.** Un seul membre du staff le prend en charge.\n"
            "**5.** La progression est suivie jusqu’à la résolution."
        ),
        inline=True,
    )
    e.add_field(
        name="Premium",
        value=(
            "Le bouton Premium de ce panneau est réservé aux membres avec `💎・VIP`. Pour acheter l’abonnement, va dans `🛒・shop` ou utilise `/buy`."
        ),
        inline=True,
    )
    e.add_field(
        name="À préparer",
        value="Résultat attendu • erreur exacte • contexte • ce que tu as essayé • disponibilités • capture utile si nécessaire.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V43 • Catégorie → formulaire adapté → ticket clair → suivi")
    return e


def videos_panel_embed() -> discord.Embed:
    e = video_home_embed()
    e.title = VIDEOS_TITLE
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

    @discord.ui.button(label="Mon espace", style=discord.ButtonStyle.secondary, custom_id="aidebot:v43:welcome:space")
    async def space(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=await member_space_embed(self.bot, interaction.user), ephemeral=True)

    @discord.ui.button(label="Support", style=discord.ButtonStyle.success, custom_id="aidebot:v43:welcome:support")
    async def support(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=ticket_embed(), view=TicketEntryView(self.bot), ephemeral=True)

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

    @discord.ui.button(label="Ce qui est inclus", style=discord.ButtonStyle.secondary, custom_id="aidebot:shop:details")
    async def details(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=premium_embed(self.bot.settings.vip_price_robux), ephemeral=True)

    @discord.ui.button(label="Continuer gratuitement", style=discord.ButtonStyle.secondary, custom_id="aidebot:shop:free")
    async def free(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=guide_index_embed(), view=GuideIndexView(), ephemeral=True)


class TicketEntryView(TicketPortalView):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)


class VideosPanelView(VideoLibraryView):
    def __init__(self) -> None:
        super().__init__()
