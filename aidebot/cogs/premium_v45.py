from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs.experience_v43 import member_space_embed
from aidebot.cogs.setup_server import SetupServerCog
from aidebot.cogs.training import TrainingPanel, TrainingRequestModal
from aidebot.cogs.training_experience_v42 import training_catalog_embed
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed
from aidebot.video_catalog import PREMIUM_VIDEO_LIBRARY


PREMIUM_CATEGORY = "━━ PREMIUM ━━"
PREMIUM_HUB_CHANNEL = "💎・espace-premium"
PREMIUM_VIDEO_CHANNEL = "🎬・videos-premium"

PREMIUM_VIDEO_CATEGORIES = {
    "architecture": {
        "label": "Architecture bot avancée",
        "description": "Concurrence, vues persistantes, rate limits et logs production.",
        "keys": ("p-architecture", "p-async", "p-persistent-ui", "p-rate-limits", "p-logging"),
    },
    "security": {
        "label": "Sécurité avancée",
        "description": "OAuth2, secrets, anti-raid, webhooks et réponse à incident.",
        "keys": ("p-oauth", "p-secrets", "p-antiraid", "p-webhook-security", "p-incident"),
    },
    "infrastructure": {
        "label": "Infrastructure & production",
        "description": "Railway, PostgreSQL, Docker, monitoring et CI/CD.",
        "keys": ("p-railway-volume", "p-postgres", "p-docker", "p-monitoring", "p-cicd"),
    },
    "product": {
        "label": "Produit & expérience membre",
        "description": "UX Discord, tickets, onboarding, accessibilité et communauté.",
        "keys": ("p-discord-ux", "p-ticket-architecture", "p-onboarding", "p-accessibility", "p-community-systems"),
    },
    "quality": {
        "label": "Qualité & fiabilité",
        "description": "Tests async, intégration, concurrence DB, migrations et performance.",
        "keys": ("p-async-pytest", "p-integration", "p-sqlite-concurrency", "p-migrations", "p-profiling"),
    },
}


def _premium_keys(category: str) -> list[str]:
    return [key for key in PREMIUM_VIDEO_CATEGORIES[category]["keys"] if key in PREMIUM_VIDEO_LIBRARY][:5]


def premium_hub_embed() -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Espace Premium",
        description=(
            "Bienvenue dans l’espace réservé aux membres **💎・VIP**. Ici, le but n’est pas de te donner plus de boutons pour rien : "
            "tu accèdes aux ressources avancées, aux vidéos techniques Premium et au suivi humain prioritaire.\n\n"
            "Utilise cet espace quand tu veux passer d’un projet qui fonctionne à un projet **propre, sécurisé, testable et prêt pour la production**."
        ),
        color=0xEB459E,
    )
    e.add_field(
        name="Formations avancées",
        value="Parcours détaillés, prérequis, objectifs, exercices et suivi dans un ticket dédié.",
        inline=True,
    )
    e.add_field(
        name="Vidéos Premium",
        value="**25 sujets avancés** répartis en 5 catégories : architecture, sécurité, production, produit et qualité.",
        inline=True,
    )
    e.add_field(
        name="Support Premium",
        value="Ouvre un accompagnement personnalisé avec contexte, objectif, disponibilité et suivi jusqu’au résultat.",
        inline=False,
    )
    e.add_field(
        name="Accès",
        value="Cette catégorie est automatiquement masquée aux non-VIP. Dès que le rôle **💎・VIP** est attribué après validation, les salons Premium deviennent visibles.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V45 • Premium = ressources avancées + accompagnement humain")
    return e


def premium_video_home_embed() -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Vidéos Premium",
        description=(
            "Bibliothèque technique réservée aux membres **💎・VIP**. Les liens ouvrent des recherches YouTube ciblées afin de rester utiles même quand "
            "les outils changent de version. Chaque catégorie contient une sélection courte de sujets à appliquer sur ton propre projet."
        ),
        color=0xEB459E,
    )
    for data in PREMIUM_VIDEO_CATEGORIES.values():
        e.add_field(name=data["label"], value=data["description"], inline=True)
    e.add_field(
        name="Comment l’utiliser",
        value="Choisis une catégorie → regarde un sujet précis → applique-le → si tu bloques, ouvre ton accompagnement Premium avec ce que tu as déjà essayé.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V45 • 25 sujets Premium • contenu avancé • application pratique")
    return e


def premium_video_category_embed(category: str) -> discord.Embed:
    data = PREMIUM_VIDEO_CATEGORIES[category]
    e = discord.Embed(
        title=f"Premium — {data['label']}",
        description=data["description"],
        color=0xEB459E,
    )
    for key in _premium_keys(category):
        video = PREMIUM_VIDEO_LIBRARY[key]
        e.add_field(name=video["title"][:256], value=video["note"][:1024], inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V45 • Regarde uniquement le sujet utile puis applique-le sur ton projet")
    return e


async def _require_premium(interaction: discord.Interaction) -> bool:
    if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
        return True
    shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
    await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
    return False


class PremiumVideoCategoryLinks(discord.ui.View):
    def __init__(self, category: str) -> None:
        super().__init__(timeout=900)
        for key in _premium_keys(category):
            video = PREMIUM_VIDEO_LIBRARY[key]
            self.add_item(
                discord.ui.Button(
                    label=video["title"][:80],
                    url=video["url"],
                    style=discord.ButtonStyle.link,
                )
            )


class PremiumVideoCategorySelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(label=data["label"], value=key, description=data["description"][:100])
            for key, data in PREMIUM_VIDEO_CATEGORIES.items()
        ]
        super().__init__(
            placeholder="Choisis une catégorie Premium",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:v45:premium-videos:category",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await _require_premium(interaction):
            return
        category = self.values[0]
        await interaction.response.send_message(
            embed=premium_video_category_embed(category),
            view=PremiumVideoCategoryLinks(category),
            ephemeral=True,
        )


class PremiumVideoLibraryView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(PremiumVideoCategorySelect())


class PremiumHubView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Vidéos Premium", style=discord.ButtonStyle.primary, custom_id="aidebot:v45:premium:videos")
    async def videos(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_premium(interaction):
            return
        await interaction.response.send_message(
            embed=premium_video_home_embed(),
            view=PremiumVideoLibraryView(),
            ephemeral=True,
        )

    @discord.ui.button(label="Formations avancées", style=discord.ButtonStyle.secondary, custom_id="aidebot:v45:premium:training")
    async def training(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_premium(interaction):
            return
        training = interaction.client.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_message(
            embed=training_catalog_embed(),
            view=TrainingPanel(training),
            ephemeral=True,
        )

    @discord.ui.button(label="Support Premium", style=discord.ButtonStyle.success, custom_id="aidebot:v45:premium:support")
    async def support(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_premium(interaction):
            return
        training = interaction.client.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de tickets indisponible.", ephemeral=True)
        await interaction.response.send_modal(TrainingRequestModal(training, "vip"))

    @discord.ui.button(label="Mon espace", style=discord.ButtonStyle.secondary, custom_id="aidebot:v45:premium:space")
    async def space(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_premium(interaction):
            return
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=await member_space_embed(self.bot, interaction.user), ephemeral=True)

    @discord.ui.button(label="Statut VIP", style=discord.ButtonStyle.secondary, custom_id="aidebot:v45:premium:status")
    async def status(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_premium(interaction):
            return
        assert isinstance(interaction.user, discord.Member)
        await interaction.response.send_message(embed=premium_member_embed(interaction.user), ephemeral=True)


def _install_setup_patch() -> None:
    """Extend /setup through regular methods; never mutate app_commands.Command.callback."""
    if getattr(SetupServerCog, "_aidebot_v45_patched", False):
        return

    original_category_permissions = SetupServerCog._reconcile_category_permissions
    original_channel_permissions = SetupServerCog._reconcile_channel_permissions

    async def category_permissions(
        self: SetupServerCog,
        guild: discord.Guild,
        category: discord.CategoryChannel,
        roles: dict[str, discord.Role],
    ) -> None:
        await original_category_permissions(self, guild, category, roles)
        if category.name != PREMIUM_CATEGORY:
            return
        await category.set_permissions(
            guild.default_role,
            view_channel=False,
            reason="Aide Bot V45 — Premium privé",
        )
        await category.set_permissions(
            roles["💎・VIP"],
            view_channel=True,
            send_messages=False,
            read_message_history=True,
            reason="Aide Bot V45 — accès VIP",
        )
        for role_name in ("👑・Direction", "📘・Responsable Formation", "🎓・Formateur"):
            await category.set_permissions(
                roles[role_name],
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                reason="Aide Bot V45 — staff Premium",
            )

    async def channel_permissions(
        self: SetupServerCog,
        guild: discord.Guild,
        channel: discord.TextChannel,
        roles: dict[str, discord.Role],
    ) -> None:
        await original_channel_permissions(self, guild, channel, roles)
        if not channel.category or channel.category.name != PREMIUM_CATEGORY:
            return

        await channel.set_permissions(
            guild.default_role,
            view_channel=False,
            reason="Aide Bot V45 — salon Premium privé",
        )
        await channel.set_permissions(
            roles["💎・VIP"],
            view_channel=True,
            send_messages=False,
            read_message_history=True,
            reason="Aide Bot V45 — lecture VIP",
        )
        for role_name in ("👑・Direction", "📘・Responsable Formation", "🎓・Formateur"):
            await channel.set_permissions(
                roles[role_name],
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True,
                reason="Aide Bot V45 — staff Premium",
            )

        if channel.name == PREMIUM_HUB_CHANNEL:
            await self._upsert_panel(channel, premium_hub_embed(), PremiumHubView(self.bot))
        elif channel.name == PREMIUM_VIDEO_CHANNEL:
            await self._upsert_panel(channel, premium_video_home_embed(), PremiumVideoLibraryView())

    SetupServerCog._reconcile_category_permissions = category_permissions
    SetupServerCog._reconcile_channel_permissions = channel_permissions
    SetupServerCog._aidebot_v45_patched = True


class PremiumV45Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        _install_setup_patch()
        self.bot.add_view(PremiumHubView(self.bot))
        self.bot.add_view(PremiumVideoLibraryView())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PremiumV45Cog(bot))
