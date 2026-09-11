from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

import discord
from discord.ext import commands


def matching_ticket_channels(request_id: int, channels: Iterable[Any]) -> list[Any]:
    """Return channels whose canonical ticket prefix matches one request id."""
    prefix = f"ticket-{int(request_id)}-"
    return [channel for channel in channels if str(getattr(channel, "name", "")).startswith(prefix)]


class TicketRecoveryCog(commands.Cog):
    """Reconcile the DB link when Discord created a ticket before a crash."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._lock = asyncio.Lock()

    async def _log(self, guild: discord.Guild, title: str, description: str) -> None:
        training = self.bot.get_cog("TrainingCog")
        if training is not None:
            await training.log_action(guild, title, description)
            return
        channel = discord.utils.get(guild.text_channels, name="🧾・logs")
        if channel:
            try:
                await channel.send(
                    embed=discord.Embed(title=title, description=description, color=0x2B2D31),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass

    async def reconcile_guild(self, guild: discord.Guild) -> tuple[int, int]:
        recovered = 0
        ambiguous = 0
        rows = await self.bot.db.active_requests_for_guild(guild.id)
        for row in rows:
            if row["channel_id"]:
                continue
            matches = matching_ticket_channels(int(row["id"]), guild.text_channels)
            if len(matches) == 1:
                channel = matches[0]
                await self.bot.db.set_request_channel(int(row["id"]), channel.id)
                recovered += 1
                await self._log(
                    guild,
                    "Ticket récupéré après redémarrage",
                    f"Demande #{row['id']} reliée automatiquement à {channel.mention}.",
                )
            elif len(matches) > 1:
                ambiguous += 1
                await self._log(
                    guild,
                    "Récupération ticket ambiguë",
                    f"Demande #{row['id']} : {len(matches)} salons correspondent au même identifiant. Aucune liaison automatique n'a été appliquée.",
                )
        return recovered, ambiguous

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # on_ready can fire again after a Discord reconnect. Serializing the
        # scan keeps the reconciliation idempotent even during reconnects.
        async with self._lock:
            for guild in self.bot.guilds:
                try:
                    await self.reconcile_guild(guild)
                except Exception:
                    # Never prevent the bot from becoming ready because a
                    # reconciliation check failed. Preflight/audit will still
                    # expose any unresolved request.
                    continue


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketRecoveryCog(bot))
