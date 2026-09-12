from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs.center import CenterView, GuideIndexView, center_embed, guide_index_embed, premium_embed
from aidebot.cogs.experience_v43 import VideoLibraryView, member_space_embed, video_home_embed
from aidebot.cogs.experience_v44 import SmartSupportView
from aidebot.cogs.training import PremiumPurchaseModal, TrainingPanel, TrainingSelect
from aidebot.cogs.training_experience_v42 import V42TrainingSelect
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed

# Compatibilité des anciens panneaux persistants : ils gardent leur custom_id,
# mais utilisent l'expérience de formation détaillée moderne.
TrainingSelect.callback = V42TrainingSelect.callback


def _modern_training_panel_init(self: TrainingPanel, cog: commands.Cog) -> None:
    discord.ui.View.__init__(self, timeout=None)
    self.add_item(V42TrainingSelect(cog))


TrainingPanel.__init__ = _modern_training_panel_init

WELCOME_TITLE = "Bienvenue — Aide Bot"
SHOP_TITLE = "Aide Bot — Boutique Premium"
TICKET_TITLE = "Aide Bot — Support intelligent"
VIDEOS_TITLE = "Aide Bot — Bibliothèque vidéo"


def welcome_embed() -> discord.Embed:
    e = discord.Embed(
        title=WELCOME_TITLE,
        description=(
            "Bienvenue sur **Aide Bot**. Ce salon **sert uniquement à t’accueillir** et à t’orienter. "
            "Le serveur fonctionne comme un vrai service : tu cliques sur ton besoin et le bot t’emmène directement au bon parcours.\n\n"
            "**Centre d’aide** → `🎓・centre-aide` pour guides, support, vidéos, espace personnel et Premium.\n"
            "**Formations** → `🎓・formations` pour les parcours détaillés avant inscription.\n"
            "**Support** → `🎫・ouvrir-ticket` pour le diagnostic rapide avant création d’un ticket.\n"
            "**Boutique** → `🛒・shop`, seul endroit où acheter Premium."
        ),
        color=0x5865F2,
    )
    e.add_field(name="Le parcours idéal", value="**Comprendre → diagnostiquer → agir → suivre le résultat.** Tu n’as pas besoin de retenir des dizaines de commandes.", inline=False)
    e.add_field(name="Sécurité", value="Ne partage jamais token, mot de passe, cookie, code 2FA ou code de récupération. Aucun Helper ou Formateur n’en a besoin.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V44 • Un besoin → un parcours clair")
    return e


def shop_embed(price_robux: int) -> discord.Embed:
    e = premium_embed(price_robux)
    e.title = SHOP_TITLE
    e.description = (
        f"**Premium — {price_robux} Robux**\n"
        "La boutique est le **seul point d’achat**. Les autres boutons Premium du serveur servent uniquement à utiliser un abonnement déjà actif.\n\n"
        + (e.description or "")
    )[:4000]
    e.set_footer(text="Aide Bot V44 • Achat uniquement ici ou avec /buy • Activation après validation")
    return e


def ticket_embed() -> discord.Embed:
    e = discord.Embed(
        title=TICKET_TITLE,
        description=(
            "Ici, Aide Bot ne crée plus immédiatement un salon vide. **Choisis d’abord le type de problème** : Discord, serveur/permissions, bot/code, sécurité ou autre. "
            "Le bot te montre ensuite une checklist de diagnostic. Si ça ne suffit pas, tu ouvres le formulaire adapté et le ticket contient déjà le bon contexte."
        ),
        color=0x3498DB,
    )
    e.add_field(name="Étapes", value="**1.** Choisis une catégorie.\n**2.** Vérifie la checklist rapide.\n**3.** Regarde la vidéo recommandée si utile.\n**4.** Si le problème continue, ouvre le formulaire.\n**5.** Un seul membre du staff prend le ticket et le suit jusqu’au résultat.", inline=False)
    e.add_field(name="Premium", value="Le bouton Premium est réservé aux membres `💎・VIP`. Pour acheter l’abonnement, utilise `🛒・shop` ou `/buy`.", inline=True)
    e.add_field(name="Jamais dans un ticket", value="Token • mot de passe • cookie • code 2FA • code de récupération • information bancaire.", inline=True)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V44 • Diagnostic → formulaire adapté → ticket clair → suivi")
    return e


def videos_panel_embed() -> discord.Embed:
    e = video_home_embed()
    e.title = VIDEOS_TITLE
    e.description = ("Les vidéos sont rangées par **catégories** pour éviter un mur de liens. Choisis le sujet, puis ouvre uniquement les ressources utiles.\n\n" + (e.description or ""))[:4000]
    e.set_footer(text="Aide Bot V44 • Catégorie → sélection courte → application pratique")
    return e


class WelcomeView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Ouvrir le centre", style=discord.ButtonStyle.primary, custom_id="aidebot:welcome:center")
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

    @discord.ui.button(label="Comparer Free / Premium", style=discord.ButtonStyle.secondary, custom_id="aidebot:shop:details")
    async def details(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=premium_embed(self.bot.settings.vip_price_robux), ephemeral=True)

    @discord.ui.button(label="Continuer gratuitement", style=discord.ButtonStyle.secondary, custom_id="aidebot:shop:free")
    async def free(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=guide_index_embed(), view=GuideIndexView(), ephemeral=True)


class TicketEntryView(SmartSupportView):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)


class VideosPanelView(VideoLibraryView):
    def __init__(self) -> None:
        super().__init__()
