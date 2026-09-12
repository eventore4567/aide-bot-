from __future__ import annotations

import re
import time

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.cogs.assistant_guardian_v52 import AskAIModal
from aidebot.cogs.experience_v56 import HelpHubViewV56, help_hub_embed
from aidebot.cogs.product_suite_v60 import (
    ProductSuiteV60Cog,
    SERVER_PROFILES,
    SetupWizardViewV60,
    audit360_embed,
)
from aidebot.cogs.setup_experience_v55 import SetupExperienceV55Cog
from aidebot.experience_content import BANNER_URL

COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F
GENERAL_CHANNEL = "💬・général"
INSTANT_HELP_TITLE = "Aide Bot — Aide instantanée"

# Le profil Général doit être le choix le plus évident dans l'installateur avancé.
# On conserve tous les profils spécialisés V60 mais on ne les impose plus au premier écran.
if "general" not in SERVER_PROFILES:
    _existing_profiles = dict(SERVER_PROFILES)
    SERVER_PROFILES.clear()
    SERVER_PROFILES["general"] = (
        "Général",
        "Configuration équilibrée pour un serveur classique : discussion, aide, communauté, formations et sécurité.",
    )
    SERVER_PROFILES.update(_existing_profiles)


def quick_setup_embed(guild: discord.Guild | None = None) -> discord.Embed:
    embed = discord.Embed(
        title="Aide Bot — Installation simple",
        description=(
            "Pas besoin de régler 3 menus pour commencer. **Installer automatiquement** applique la configuration recommandée "
            "avec le profil Général et le thème Clean. Tu peux personnaliser seulement si tu en as besoin."
        ),
        color=COLOR,
    )
    embed.add_field(
        name="Installer automatiquement",
        value="Crée/répare la structure Aide Bot, le salon Général, le Centre d’aide, l’Academy, les rôles et les panneaux.",
        inline=False,
    )
    embed.add_field(
        name="Personnaliser",
        value="Ouvre les réglages avancés : profils spécialisés et thèmes. Rien n’est obligatoire.",
        inline=True,
    )
    embed.add_field(
        name="Vérifier",
        value="Lance seulement l’Audit 360 sans modifier le serveur.",
        inline=True,
    )
    if guild is not None:
        embed.add_field(name="Serveur", value=guild.name, inline=False)
    embed.set_footer(text="Recommandé : Installer automatiquement")
    return embed


def instant_help_embed(ai_ready: bool) -> discord.Embed:
    embed = discord.Embed(
        title=INSTANT_HELP_TITLE,
        description=(
            "Besoin d’aide ? Utilise les boutons ci-dessous ou **mentionne Aide Bot avec ta question**.\n\n"
            "Exemple : `@Aide Bot aide, pourquoi mon rôle ne voit pas ce salon ?`"
        ),
        color=COLOR,
    )
    embed.add_field(
        name="Centre d’aide",
        value="Solutions guidées, diagnostic, support humain et formations.",
        inline=True,
    )
    embed.add_field(
        name="Assistant IA",
        value="Disponible maintenant." if ai_ready else "La clé IA doit être configurée côté hébergement.",
        inline=True,
    )
    embed.add_field(
        name="Discussion normale",
        value="Ce salon reste un vrai général : Aide Bot intervient seulement quand tu lui demandes de l’aide.",
        inline=False,
    )
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Aide Bot • parle normalement • demande de l’aide quand tu en as besoin")
    return embed


class QuickSetupViewV62(discord.ui.View):
    def __init__(self, cog: "SimpleHelpV62Cog", user_id: int) -> None:
        super().__init__(timeout=900)
        self.cog = cog
        self.user_id = int(user_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.user_id:
            return True
        await interaction.response.send_message(
            "Seule la personne qui a lancé `/setup` peut utiliser cet installateur.",
            ephemeral=True,
        )
        return False

    @discord.ui.button(label="Installer automatiquement", style=discord.ButtonStyle.success, row=0)
    async def install(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild:
            return
        product = interaction.client.get_cog("ProductSuiteV60Cog")
        if isinstance(product, ProductSuiteV60Cog):
            await product.store.save_preferences(interaction.guild.id, profile="general", theme="clean")
            await product.apply_theme(interaction.guild, "clean", apply_now=False)
        base = interaction.client.get_cog("SetupExperienceV55Cog")
        if not isinstance(base, SetupExperienceV55Cog):
            return await interaction.response.send_message(
                "Le moteur d’installation est temporairement indisponible.",
                ephemeral=True,
            )
        await base.run_setup(interaction)

    @discord.ui.button(label="Personnaliser", style=discord.ButtonStyle.secondary, row=0)
    async def customize(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild:
            return
        product = interaction.client.get_cog("ProductSuiteV60Cog")
        if not isinstance(product, ProductSuiteV60Cog):
            return await interaction.response.send_message("Les réglages avancés sont indisponibles.", ephemeral=True)
        view = SetupWizardViewV60(product, interaction.user.id)
        view.profile = "general"
        await interaction.response.edit_message(embed=view.preview_embed(interaction.guild), view=view)

    @discord.ui.button(label="Vérifier", style=discord.ButtonStyle.primary, row=0)
    async def verify(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild:
            return
        await interaction.response.send_message(embed=audit360_embed(interaction.guild), ephemeral=True)


class GeneralHelpViewV62(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="J’ai besoin d’aide", style=discord.ButtonStyle.primary, custom_id="aidebot:v62:general:help")
    async def help(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            embed=help_hub_embed(),
            view=HelpHubViewV56(self.bot),
            ephemeral=True,
        )

    @discord.ui.button(label="Demander à l’IA", style=discord.ButtonStyle.secondary, custom_id="aidebot:v62:general:ai")
    async def ai(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        ai_cog = interaction.client.get_cog("AssistantGuardianV52Cog")
        if ai_cog is None or not ai_cog.ai.configured:
            return await interaction.response.send_message(
                "L’Assistant IA n’est pas disponible pour le moment. Le Centre d’aide reste accessible.",
                ephemeral=True,
            )
        await interaction.response.send_modal(AskAIModal(ai_cog))


class SimpleHelpV62Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._ready: set[int] = set()
        self._message_cooldowns: dict[tuple[int, int], float] = {}

    async def cog_load(self) -> None:
        self.bot.add_view(GeneralHelpViewV62(self.bot))

    def _authorized_setup(self, interaction: discord.Interaction) -> bool:
        return bool(
            interaction.guild
            and isinstance(interaction.user, discord.Member)
            and (
                interaction.guild.owner_id == interaction.user.id
                or interaction.user.guild_permissions.administrator
            )
        )

    async def reconcile_general(self, guild: discord.Guild) -> None:
        channel = discord.utils.get(guild.text_channels, name=GENERAL_CHANNEL)
        if channel is None:
            return
        try:
            await channel.edit(
                topic="Discussion générale • mentionne Aide Bot avec « aide » ou ta question pour obtenir de l’aide.",
                reason="Aide Bot V62 — général et aide conversationnelle",
            )
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await channel.set_permissions(
                guild.default_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                reason="Aide Bot V62 — salon général public",
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

        setup = self.bot.get_cog("SetupServerCog")
        ai_cog = self.bot.get_cog("AssistantGuardianV52Cog")
        if setup is not None:
            await setup._upsert_panel(
                channel,
                instant_help_embed(bool(ai_cog is not None and ai_cog.ai.configured)),
                GeneralHelpViewV62(self.bot),
            )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            if guild.id in self._ready:
                continue
            self._ready.add(guild.id)
            await self.reconcile_general(guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if isinstance(channel, discord.TextChannel) and channel.name == GENERAL_CHANNEL:
            await self.reconcile_general(channel.guild)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None or self.bot.user is None:
            return
        if not isinstance(message.author, discord.Member):
            return

        content = (message.content or "").strip()
        folded = content.casefold()
        simple_help = folded in {"aide", "help", "j'ai besoin d'aide", "j’ai besoin d’aide", "besoin d'aide", "besoin d’aide"}
        mentioned = self.bot.user in message.mentions
        in_general = isinstance(message.channel, discord.TextChannel) and message.channel.name == GENERAL_CHANNEL

        # Discord fournit le contenu des messages qui mentionnent directement le bot même
        # sans activer le privileged Message Content Intent. Le mot "aide" seul fonctionne
        # aussi lorsque Discord expose le contenu du salon ; sinon le panneau reste le fallback.
        if not mentioned and not (in_general and simple_help):
            return

        now = time.monotonic()
        key = (message.guild.id, message.author.id)
        if now - self._message_cooldowns.get(key, 0.0) < 8.0:
            return
        self._message_cooldowns[key] = now

        query = content
        if mentioned:
            query = re.sub(rf"<@!?{self.bot.user.id}>", "", query).strip()
        query = re.sub(r"^(aide|help)\b[\s,:;.!?-]*", "", query, flags=re.IGNORECASE).strip()

        if not query:
            ai_cog = self.bot.get_cog("AssistantGuardianV52Cog")
            await message.reply(
                embed=instant_help_embed(bool(ai_cog is not None and ai_cog.ai.configured)),
                view=GeneralHelpViewV62(self.bot),
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        ai_cog = self.bot.get_cog("AssistantGuardianV52Cog")
        if ai_cog is None or not ai_cog.ai.configured:
            await message.reply(
                embed=help_hub_embed(),
                view=HelpHubViewV56(self.bot),
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        allowed, reason = await ai_cog.ai_limiter.allow(message.guild.id, message.author.id)
        if not allowed:
            await message.reply(reason or "Réessaie plus tard.", mention_author=False)
            return

        try:
            async with message.channel.typing():
                answer, redacted = await ai_cog.ai.answer(
                    question=query[:1500],
                    guild=message.guild,
                    member=message.author,
                )
        except Exception:
            await message.reply(
                "Je n’arrive pas à joindre l’IA pour le moment. Ouvre le **Centre d’aide** avec le bouton ci-dessous.",
                view=GeneralHelpViewV62(self.bot),
                mention_author=False,
            )
            return

        embed = discord.Embed(title="Aide Bot — Réponse", description=answer[:3800], color=COLOR)
        if redacted:
            embed.add_field(
                name="Secret masqué",
                value="Une valeur sensible a été masquée. Si c’était un vrai token ou une clé, régénère-la.",
                inline=False,
            )
        embed.set_footer(text="Tu peux continuer en mentionnant Aide Bot avec ta prochaine question")
        await message.reply(
            embed=embed,
            view=GeneralHelpViewV62(self.bot),
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="setup", description="Installer Aide Bot simplement")
    @app_commands.guild_only()
    async def setup_v62(self, interaction: discord.Interaction) -> None:
        if not self._authorized_setup(interaction):
            return await interaction.response.send_message(
                "Le setup est réservé au propriétaire ou à un administrateur Discord.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=quick_setup_embed(interaction.guild),
            view=QuickSetupViewV62(self, interaction.user.id),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    bot.tree.remove_command("setup")
    await bot.add_cog(SimpleHelpV62Cog(bot))
