import asyncio
from types import SimpleNamespace

import discord
from discord.ext import commands


def test_rich_center_replaces_legacy_center_without_registration_collision():
    async def run() -> None:
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.none(), help_command=None)
        bot.settings = SimpleNamespace(vip_price_robux=500)
        try:
            await bot.load_extension("aidebot.cogs.member_experience")
            legacy = bot.tree.get_command("centre")
            assert legacy is not None

            await bot.load_extension("aidebot.cogs.command_cleanup")
            assert bot.tree.get_command("centre") is None

            await bot.load_extension("aidebot.cogs.center")
            rich = bot.tree.get_command("centre")
            assert rich is not None
            assert rich.callback.__module__ == "aidebot.cogs.center"
        finally:
            await bot.close()

    asyncio.run(run())
