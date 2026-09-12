from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.cogs.experience_v43 import (
    TicketPortalView,
    VideoLibraryView,
    member_space_embed,
    video_home_embed,
)
from aidebot.cogs.training import TrainingRequestModal
from aidebot.cogs.training_experience_v42 import V42TrainingPanel, training_catalog_embed
from aidebot.experience_content import BANNER_URL, FREE_DESCRIPTION, GUIDES, PREMIUM_DESCRIPTION
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed
from aidebot.video_catalog import VIDEO_LIBRARY


COLOR = 0x5865F2
SUCCESS = 0x57F287
PREMIUM = 0x9B59B6


def center_embed(vip_price: int) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Ton centre de contrôle",
        description=(
            "**Un seul endroit pour comprendre quoi faire ensuite.** Tu peux apprendre gratuitement, choisir un vrai parcours, "
            "ouvrir un support adapté à ton problème, consulter les vidéos par catégorie ou accéder à ton espace Premium.\n\n"
            "Aide Bot ne te renvoie plus d’une commande à une autre : chaque bouton ouvre directement l’expérience correspondante."
        ),
        color=COLOR,
    )
    e.add_field(
        name="Apprendre",
        value="Guides détaillés, exemples, erreurs fréquentes et vidéos complémentaires.",
        inline=True,
    )
    e.add_field(
        name="Se former",
        value="Fiche complète du parcours avant inscription, programme, durée, niveau et formulaire spécifique.",
        inline=True,
    )
    e.add_field(
        name="Être aidé",
        value="Support trié par type : Discord, serveur/permissions, bot/code, sécurité ou autre.",
        inline=True,
    )
    e.add_field(
        name="Premium",
        value=(
            f"Abonnement configuré à **{vip_price} Robux**. Achat uniquement via `🛒・shop` ou `/buy`; les autres boutons Premium servent à utiliser un accès déjà actif."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V43 • Choisis ton objectif, pas une commande")
    return e


def guide_index_embed() -> discord.Embed:
    lines = [f"**{data['title']}**\n{data['subtitle']}" for data in GUIDES.values()]
    e = discord.Embed(
        title="Guides gratuits — apprendre vraiment",
        description=(
            FREE_DESCRIPTION
            + "\n\nChoisis un sujet dans le menu. Chaque guide contient une explication, un exemple concret, des erreurs à éviter et une ressource vidéo quand elle existe.\n\n"
            + "\n\n".join(lines)
        )[:4000],
        color=SUCCESS,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Guide → exemple → erreurs → vidéo → pratique")
    return e


def guide_embed(key: str) -> discord.Embed:
    data = GUIDES[key]
    e = discord.Embed(title=data["title"], description=data["subtitle"], color=0x3498DB)
    for title, text in data["sections"]:
        e.add_field(name=title, value=text, inline=False)
    e.add_field(name="Exemple concret", value=data["example"], inline=False)
    e.add_field(name="Erreurs fréquentes à éviter", value=data["mistakes"], inline=False)
    video = VIDEO_LIBRARY.get(data.get("video_key", ""))
    if video:
        e.add_field(name="Vidéo complémentaire", value=f"**{video['title']}**\n{video['note']}", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Comprends d’abord, applique ensuite")
    return e


def premium_embed(vip_price: int) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot Premium — espace abonné",
        description=(
            PREMIUM_DESCRIPTION
            + "\n\nPremium sert à obtenir **du temps humain, un diagnostic et un suivi sur ton projet réel**. Les bases restent accessibles gratuitement."
        ),
        color=PREMIUM,
    )
    e.add_field(
        name="Ce que ton abonnement débloque",
        value=(
            "Diagnostic personnalisé • plan de travail • ticket privé • Formateur assigné • parcours avancés • audits serveur/bot/sécurité • "
            "exercices • corrections • vérification finale • ressources de fin."
        ),
        inline=False,
    )
    e.add_field(
        name="Activation",
        value=(
            f"Prix configuré : **{vip_price} Robux**. Achat uniquement dans `🛒・shop` ou avec `/buy`. Après validation par la Direction, le rôle **💎・VIP** est attribué automatiquement."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot Premium • Acheter dans la boutique, utiliser partout ailleurs")
    return e


def videos_embed() -> discord.Embed:
    return video_home_embed()


class HelpRequestModal(discord.ui.Modal, title="Ouvrir une demande d’aide"):
    problem = discord.ui.TextInput(
        label="Quel est ton problème ?",
        placeholder="Explique précisément ce qui ne marche pas...",
        style=discord.TextStyle.paragraph,
        min_length=10,
        max_length=1000,
    )
    tried = discord.ui.TextInput(
        label="Qu’as-tu déjà essayé ?",
        placeholder="Réglages, messages d’erreur, étapes testées...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=700,
    )
    availability = discord.ui.TextInput(label="Tes disponibilités", placeholder="Ex: ce soir 18h-21h", max_length=120)

    def __init__(self, cog: "CenterCog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        training = self.cog.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Le module de tickets est indisponible.", ephemeral=True)
        objective = str(self.problem)
        tried = str(self.tried).strip()
        if tried:
            objective += f"\n\nDéjà essayé : {tried}"
        await training.create_request_channel(
            interaction,
            "community_help",
            level="Aide communautaire",
            objective=objective,
            availability=str(self.availability),
            budget="Gratuit",
            status="open",
            payment_status="not_required",
            requires_invite=False,
        )


class GuideSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [discord.SelectOption(label=data["title"][:100], value=key, description=data["subtitle"][:100]) for key, data in GUIDES.items()]
        super().__init__(placeholder="Choisis le guide que tu veux lire", min_values=1, max_values=1, options=options, custom_id="aidebot:center:guide_select")

    async def callback(self, interaction: discord.Interaction) -> None:
        key = self.values[0]
        await interaction.response.edit_message(embed=guide_embed(key), view=GuideDetailView(key))


class GuideIndexView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=900)
        self.add_item(GuideSelect())


class GuideDetailView(discord.ui.View):
    def __init__(self, key: str) -> None:
        super().__init__(timeout=900)
        data = GUIDES[key]
        video = VIDEO_LIBRARY.get(data.get("video_key", ""))
        if video:
            self.add_item(discord.ui.Button(label="Voir la vidéo", style=discord.ButtonStyle.link, url=video["url"]))

    @discord.ui.button(label="Tous les guides", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=guide_index_embed(), view=GuideIndexView())

    @discord.ui.button(label="J’ai encore besoin d’aide", style=discord.ButtonStyle.primary)
    async def help(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Choisis d’abord la catégorie qui correspond vraiment à ton problème.",
            view=TicketPortalView(interaction.client),
            ephemeral=True,
        )


class VideoView(VideoLibraryView):
    """Alias de compatibilité : les anciens appels ouvrent maintenant la bibliothèque V43."""

    def __init__(self) -> None:
        super().__init__()


class PremiumView(discord.ui.View):
    def __init__(self, cog: "CenterCog") -> None:
        super().__init__(timeout=900)
        self.cog = cog

    @discord.ui.button(label="Ouvrir mon accompagnement", style=discord.ButtonStyle.success)
    async def request(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            return await interaction.response.send_message(embed=missing_premium_embed(), ephemeral=True)
        training = self.cog.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_modal(TrainingRequestModal(training, "vip"))


class CenterView(discord.ui.View):
    def __init__(self, cog: "CenterCog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Guides gratuits", style=discord.ButtonStyle.success, custom_id="aidebot:center:free")
    async def free(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=guide_index_embed(), view=GuideIndexView(), ephemeral=True)

    @discord.ui.button(label="Formations", style=discord.ButtonStyle.primary, custom_id="aidebot:v43:center:training")
    async def training(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        training = interaction.client.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_message(embed=training_catalog_embed(), view=V42TrainingPanel(training), ephemeral=True)

    @discord.ui.button(label="Support", style=discord.ButtonStyle.primary, custom_id="aidebot:center:help")
    async def help(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Choisis le type de problème pour ouvrir le bon formulaire.",
            view=TicketPortalView(self.cog.bot),
            ephemeral=True,
        )

    @discord.ui.button(label="Vidéos", style=discord.ButtonStyle.secondary, custom_id="aidebot:center:videos")
    async def videos(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=video_home_embed(), view=VideoLibraryView(), ephemeral=True)

    @discord.ui.button(label="Mon espace", style=discord.ButtonStyle.secondary, custom_id="aidebot:v43:center:space")
    async def space(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=await member_space_embed(self.cog.bot, interaction.user), ephemeral=True)

    @discord.ui.button(label="Premium", style=discord.ButtonStyle.secondary, custom_id="aidebot:center:premium", row=1)
    async def premium(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        await interaction.response.send_message(embed=premium_embed(self.cog.bot.settings.vip_price_robux), view=PremiumView(self.cog), ephemeral=True)


class CenterCog(commands.Cog, name="CenterCog"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(CenterView(self))

    async def post_center(self, channel: discord.TextChannel) -> None:
        await channel.send(embed=center_embed(self.bot.settings.vip_price_robux), view=CenterView(self))

    @app_commands.command(name="centre", description="Ouvrir le centre interactif Aide Bot")
    async def centre(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=center_embed(self.bot.settings.vip_price_robux), view=CenterView(self), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CenterCog(bot))
