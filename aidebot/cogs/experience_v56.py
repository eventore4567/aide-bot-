from __future__ import annotations

import discord
from discord.ext import commands

import aidebot.cogs.center_autopost as center_autopost
import aidebot.cogs.product_experience_v51 as product_v51
import aidebot.cogs.setup_server as setup_server
import aidebot.cogs.setup_experience_v55 as setup_v55
from aidebot.cogs.assistant_guardian_v52 import AskAIModal
from aidebot.cogs.experience_v43 import member_space_embed
from aidebot.cogs.experience_v44 import SmartSupportView
from aidebot.cogs.help_system_v54 import (
    HELP_CARDS,
    HELP_CATEGORIES,
    HelpCard,
    EscalationModal,
    classify_problem,
)
from aidebot.cogs.premium_v45 import PREMIUM_VIDEO_CHANNEL
from aidebot.cogs.training_experience_v42 import V42TrainingPanel, training_catalog_embed
from aidebot.experience_content import BANNER_URL

COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F
CENTER_CHANNEL = "🎓・centre-aide"
CENTER_TITLE = "Aide Bot — Centre d’aide"

# Ces salons ont été utiles pendant les itérations précédentes, mais ils
# dupliquent désormais des actions présentes dans le Centre d'aide V56.
OBSOLETE_PANEL_CHANNELS = (
    "🆘・aide-rapide",
    "🤖・assistant-aide",
    "📚・guides",
    "🎫・ouvrir-ticket",
    PREMIUM_VIDEO_CHANNEL,
    "🎥・videos-guides",
)


def help_hub_embed() -> discord.Embed:
    e = discord.Embed(
        title=CENTER_TITLE,
        description=(
            "**Un seul endroit pour toute l’aide.** Tu n’as plus besoin de choisir entre plusieurs salons qui font presque la même chose.\n\n"
            "Choisis ce que tu veux faire dans le menu : trouver une solution, poser une question à l’IA, contacter le support, commencer une formation ou consulter ton espace."
        ),
        color=COLOR,
    )
    e.add_field(
        name="Trouver une solution",
        value="Choisis un domaine puis ton problème exact. La réponse affiche les vérifications et la correction dans le bon ordre.",
        inline=True,
    )
    e.add_field(
        name="Question libre",
        value="L’Assistant IA sert uniquement quand ton problème ne rentre pas bien dans une fiche existante.",
        inline=True,
    )
    e.add_field(
        name="Support humain",
        value="Si les vérifications ne suffisent pas, le ticket récupère le contexte déjà identifié au lieu de repartir de zéro.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • 1 centre • 1 action claire par besoin")
    return e


def welcome_embed_v56() -> discord.Embed:
    e = discord.Embed(
        title="Bienvenue — Aide Bot",
        description=(
            "Bienvenue. Ici, le parcours est volontairement simple : **commence par le Centre d’aide**. "
            "Il regroupe les solutions, l’IA, le support et les raccourcis utiles sans te faire naviguer entre plusieurs panneaux identiques."
        ),
        color=COLOR,
    )
    e.add_field(
        name="Comment commencer ?",
        value="Clique sur **Commencer** → choisis ton besoin → suis les étapes proposées.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Accueil simplifié")
    return e


def category_embed_v56(category: str) -> discord.Embed:
    label, description = HELP_CATEGORIES[category]
    cards = [card for card in HELP_CARDS.values() if card.category == category]
    e = discord.Embed(
        title=f"Solutions — {label}",
        description=description,
        color=COLOR,
    )
    e.add_field(
        name=f"{len(cards)} problème(s) couvert(s)",
        value="\n".join(f"• **{card.label}** — {card.description}" for card in cards)[:1024],
        inline=False,
    )
    e.set_footer(text="Choisis le problème précis dans le menu ci-dessous")
    return e


def solution_embed_v56(card: HelpCard) -> discord.Embed:
    e = discord.Embed(title=card.label, description=card.description, color=SUCCESS)
    e.add_field(
        name="1 — Vérifie",
        value="\n".join(f"**{index}.** {item}" for index, item in enumerate(card.checks, start=1)),
        inline=False,
    )
    e.add_field(
        name="2 — Corrige",
        value="\n".join(f"**{index}.** {item}" for index, item in enumerate(card.fixes, start=1)),
        inline=False,
    )
    if card.category == "security":
        e.add_field(
            name="Sécurité",
            value="Ne partage jamais token, cookie, mot de passe, code 2FA ou code de récupération, même dans un ticket.",
            inline=False,
        )
    e.set_footer(text="Si le problème continue : IA pour approfondir, Support pour une prise en charge humaine")
    return e


async def _open_ai(interaction: discord.Interaction) -> None:
    cog = interaction.client.get_cog("AssistantGuardianV52Cog")
    if cog is None or not cog.ai.configured:
        await interaction.response.send_message(
            "L’Assistant IA n’est pas disponible pour le moment. Utilise le support humain depuis le Centre d’aide.",
            ephemeral=True,
        )
        return
    await interaction.response.send_modal(AskAIModal(cog))


async def _open_training(interaction: discord.Interaction) -> None:
    training = interaction.client.get_cog("TrainingCog")
    if training is None:
        await interaction.response.send_message("Les formations sont temporairement indisponibles.", ephemeral=True)
        return
    await interaction.response.send_message(
        embed=training_catalog_embed(),
        view=V42TrainingPanel(training),
        ephemeral=True,
    )


class SolutionResultViewV56(discord.ui.View):
    def __init__(self, bot: commands.Bot, card: HelpCard) -> None:
        super().__init__(timeout=900)
        self.bot = bot
        self.card = card

    @discord.ui.button(label="Retour aux solutions", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=help_hub_embed(), view=HelpHubViewV56(self.bot))

    @discord.ui.button(label="Approfondir avec l’IA", style=discord.ButtonStyle.primary)
    async def ai(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await _open_ai(interaction)

    @discord.ui.button(label="Support humain", style=discord.ButtonStyle.success)
    async def support(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(EscalationModal(self.bot, self.card))


class SolutionTopicSelectV56(discord.ui.Select):
    def __init__(self, bot: commands.Bot, category: str) -> None:
        self.bot = bot
        cards = [card for card in HELP_CARDS.values() if card.category == category]
        super().__init__(
            placeholder="Choisis ton problème précis",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=card.label[:100], value=card.key, description=card.description[:100])
                for card in cards[:25]
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        card = HELP_CARDS[self.values[0]]
        await interaction.response.edit_message(embed=solution_embed_v56(card), view=SolutionResultViewV56(self.bot, card))


class SolutionTopicViewV56(discord.ui.View):
    def __init__(self, bot: commands.Bot, category: str) -> None:
        super().__init__(timeout=900)
        self.add_item(SolutionTopicSelectV56(bot, category))

    @discord.ui.button(label="Retour", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=help_hub_embed(), view=HelpHubViewV56(interaction.client))


class SolutionCategorySelectV56(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__(
            placeholder="Choisis le domaine du problème",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=label, value=key, description=description[:100])
                for key, (label, description) in HELP_CATEGORIES.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        category = self.values[0]
        await interaction.response.edit_message(
            embed=category_embed_v56(category),
            view=SolutionTopicViewV56(self.bot, category),
        )


class SolutionBrowseViewV56(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=900)
        self.add_item(SolutionCategorySelectV56(bot))

    @discord.ui.button(label="Retour", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=help_hub_embed(), view=HelpHubViewV56(interaction.client))


class DescribeProblemModalV56(discord.ui.Modal, title="Décrire mon problème"):
    problem = discord.ui.TextInput(
        label="Explique ce qui ne marche pas",
        placeholder="Ex: mon rôle modo voit le salon mais ne peut pas écrire",
        style=discord.TextStyle.paragraph,
        min_length=8,
        max_length=1200,
    )

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        card = classify_problem(str(self.problem))
        if card is None:
            e = discord.Embed(
                title="Problème non reconnu automatiquement",
                description=(
                    "Je préfère ne pas inventer de diagnostic. Tu peux poser la question à l’IA ou passer au support humain avec ton explication."
                ),
                color=WARNING,
            )
            return await interaction.response.send_message(embed=e, view=UnclearProblemViewV56(self.bot), ephemeral=True)
        await interaction.response.send_message(
            embed=solution_embed_v56(card),
            view=SolutionResultViewV56(self.bot, card),
            ephemeral=True,
        )


class UnclearProblemViewV56(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=900)
        self.bot = bot

    @discord.ui.button(label="Demander à l’IA", style=discord.ButtonStyle.primary)
    async def ai(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await _open_ai(interaction)

    @discord.ui.button(label="Support humain", style=discord.ButtonStyle.success)
    async def support(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        e = discord.Embed(
            title="Support Aide Bot",
            description="Choisis la catégorie qui correspond le mieux à ton problème. Le formulaire demandera uniquement le contexte utile.",
            color=SUCCESS,
        )
        await interaction.response.edit_message(embed=e, view=SmartSupportView(self.bot))


class HelpIntentSelectV56(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(label="Trouver une solution", value="solution", description="Diagnostic + correction guidée"),
            discord.SelectOption(label="Poser une question à l’IA", value="ai", description="Pour une question libre ou un cas inhabituel"),
            discord.SelectOption(label="Contacter le support", value="support", description="Créer une demande humaine avec le bon formulaire"),
            discord.SelectOption(label="Commencer une formation", value="training", description="Parcours guidés pour apprendre"),
            discord.SelectOption(label="Voir mon espace", value="space", description="Demandes en cours et statut personnel"),
        ]
        super().__init__(
            placeholder="Qu’est-ce que tu veux faire ?",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:v56:help:intent",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        choice = self.values[0]
        if choice == "solution":
            e = discord.Embed(
                title="Trouver une solution",
                description="Choisis le domaine concerné. Le menu suivant affichera uniquement les problèmes de ce domaine.",
                color=COLOR,
            )
            return await interaction.response.send_message(embed=e, view=SolutionBrowseViewV56(self.bot), ephemeral=True)
        if choice == "ai":
            return await _open_ai(interaction)
        if choice == "support":
            e = discord.Embed(
                title="Support Aide Bot",
                description="Choisis la catégorie qui correspond à ton problème. Un seul ticket actif est conservé pour éviter les doublons.",
                color=SUCCESS,
            )
            return await interaction.response.send_message(embed=e, view=SmartSupportView(self.bot), ephemeral=True)
        if choice == "training":
            return await _open_training(interaction)
        if choice == "space":
            if not isinstance(interaction.user, discord.Member):
                return
            return await interaction.response.send_message(
                embed=await member_space_embed(self.bot, interaction.user),
                ephemeral=True,
            )


class HelpHubViewV56(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(HelpIntentSelectV56(bot))

    @discord.ui.button(label="Décrire mon problème", style=discord.ButtonStyle.primary, custom_id="aidebot:v56:help:describe", row=1)
    async def describe(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(DescribeProblemModalV56(self.bot))


class WelcomeViewV56(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Commencer", style=discord.ButtonStyle.primary, custom_id="aidebot:v56:welcome:start")
    async def start(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=help_hub_embed(), view=HelpHubViewV56(self.bot), ephemeral=True)


async def _safe_remove_redundant_panel_channel(bot: commands.Bot, guild: discord.Guild, name: str) -> str:
    channel = discord.utils.get(guild.text_channels, name=name)
    if channel is None:
        return "déjà absent"
    if bot.user is None:
        return "conservé"
    if getattr(channel, "threads", None):
        if channel.threads:
            return "conservé (threads)"
    try:
        async for message in channel.history(limit=None, oldest_first=True):
            if message.author.id != bot.user.id:
                return "conservé (contenu humain)"
    except (discord.Forbidden, discord.HTTPException):
        return "conservé (non vérifiable)"
    try:
        await channel.delete(reason="Aide Bot — consolidation V56 des panneaux redondants")
        return "supprimé"
    except (discord.Forbidden, discord.HTTPException):
        return "échec suppression"


class HelpSystemV54Cog(commands.Cog):
    """Nom de Cog conservé pour compatibilité avec le préflight du setup V55."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._ready_guilds: set[int] = set()

    async def cog_load(self) -> None:
        self.bot.add_view(HelpHubViewV56(self.bot))
        self.bot.add_view(WelcomeViewV56(self.bot))

        # Tous les anciens points d'entrée ouvrent désormais le même hub.
        product_v51.help_center_embed_v51 = lambda _vip_price=None: help_hub_embed()
        product_v51.HelpCenterViewV51 = lambda _bot: HelpHubViewV56(self.bot)
        product_v51.welcome_embed_v51 = welcome_embed_v56
        product_v51.WelcomeViewV51 = lambda _bot: WelcomeViewV56(self.bot)
        center_autopost.center_embed = lambda _price=None: help_hub_embed()
        center_autopost.CenterView = lambda _center_cog: HelpHubViewV56(self.bot)
        setup_server.center_embed = lambda _price=None: help_hub_embed()
        setup_server.CenterView = lambda _center_cog: HelpHubViewV56(self.bot)

        # Le setup ne doit plus transformer l'ancien salon vidéo en nouveau salon IA.
        setup_v55.LEGACY_VIDEO_CHANNEL = "__aidebot_v56_no_ai_channel__"

        # Remplace uniquement les méthodes normales du setup, jamais Command.callback.
        setup_v55.SetupExperienceV55Cog._publish_panels = _publish_panels_v56
        setup_v55.SetupExperienceV55Cog._preflight_embed = _preflight_embed_v56

    async def _configure_channel(self, channel: discord.TextChannel) -> None:
        guild = channel.guild
        try:
            await channel.set_permissions(
                guild.default_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True,
                reason="Aide Bot — Centre d'aide public en lecture seule",
            )
            for role_name in ("👑・Direction", "📘・Responsable Formation", "🎓・Formateur", "🤝・Helper"):
                role = discord.utils.get(guild.roles, name=role_name)
                if role is not None:
                    await channel.set_permissions(
                        role,
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_messages=role_name in {"👑・Direction", "📘・Responsable Formation"},
                        reason="Aide Bot — équipe d'aide",
                    )
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _upsert_center(self, guild: discord.Guild) -> None:
        channel = discord.utils.get(guild.text_channels, name=CENTER_CHANNEL)
        base = self.bot.get_cog("SetupServerCog")
        if channel is None or base is None:
            return
        await self._configure_channel(channel)
        await base._upsert_panel(channel, help_hub_embed(), HelpHubViewV56(self.bot))

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            if guild.id in self._ready_guilds:
                continue
            self._ready_guilds.add(guild.id)
            await self._upsert_center(guild)


async def _publish_panels_v56(self, guild: discord.Guild, channels: dict[str, discord.TextChannel], roles: dict[str, discord.Role]) -> list[tuple[str, str]]:
    base = self._base_setup()
    assert base is not None
    actions: list[tuple[str, str]] = []

    # Nettoie uniquement les anciens salons de panneaux contenant exclusivement
    # des messages du bot. Tout contenu humain est conservé automatiquement.
    for name in OBSOLETE_PANEL_CHANNELS:
        state = await _safe_remove_redundant_panel_channel(self.bot, guild, name)
        actions.append((f"Consolidation {name}", state))

    async def upsert(label: str, channel_name: str, embed: discord.Embed, view: discord.ui.View | None = None) -> None:
        actions.append((label, await base._upsert_panel(channels.get(channel_name), embed, view)))

    await upsert("Bienvenue", "👋・bienvenue", welcome_embed_v56(), WelcomeViewV56(self.bot))
    await upsert("Règlement", "📜・règlement", base._rules_embed())
    await upsert("Centre d’aide", CENTER_CHANNEL, help_hub_embed(), HelpHubViewV56(self.bot))

    training = self.bot.get_cog("TrainingCog")
    if training is not None:
        from aidebot.cogs.training import TrainingPanel
        await upsert("Formations", "🎓・formations", base._training_embed(), TrainingPanel(training))
    else:
        actions.append(("Formations", "absent"))

    guardian = self.bot.get_cog("AssistantGuardianV52Cog")
    if guardian is not None:
        from aidebot.cogs.assistant_guardian_v52 import GuardianPanelView, guardian_panel_embed
        await upsert("Guardian", "📋・staff", guardian_panel_embed(), GuardianPanelView(guardian))
    else:
        actions.append(("Guardian", "absent"))

    await upsert("Boutique", "🛒・shop", product_v51.shop_embed_v51(self.bot.settings.vip_price_robux), product_v51.ShopViewV51(self.bot))
    await upsert("Recrutement", "🧑‍🏫・recrutement", __import__("aidebot.cogs.recruitment_panel", fromlist=["recruitment_embed"]).recruitment_embed(), __import__("aidebot.cogs.recruitment_panel", fromlist=["RecruitmentView"]).RecruitmentView(self.bot))
    await upsert("Premium", "💎・espace-premium", product_v51.premium_hub_embed_v51(), product_v51.PremiumHubViewV51(self.bot))
    return actions


def _preflight_embed_v56(self, guild: discord.Guild, report) -> discord.Embed:
    color = 0xED4245 if report.blocked else WARNING if report.hierarchy_warnings else COLOR
    e = discord.Embed(
        title="Aide Bot — Installation & réparation",
        description=(
            "Le setup installe une structure **plus courte et plus lisible**. Diagnostics, solutions, IA et support sont regroupés dans un seul Centre d’aide au lieu de plusieurs salons similaires."
        ),
        color=color,
    )
    e.add_field(
        name="Plan visible",
        value=(
            f"Rôles à créer : **{report.roles_to_create}**\n"
            f"Catégories à créer : **{report.categories_to_create}**\n"
            f"Salons à créer : **{report.channels_to_create}**\n"
            f"Salons à replacer : **{report.channels_to_move}**"
        ),
        inline=True,
    )
    e.add_field(
        name="Structure finale",
        value="Accueil • Centre d’aide tout-en-un • Formations • Boutique • Premium • Avis • Recrutement • Staff.",
        inline=True,
    )
    e.add_field(
        name="Consolidation",
        value=(
            "Les anciens salons Aide rapide / Assistant IA / Guides / Ouvrir ticket / Vidéos Premium sont supprimés **uniquement s’ils contiennent seulement des messages du bot**. "
            "S’il existe du contenu humain, le salon est conservé."
        ),
        inline=False,
    )
    if report.missing_permissions:
        e.add_field(name="Permissions manquantes", value="\n".join(f"• {item}" for item in report.missing_permissions), inline=False)
    if report.collisions:
        from aidebot.setup_guard import format_collisions
        e.add_field(name="Doublons à corriger", value=format_collisions(list(report.collisions)), inline=False)
    if report.module_warnings:
        e.add_field(name="Modules indisponibles", value="\n".join(f"• {item}" for item in report.module_warnings), inline=False)
    if report.hierarchy_warnings:
        e.add_field(name="Hiérarchie à surveiller", value=", ".join(f"**{name}**" for name in report.hierarchy_warnings[:8]), inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Installer / réparer = appliquer la structure • Vérifier seulement = aucun changement")
    return e


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpSystemV54Cog(bot))
