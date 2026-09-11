from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.public_panels import ShopView, TicketEntryView, VideosPanelView, WelcomeView, shop_embed


class StorefrontCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(WelcomeView(self.bot))
        self.bot.add_view(ShopView(self.bot))
        self.bot.add_view(TicketEntryView(self.bot))
        self.bot.add_view(VideosPanelView())

    @app_commands.command(name="buy", description="Ouvrir la boutique Aide Bot")
    async def buy(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            embed=shop_embed(self.bot.settings.vip_price_robux),
            view=ShopView(self.bot),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StorefrontCog(bot))
