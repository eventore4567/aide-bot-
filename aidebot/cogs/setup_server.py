from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.blueprint import CATEGORY_SPECS, ROLE_SPECS, role_permissions


class SetupServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setup", description="Configurer Aide Bot sans supprimer les salons/rôles existants")
    async def setup_server(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if interaction.guild.owner_id != interaction.user.id:
            return await interaction.response.send_message("Seul le propriétaire du serveur peut lancer le setup initial.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild

        roles: dict[str, discord.Role] = {}
        for name, color, perm_spec in reversed(ROLE_SPECS):
            role = discord.utils.get(guild.roles, name=name)
            if role is None:
                role = await guild.create_role(name=name, colour=discord.Colour(color), permissions=role_permissions(perm_spec), reason="Setup Aide Bot")
            roles[name] = role

        for category_name, channel_names in CATEGORY_SPECS:
            category = discord.utils.get(guild.categories, name=category_name)
            if category is None:
                overwrites = None
                if category_name == "━━ STAFF ━━":
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        roles["👑・Direction"]: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                        roles["📘・Responsable Formation"]: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    }
                category = await guild.create_category(category_name, overwrites=overwrites, reason="Setup Aide Bot")
            for channel_name in channel_names:
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                if channel is None:
                    overwrites = None
                    if channel_name in {"📢・annonces", "📜・règlement"}:
                        overwrites = {guild.default_role: discord.PermissionOverwrite(send_messages=False, view_channel=True)}
                    await guild.create_text_channel(channel_name, category=category, overwrites=overwrites, reason="Setup Aide Bot")

        bienvenue = discord.utils.get(guild.text_channels, name="👋・bienvenue")
        if bienvenue:
            e = discord.Embed(title="Bienvenue sur Aide Bot", description="Apprends Discord, crée ton serveur ou ton premier bot, demande de l’aide puis aide à ton tour les nouveaux.", color=0x5865F2)
            await bienvenue.send(embed=e)

        formations = discord.utils.get(guild.text_channels, name="🎓・formations")
        training_cog = self.bot.get_cog("TrainingCog")
        if formations and training_cog:
            await training_cog.post_panel(formations)

        recrutement = discord.utils.get(guild.text_channels, name="🧑‍🏫・recrutement")
        if recrutement:
            await recrutement.send(embed=discord.Embed(title="Devenir Helper / Formateur", description="Utilise `/candidature` pour envoyer ton expérience, tes spécialités et tes disponibilités.", color=0x57F287))

        await interaction.followup.send("Setup terminé. Rien d’existant n’a été supprimé. Vérifie ensuite la hiérarchie des rôles et place le rôle du bot au-dessus des rôles qu’il doit gérer.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupServerCog(bot))
