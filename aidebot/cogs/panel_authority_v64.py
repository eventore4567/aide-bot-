from __future__ import annotations

import asyncio
from collections import defaultdict

import discord
from discord.ext import commands

from aidebot.cogs.assistant_guardian_v52 import GUARDIAN_TITLE
from aidebot.cogs.enterprise_academy_v61 import STAFF_CHANNEL

CANONICAL_STAFF_TITLE = "Aide Bot — Outils avancés"


def _embed_text(embed: discord.Embed) -> str:
    parts = [embed.title or "", embed.description or ""]
    parts.extend(f"{field.name} {field.value}" for field in embed.fields)
    if embed.footer and embed.footer.text:
        parts.append(embed.footer.text)
    return " ".join(parts)


def is_latest_staff_embed(embed: discord.Embed) -> bool:
    """Recognise the V61+ enterprise staff surface, not older V58/V59/V60 variants."""
    if (embed.title or "") != CANONICAL_STAFF_TITLE:
        return False
    text = _embed_text(embed)
    return "Academy QA" in text and "Audit 360" in text and "Role Studio" in text


def is_legacy_guardian_embed(embed: discord.Embed) -> bool:
    return (embed.title or "") == GUARDIAN_TITLE


class PanelAuthorityV64Cog(commands.Cog):
    """Keeps one authoritative staff panel after all historical compatibility layers.

    Older V52/V58/V59/V60 cogs are still loaded because their engines are used by
    newer workflows. Some of them also contain historical on_ready publishers.
    V64 is the final reconciliation layer: it removes the obsolete standalone
    Guardian panel and restores the latest Enterprise staff surface whenever an
    older listener rewrites it.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._stabilizers: dict[int, asyncio.Task] = {}

    async def _cleanup_staff(self, channel: discord.TextChannel) -> None:
        if self.bot.user is None:
            return

        canonical: list[discord.Message] = []
        try:
            async for message in channel.history(limit=120):
                if message.author.id != self.bot.user.id or not message.embeds:
                    continue
                embed = message.embeds[0]
                if is_legacy_guardian_embed(embed):
                    try:
                        await message.delete()
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                    continue
                if (embed.title or "") == CANONICAL_STAFF_TITLE:
                    canonical.append(message)
        except (discord.Forbidden, discord.HTTPException):
            return

        # A single persistent staff control surface is intentional. Keep the newest
        # canonical message and remove accidental duplicates left by old races.
        for duplicate in canonical[1:]:
            try:
                await duplicate.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def reconcile_guild(self, guild: discord.Guild) -> None:
        async with self._locks[guild.id]:
            channel = discord.utils.get(guild.text_channels, name=STAFF_CHANNEL)
            if channel is None:
                return

            await self._cleanup_staff(channel)

            academy = self.bot.get_cog("EnterpriseAcademyV61Cog")
            if academy is not None:
                # EnterpriseAcademyV61Cog.publish uses the newest shared V60 tools
                # menu plus Academy QA. V63 only patches content copy, so this is
                # the authoritative staff surface for the current product.
                await academy.publish(guild)

            await self._cleanup_staff(channel)

    async def _stabilize(self, guild: discord.Guild) -> None:
        # Historical listeners are dispatched as independent tasks on reconnect.
        # Reconcile more than once so a slower legacy publisher cannot win later.
        for delay in (0.0, 1.5, 6.0, 20.0):
            if delay:
                await asyncio.sleep(delay)
            await self.reconcile_guild(guild)

    def _schedule_stabilize(self, guild: discord.Guild) -> None:
        previous = self._stabilizers.get(guild.id)
        if previous and not previous.done():
            previous.cancel()
        self._stabilizers[guild.id] = asyncio.create_task(self._stabilize(guild))

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            self._schedule_stabilize(guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if isinstance(channel, discord.TextChannel) and channel.name == STAFF_CHANNEL:
            self._schedule_stabilize(channel.guild)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if self.bot.user is None or message.author.id != self.bot.user.id:
            return
        if not isinstance(message.channel, discord.TextChannel) or message.channel.name != STAFF_CHANNEL:
            return
        if not message.embeds:
            return
        embed = message.embeds[0]
        if is_legacy_guardian_embed(embed):
            try:
                await message.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass
            return
        if (embed.title or "") == CANONICAL_STAFF_TITLE and not is_latest_staff_embed(embed):
            self._schedule_stabilize(message.guild)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if self.bot.user is None or after.author.id != self.bot.user.id:
            return
        if not isinstance(after.channel, discord.TextChannel) or after.channel.name != STAFF_CHANNEL:
            return
        if not after.embeds:
            return
        embed = after.embeds[0]
        if is_legacy_guardian_embed(embed):
            try:
                await after.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass
            return
        if (embed.title or "") == CANONICAL_STAFF_TITLE and not is_latest_staff_embed(embed):
            self._schedule_stabilize(after.guild)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PanelAuthorityV64Cog(bot))
