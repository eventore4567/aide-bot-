from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.cogs.experience_v43 import VideoLibraryView, video_home_embed
from aidebot.cogs.experience_v44 import SmartSupportView, premium_compare_embed
from aidebot.cogs.help_center_v46 import HelpCenterV46View, help_center_embed
from aidebot.cogs.training import TrainingRequestModal
from aidebot.experience_content import BANNER_URL, FREE_DESCRIPTION, GUIDES
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed
from aidebot.video_catalog import VIDEO_LIBRARY

COLOR = 0x5865F2
SUCCESS = 0x57F287
PREMIUM = 0x9B59B6


def center_embed(vip_price: int) -> discord.Embed:
    e = help_center_embed(vip_price)
    e.title = "Aide Bot — Centre d’aide • Tableau de bord"
    return e


def guide_index_embed() -> discord.Embed:
    lines = [f"**{data['title']}**\n{data['subtitle']}" for data in GUIDES.values()]
    e = discord.Embed(
        title="Guides gratuits — apprendre vraiment",
        description=(
            FREE_DESCRIPTION
            + "\n\nChaque guide contient une explication complète, un exemple réel, les erreurs fréquentes et une vidéo complémentaire quand elle est disponible.\n\n"
            + "\n\n".join(lines)
        )[:4000],
        color=SUCCESS,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V46 • Guide → exemple → erreurs → vidéo → pratique")
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
    e.set_footer(text="Aide Bot V46 • Comprends d’abord, applique ensuite")
    return e


def premium_embed(vip_price: int) -> discord.Embed:
    return premium_compare_embed(vip_price)


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
        objective = str(self.problem).strip()
        tried = str(self.tried).strip()
        if tried:
            objective += f"\n\n**Déjà essayé :** {tried}"
        await training.create_request_channel(
            interaction,
            "community_help",
            level="Aide communautaire",
            objective=objective,
            availability=str(self.availability).strip(),
            budget="Aide gratuite",
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
        self.key = key
        data = GUIDES[key]
        video = VIDEO_LIBRARY.get(data.get("video_key", ""))
        if video:
            self.add_item(discord.ui.Button(label="Voir la vidéo", style=discord.ButtonStyle.link, url=video["url"]))

    @discord.ui.button(label="Tous les guides", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=guide_index_embed(), view=GuideIndexView())

    @discord.ui.button(label="J’ai encore besoin d’aide", style=discord.ButtonStyle.primary)
    async def help(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        bot = interaction.client
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Support intelligent",
                description="Choisis ton type de problème. Aide Bot te donne d’abord une checklist de diagnostic, puis un formulaire adapté uniquement si nécessaire.",
                color=COLOR,
            ),
            view=SmartSupportView(bot),
            ephemeral=True,
        )


class VideoView(VideoLibraryView):
    def __init__(self) -> None:
        super().__init__()


class PremiumView(discord.ui.View):
    def __init__(self, cog: "CenterCog") -> None:
        super().__init__(timeout=900)
        self.cog = cog

    @discord.ui.button(label="Ouvrir mon accompagnement", style=discord.ButtonStyle.success)
    async def request(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        training = self.cog.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_modal(TrainingRequestModal(training, "vip"))


class CenterView(HelpCenterV46View):
    def __init__(self, cog: "CenterCog") -> None:
        super().__init__(cog.bot)
        self.cog = cog

        # Compatibilité avec le dashboard V44 : on garde exactement les cinq
        # raccourcis principaux. Les choix supplémentaires vivent dans le menu
        # de 14 sujets, ce qui évite un mur de boutons.
        for item in list(self.children):
            if not isinstance(item, discord.ui.Button):
                continue
            if item.label in {"Candidatures", "Statut Premium"}:
                self.remove_item(item)
            elif item.label == "Support / Tickets":
                item.label = "Support intelligent"


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
