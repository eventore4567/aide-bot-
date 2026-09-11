from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from aidebot.cogs.member_experience import MemberHubView
from aidebot.ops import MEMBER_HUB_MARKER, OPS_DASHBOARD_MARKER, format_operations
from aidebot.permissions import can
from aidebot.worker_resilience import run_isolated_batch

log = logging.getLogger("aidebot.ops_dashboard")


class OpsDashboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.refresh_dashboards.start()

    async def cog_unload(self) -> None:
        self.refresh_dashboards.cancel()

    async def _find_bot_message(self, channel: discord.TextChannel, marker: str) -> tuple[bool, discord.Message | None]:
        if not self.bot.user:
            return False, None
        try:
            async for message in channel.history(limit=50):
                if message.author.id != self.bot.user.id:
                    continue
                for item in message.embeds:
                    if item.footer and item.footer.text == marker:
                        return True, message
        except (discord.Forbidden, discord.HTTPException):
            # Fail closed: never create another panel when history could not be
            # inspected, otherwise a temporary permission/API failure can spam
            # duplicate permanent panels.
            return False, None
        return True, None

    async def refresh_ops_dashboard(self, guild: discord.Guild, *, allow_create: bool = True) -> bool:
        channel = discord.utils.get(guild.text_channels, name="🧠・suivi-formations")
        if channel is None:
            return False

        stats = await self.bot.db.dashboard_stats(guild.id)
        embed = discord.Embed(
            title="Aide Bot — Suivi opérationnel",
            description=format_operations(stats),
            color=0x57F287,
        )
        embed.set_footer(text=OPS_DASHBOARD_MARKER)

        history_checked, existing = await self._find_bot_message(channel, OPS_DASHBOARD_MARKER)
        if existing:
            try:
                await existing.edit(embed=embed)
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

        if not history_checked or not allow_create:
            return False
        try:
            await channel.send(embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    async def ensure_member_hub(self, guild: discord.Guild, *, allow_create: bool = True) -> bool:
        channel = discord.utils.get(guild.text_channels, name="🎫・commencer")
        if channel is None:
            return False

        history_checked, existing = await self._find_bot_message(channel, MEMBER_HUB_MARKER)
        if existing:
            return True
        if not history_checked or not allow_create:
            return False

        embed = discord.Embed(
            title="Aide Bot — Commencer",
            description=(
                "Tout passe par ce panneau : choisis une formation, cherche une réponse, demande de l’aide, "
                "consulte ta progression ou commence à aider la communauté.\n\n"
                "Pour une recommandation personnalisée, utilise aussi `/commencer`."
            ),
            color=0x5865F2,
        )
        embed.set_footer(text=MEMBER_HUB_MARKER)
        try:
            await channel.send(embed=embed, view=MemberHubView(self.bot))
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    async def refresh_guild(self, guild: discord.Guild) -> tuple[bool, bool]:
        # Keep both panels independent: a DB/Discord issue on the staff
        # dashboard must not prevent the member hub from being reconciled.
        ops = False
        hub = False
        try:
            ops = await self.refresh_ops_dashboard(guild)
        except Exception as exc:
            log.exception("Échec dashboard opérations guild=%s", guild.id, exc_info=exc)
        try:
            hub = await self.ensure_member_hub(guild)
        except Exception as exc:
            log.exception("Échec centre membre guild=%s", guild.id, exc_info=exc)
        return ops, hub

    async def _refresh_one(self, guild: discord.Guild) -> None:
        await self.refresh_guild(guild)

    async def _refresh_error(self, guild: discord.Guild, exc: Exception) -> None:
        log.exception("Échec isolé de réconciliation des panneaux guild=%s", guild.id, exc_info=exc)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await run_isolated_batch(self.bot.guilds, self._refresh_one, self._refresh_error)

    @tasks.loop(minutes=5)
    async def refresh_dashboards(self) -> None:
        # One guild must never be able to stop updates for every other guild or
        # terminate this long-lived task.
        try:
            await run_isolated_batch(self.bot.guilds, self._refresh_one, self._refresh_error)
        except Exception:
            # Defensive outer boundary: keep the task alive even if an
            # unexpected iterable/runtime problem happens outside one guild.
            log.exception("Erreur inattendue du worker dashboards; prochaine itération conservée")

    @refresh_dashboards.before_loop
    async def before_refresh_dashboards(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(name="dashboard_actualiser", description="Actualiser le panneau de suivi des formations et de l'entraide")
    async def dashboard_actualiser(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "dashboard.view"):
            return await interaction.response.send_message("Accès refusé : `dashboard.view` requis.", ephemeral=True)
        updated = await self.refresh_ops_dashboard(interaction.guild)
        await interaction.response.send_message(
            "Dashboard actualisé." if updated else "Impossible d'actualiser le dashboard. Vérifie le setup et les permissions du bot.",
            ephemeral=True,
        )

    @app_commands.command(name="panneaux_actualiser", description="Réconcilier les panneaux permanents Aide Bot")
    async def panneaux_actualiser(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "config.manage"):
            return await interaction.response.send_message("Accès refusé : `config.manage` requis.", ephemeral=True)
        ops, hub = await self.refresh_guild(interaction.guild)
        await interaction.response.send_message(
            f"Suivi opérationnel : **{'OK' if ops else 'échec'}** • Centre membre : **{'OK' if hub else 'échec'}**.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OpsDashboardCog(bot))
