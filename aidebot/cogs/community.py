from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.catalog import RESOURCES
from aidebot.permissions import can


class ApplicationModal(discord.ui.Modal, title="Candidature Aide Bot"):
    experience = discord.ui.TextInput(label="Ton expérience", style=discord.TextStyle.paragraph, max_length=700)
    skills = discord.ui.TextInput(label="Tes spécialités", placeholder="Permissions, bots, sécurité...", max_length=200)
    availability = discord.ui.TextInput(label="Tes disponibilités", max_length=150)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        staff = discord.utils.get(interaction.guild.text_channels, name="📋・staff")
        if not staff:
            return await interaction.response.send_message("Salon staff introuvable.", ephemeral=True)
        e = discord.Embed(title="Nouvelle candidature Helper/Formateur", color=0x57F287)
        e.add_field(name="Candidat", value=interaction.user.mention, inline=False)
        e.add_field(name="Expérience", value=str(self.experience), inline=False)
        e.add_field(name="Spécialités", value=str(self.skills), inline=False)
        e.add_field(name="Disponibilités", value=str(self.availability), inline=False)
        await staff.send(embed=e)
        logs = discord.utils.get(interaction.guild.text_channels, name="🧾・logs")
        if logs:
            await logs.send(embed=discord.Embed(title="Candidature reçue", description=f"{interaction.user.mention} a envoyé une candidature.", color=0x2B2D31))
        await interaction.response.send_message("Candidature envoyée.", ephemeral=True)


class CommunityCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    aide = app_commands.Group(name="aide", description="Entraide communautaire")

    @aide.command(name="demander", description="Demander de l’aide à la communauté")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def demander(self, interaction: discord.Interaction, question: str) -> None:
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de tickets indisponible.", ephemeral=True)
        await training.create_request_channel(
            interaction,
            "community_help",
            level="Communauté",
            objective=question,
            availability="Dès qu’un Helper est disponible",
            budget="Gratuit",
            status="open",
            payment_status="not_required",
            invite_used=False,
        )

    @aide.command(name="disponible", description="Activer ou désactiver ton statut Helper disponible")
    async def disponible(self, interaction: discord.Interaction, actif: bool) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "help.claim"):
            return await interaction.response.send_message("Il faut être Helper/Formateur pour utiliser ce statut.", ephemeral=True)
        await self.bot.db.set_helper_available(interaction.guild.id, interaction.user.id, actif)
        await interaction.response.send_message(f"Statut Helper : **{'disponible' if actif else 'indisponible'}**.", ephemeral=True)

    @aide.command(name="competence", description="Ajouter une compétence à ton profil")
    async def competence(self, interaction: discord.Interaction, competence: str) -> None:
        if not interaction.guild:
            return
        await self.bot.db.add_skill(interaction.guild.id, interaction.user.id, competence)
        await interaction.response.send_message(f"Compétence ajoutée : **{competence}**.", ephemeral=True)

    @app_commands.command(name="profil", description="Voir un profil Aide Bot")
    async def profil(self, interaction: discord.Interaction, membre: discord.Member | None = None) -> None:
        if not interaction.guild:
            return
        target = membre or interaction.user
        row = await self.bot.db.profile(interaction.guild.id, target.id)
        average = (row["rating_sum"] / row["reviews_count"]) if row["reviews_count"] else 0
        desc = (
            f"**Réputation :** {row['reputation']}\n"
            f"**Personnes aidées :** {row['helped_count']}\n"
            f"**Formations terminées :** {row['trainings_completed']}\n"
            f"**Note :** {average:.1f}/5 ({row['reviews_count']} avis)\n"
            f"**Disponible :** {'Oui' if row['helper_available'] else 'Non'}\n"
            f"**Compétences :** {row['skills'] or 'Aucune'}"
        )
        await interaction.response.send_message(embed=discord.Embed(title=f"Profil — {target.display_name}", description=desc, color=0x3498DB))

    @app_commands.command(name="ressource", description="Voir une ressource rapide")
    async def ressource(self, interaction: discord.Interaction, nom: str) -> None:
        value = RESOURCES.get(nom.lower())
        if not value:
            return await interaction.response.send_message(f"Ressources disponibles : {', '.join(RESOURCES)}", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(title=f"Ressource — {nom}", description=value, color=0x5865F2), ephemeral=True)

    @app_commands.command(name="candidature", description="Candidater comme Helper ou Formateur")
    @app_commands.checks.cooldown(1, 600.0, key=lambda i: (i.guild_id, i.user.id))
    async def candidature(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ApplicationModal())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CommunityCog(bot))
