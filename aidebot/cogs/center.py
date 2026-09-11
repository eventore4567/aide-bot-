from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.experience_content import (
    BANNER_URL,
    FREE_DESCRIPTION,
    GUIDES,
    PREMIUM_DESCRIPTION,
)
from aidebot.video_catalog import VIDEO_LIBRARY
from aidebot.cogs.training import TrainingRequestModal
from aidebot.premium_access import has_premium, missing_premium_message


COLOR = 0x5865F2
SUCCESS = 0x57F287
PREMIUM = 0x9B59B6


def center_embed(vip_price: int) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Centre d’aide & formations",
        description=(
            "**Bienvenue sur Aide Bot.** Ici, tu n’as pas besoin de connaître 30 commandes pour commencer. "
            "Choisis ce que tu veux faire avec les boutons ci-dessous et le bot te guide étape par étape.\n\n"
            "Aide Bot est pensé comme un vrai service : explications complètes, exemples, vidéos, guides, "
            "tickets suivis et accompagnement humain quand tu en as besoin."
        ),
        color=COLOR,
    )
    e.add_field(
        name="GRATUIT — apprendre et résoudre un problème",
        value=(
            "Guides complets sur Discord, serveurs, permissions, bots et tickets. Vidéos complémentaires, exemples "
            "concrets, erreurs fréquentes, quiz et entraide communautaire. **Tu peux déjà apprendre sérieusement sans payer.**"
        ),
        inline=False,
    )
    e.add_field(
        name="PREMIUM — espace réservé aux abonnés",
        value=(
            f"L’abonnement est actuellement configuré à **{vip_price} Robux**. Il s’achète uniquement depuis `🛒・shop` ou `/buy`. "
            "Après validation du paiement, le rôle **💎・VIP** est attribué et débloque les parcours Premium, audits et accompagnements personnalisés."
        ),
        inline=False,
    )
    e.add_field(
        name="SUPPORT — un vrai ticket, pas un salon vide",
        value=(
            "Explique ton problème dans un formulaire. Le ticket affiche ton objectif, ton niveau et ton contexte. "
            "Un membre autorisé peut le prendre en charge ; une seule personne peut être assignée à la fois. "
            "Tu gardes ensuite un suivi clair jusqu’à la résolution et l’avis final."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Choisis une action ci-dessous • Aucun secret ne doit être envoyé en ticket")
    return e


def guide_index_embed() -> discord.Embed:
    lines = []
    for key, data in GUIDES.items():
        lines.append(f"**{data['title']}** (`{key}`)\n{data['subtitle']}")
    e = discord.Embed(
        title="Guides gratuits — choisis un sujet",
        description=FREE_DESCRIPTION + "\n\n" + "\n\n".join(lines),
        color=SUCCESS,
    )
    e.set_image(url=BANNER_URL)
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
        e.add_field(
            name="Vidéo complémentaire",
            value=f"**{video['title']}**\n{video['note']}",
            inline=False,
        )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Lis, pratique, puis ouvre un ticket seulement si tu restes bloqué")
    return e


def premium_embed(vip_price: int) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot Premium — espace abonné",
        description=PREMIUM_DESCRIPTION,
        color=PREMIUM,
    )
    e.add_field(
        name="Ce que ton abonnement débloque",
        value=(
            "• Diagnostic de ton besoin et de ton niveau\n"
            "• Plan de travail adapté à ton objectif\n"
            "• Ticket privé avec un Formateur assigné\n"
            "• Rendez-vous / suivi selon la formule\n"
            "• Audits serveur, bot ou sécurité\n"
            "• Parcours Premium et extensions avancées\n"
            "• Exercices, corrections et vérification finale\n"
            "• Ressources de fin pour pouvoir refaire seul"
        ),
        inline=False,
    )
    e.add_field(
        name="Comment obtenir l’accès",
        value=(
            f"L’abonnement principal est configuré à **{vip_price} Robux**. L’achat se fait **uniquement** dans `🛒・shop` ou avec `/buy`. "
            "Un ticket d’activation est créé ; après validation du paiement par la Direction, le rôle **💎・VIP** est ajouté automatiquement."
        ),
        inline=False,
    )
    e.add_field(
        name="Important",
        value=(
            "Le bouton Premium n’est pas un bouton d’achat. Il sert à utiliser un abonnement déjà actif. "
            "Sans rôle VIP, le bot affiche **Abonnement Premium manquant** et te renvoie vers la boutique."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    return e


def videos_embed() -> discord.Embed:
    lines = []
    for video in VIDEO_LIBRARY.values():
        lines.append(f"**{video['title']}**\n{video['note']}")
    description = (
        "La bibliothèque contient maintenant plusieurs supports : serveur, permissions, bots, slash commands, webhooks/embeds, "
        "Railway, tickets, sécurité/anti-raid et Git/GitHub. Les vidéos servent à voir les manipulations ; les guides Aide Bot expliquent le pourquoi.\n\n"
        + "\n\n".join(lines)
    )
    e = discord.Embed(
        title="Bibliothèque vidéo — supports visuels",
        description=description[:4000],
        color=0xE67E22,
    )
    e.set_image(url=BANNER_URL)
    return e


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
        placeholder="Commandes, réglages, message d’erreur, étapes déjà testées...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=700,
    )
    availability = discord.ui.TextInput(
        label="Tes disponibilités",
        placeholder="Ex: maintenant / ce soir 18h-21h",
        max_length=120,
    )

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
            invite_used=False,
        )


class GuideSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(label=data["title"][:100], value=key, description=data["subtitle"][:100])
            for key, data in GUIDES.items()
        ]
        super().__init__(
            placeholder="Choisis le guide que tu veux lire",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:center:guide_select",
        )

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
        cog = interaction.client.get_cog("CenterCog")
        if cog is None:
            return await interaction.response.send_message("Centre d’aide indisponible.", ephemeral=True)
        await interaction.response.send_modal(HelpRequestModal(cog))


class VideoView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=900)
        for video in VIDEO_LIBRARY.values():
            self.add_item(discord.ui.Button(label=video["title"][:80], style=discord.ButtonStyle.link, url=video["url"]))


class PremiumView(discord.ui.View):
    def __init__(self, cog: "CenterCog") -> None:
        super().__init__(timeout=900)
        self.cog = cog

    @discord.ui.button(label="Ouvrir mon accompagnement Premium", style=discord.ButtonStyle.success)
    async def request(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            return await interaction.response.send_message(missing_premium_message(), ephemeral=True)
        training = self.cog.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_modal(TrainingRequestModal(training, "vip"))


class CenterView(discord.ui.View):
    def __init__(self, cog: "CenterCog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Commencer gratuitement", style=discord.ButtonStyle.success, custom_id="aidebot:center:free")
    async def free(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=guide_index_embed(), view=GuideIndexView(), ephemeral=True)

    @discord.ui.button(label="Ouvrir un ticket d’aide", style=discord.ButtonStyle.primary, custom_id="aidebot:center:help")
    async def help(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(HelpRequestModal(self.cog))

    @discord.ui.button(label="Premium", style=discord.ButtonStyle.secondary, custom_id="aidebot:center:premium")
    async def premium(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            return await interaction.response.send_message(missing_premium_message(), ephemeral=True)
        await interaction.response.send_message(
            embed=premium_embed(self.cog.bot.settings.vip_price_robux),
            view=PremiumView(self.cog),
            ephemeral=True,
        )

    @discord.ui.button(label="Vidéos", style=discord.ButtonStyle.secondary, custom_id="aidebot:center:videos")
    async def videos(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=videos_embed(), view=VideoView(), ephemeral=True)


class CenterCog(commands.Cog, name="CenterCog"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(CenterView(self))

    async def post_center(self, channel: discord.TextChannel) -> None:
        await channel.send(embed=center_embed(self.bot.settings.vip_price_robux), view=CenterView(self))

    @app_commands.command(name="centre", description="Ouvrir le centre interactif Aide Bot")
    async def centre(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            embed=center_embed(self.bot.settings.vip_price_robux),
            view=CenterView(self),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CenterCog(bot))
