from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs.assistant_guardian_v52 import (
    AI_CHANNEL,
    LEGACY_VIDEO_CHANNEL,
    STAFF_CHANNEL,
    AssistantPanelView,
    GuardianPanelView,
    _cleanup_legacy_video_panel,
    _upsert_panel,
    assistant_panel_embed,
    guardian_panel_embed,
)


class AssistantGuardianSetupV52Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        # Le setup historique tente encore de publier le panneau vidéo public.
        # V52 a volontairement remplacé ce salon par l'assistant IA afin de
        # conserver seulement 15 salons permanents. On marque donc ce panneau
        # comme remplacé au lieu de faire apparaître un faux échec dans /setup.
        from aidebot.cogs.setup_server import SetupServerCog
        from aidebot.public_panels import VIDEOS_TITLE

        if not getattr(SetupServerCog, "_aidebot_v52_video_replaced", False):
            original_upsert = SetupServerCog._upsert_panel

            async def upsert(self, channel, embed, view=None):
                if channel is None and getattr(embed, "title", None) == VIDEOS_TITLE:
                    return "replaced_by_ai"
                return await original_upsert(self, channel, embed, view)

            SetupServerCog._upsert_panel = upsert
            SetupServerCog._aidebot_v52_video_replaced = True

    def _core(self):
        return self.bot.get_cog("AssistantGuardianV52Cog")

    async def _configure_ai_channel(self, channel: discord.TextChannel, *, apply_permissions: bool) -> None:
        core = self._core()
        if core is None:
            return
        guild = channel.guild
        if apply_permissions:
            try:
                await channel.set_permissions(
                    guild.default_role,
                    view_channel=True,
                    send_messages=False,
                    read_message_history=True,
                    reason="Aide Bot V52 — panneau Assistant IA en lecture seule",
                )
                for role_name in ("👑・Direction", "📘・Responsable Formation", "🎓・Formateur", "🤝・Helper"):
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role is None:
                        continue
                    await channel.set_permissions(
                        role,
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_messages=role_name in {"👑・Direction", "📘・Responsable Formation"},
                        reason="Aide Bot V52 — accès équipe au salon Assistant IA",
                    )
            except (discord.Forbidden, discord.HTTPException):
                pass
        await _cleanup_legacy_video_panel(self.bot, channel)
        await _upsert_panel(
            self.bot,
            channel,
            embed=assistant_panel_embed(core.ai.configured),
            view=AssistantPanelView(core),
        )

    async def _configure_staff_panel(self, channel: discord.TextChannel) -> None:
        core = self._core()
        if core is None:
            return
        await _upsert_panel(self.bot, channel, embed=guardian_panel_embed(), view=GuardianPanelView(core))

    async def _reconcile(self, guild: discord.Guild) -> None:
        ai_channel = discord.utils.get(guild.text_channels, name=AI_CHANNEL)
        if ai_channel is not None:
            # Un salon déjà existant vient généralement de l'ancien salon vidéo,
            # qui était déjà en lecture seule. Ne réécris pas ses overwrites au
            # démarrage : cela éviter de créer un faux drift Guardian.
            await self._configure_ai_channel(ai_channel, apply_permissions=False)
        staff = discord.utils.get(guild.text_channels, name=STAFF_CHANNEL)
        if staff is not None:
            await self._configure_staff_panel(staff)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            await self._reconcile(guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.TextChannel):
            return
        if channel.name == AI_CHANNEL:
            await self._configure_ai_channel(channel, apply_permissions=True)
        elif channel.name == STAFF_CHANNEL:
            await self._configure_staff_panel(channel)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> None:
        if not isinstance(after, discord.TextChannel):
            return
        if before.name == LEGACY_VIDEO_CHANNEL and after.name == AI_CHANNEL:
            # L'ancien salon vidéo était déjà public en lecture seule ; garde ses
            # permissions pendant la migration et remplace seulement son panneau.
            await self._configure_ai_channel(after, apply_permissions=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AssistantGuardianSetupV52Cog(bot))
