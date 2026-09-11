from __future__ import annotations

from discord.ext import commands


async def setup(bot: commands.Bot) -> None:
    """Remove the legacy member-hub /centre before the V34 center is loaded.

    The MemberExperience cog stays loaded so its other commands and persistent
    views remain available. Only the old /centre registration is replaced by
    the richer V34 implementation.
    """
    bot.tree.remove_command("centre")
