from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.config import Settings
from aidebot.db import Database

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aidebot")

EXTENSIONS = (
    "aidebot.cogs.training",
    "aidebot.cogs.community",
    "aidebot.cogs.invites",
    "aidebot.cogs.learning",
    "aidebot.cogs.reminders",
    "aidebot.cogs.health",
    "aidebot.cogs.admin",
    "aidebot.cogs.setup_server",
)


class AideBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.invites = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.settings = settings
        self.db = Database(settings.db_path)

    async def setup_hook(self) -> None:
        await self.db.connect()
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("%s commandes synchronisées sur la guild de test", len(synced))
        else:
            synced = await self.tree.sync()
            log.info("%s commandes globales synchronisées", len(synced))

    async def close(self) -> None:
        await self.db.close()
        await super().close()


async def main() -> None:
    settings = Settings.from_env()
    if not settings.token:
        raise RuntimeError("DISCORD_TOKEN absent. Configure-le dans Railway ou .env avant de démarrer Aide Bot.")

    bot = AideBot(settings)

    @bot.event
    async def on_ready() -> None:
        assert bot.user is not None
        log.info("Connecté en tant que %s (%s)", bot.user, bot.user.id)

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"Tu vas trop vite. Réessaie dans **{error.retry_after:.0f}s**."
        else:
            log.exception("Erreur de commande slash", exc_info=error)
            message = "Une erreur interne est survenue. L’action n’a pas été appliquée."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    try:
        async with bot:
            await bot.start(settings.token)
    except discord.PrivilegedIntentsRequired:
        log.critical(
            "Discord refuse Server Members Intent. Active Developer Portal > Bot > Privileged Gateway Intents > Server Members Intent, puis redémarre le service."
        )
        raise


if __name__ == "__main__":
    asyncio.run(main())
