from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs.center import CenterView, center_embed
from aidebot.message_reconcile import find_bot_embed_by_title


CENTER_TITLE = "Aide Bot — Centre d’aide & formations"
CENTER_CHANNEL = "🎓・centre-aide"


class CenterAutoPostCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._checked_guilds: set[int] = set()

    async def _publish_or_update(self, channel: discord.TextChannel) -> None:
        if self.bot.user is None:
            return
        center_cog = self.bot.get_cog("CenterCog")
        if center_cog is None:
            return

        checked, existing = await find_bot_embed_by_title(
            channel,
            bot_user_id=self.bot.user.id,
            title=CENTER_TITLE,
            limit=100,
        )
        if existing is not None:
            try:
                await existing.edit(
                    embed=center_embed(self.bot.settings.vip_price_robux),
                    view=CenterView(center_cog),
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            return
        if not checked:
            return
        try:
            await channel.send(
                embed=center_embed(self.bot.settings.vip_price_robux),
                view=CenterView(center_cog),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self.bot.user is None:
            return

        for guild in self.bot.guilds:
            if guild.id in self._checked_guilds:
                continue
            self._checked_guilds.add(guild.id)
            channel = discord.utils.get(guild.text_channels, name=CENTER_CHANNEL)
            if channel is not None:
                await self._publish_or_update(channel)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CenterAutoPostCog(bot))
