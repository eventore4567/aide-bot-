from __future__ import annotations

import re

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.catalog import RESOURCES
from aidebot.permissions import can
from aidebot.progression import community_level, profile_badges


def _skill_score(question: str, skills: str) -> int:
    text = question.casefold()
    words = {word for word in re.findall(r"[a-zà-ÿ0-9+#.-]{3,}", text)}
    score = 0
    for skill in (item.strip().casefold() for item in skills.split(",")):
        if not skill:
            continue
        if skill in text:
            score += 4
        score += len(words & set(re.findall(r"[a-zà-ÿ0-9+#.-]{3,}", skill)))
    return score


class ApplicationModal(discord.ui.Modal, title="Candidature Aide Bot"):
    target_role = discord.ui.TextInput(label="Rôle souhaité", placeholder="Helper ou Formateur", max_length=20)
    experience = discord.ui.TextInput(label="Ton expérience", style=discord.TextStyle.paragraph, max_length=700)
    skills = discord.ui.TextInput(label="Tes spécialités", placeholder="Permissions, bots, sécurité...", max_length=200)
    availability = discord.ui.TextInput(label="Tes disponibilités", max_length=150)

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return

        requested = str(self.target_role).casefold().strip()
        if requested in {"helper", "aide", "aidant"}:
            target = "helper"
            label = "Helper"
        elif requested in {"formateur", "trainer", "formation"}:
            target = "trainer"
            label = "Formateur"
        else:
            return await interaction.response.send_message(
                "Rôle invalide. Écris exactement **Helper** ou **Formateur**.",
                ephemeral=True,
            )

        application_id = await self.bot.db.create_application(
            interaction.guild.id,
            interaction.user.id,
            target,
            str(self.experience),
            str(self.skills),
            str(self.availability),
        )
        if application_id is None:
            return await interaction.response.send_message(
                "Tu as déjà une candidature en attente. Attends qu'elle soit traitée avant d'en envoyer une autre.",
                ephemeral=True,
            )

        staff = discord.utils.get(interaction.guild.text_channels, name="📋・staff")
        if not staff:
            return await interaction.response.send_message(
                f"Candidature **#{application_id}** enregistrée, mais le salon staff est introuvable. Préviens la Direction.",
                ephemeral=True,
            )

        e = discord.Embed(title=f"Candidature #{application_id} — {label}", color=0x57F287)
        e.add_field(name="Candidat", value=interaction.user.mention, inline=False)
        e.add_field(name="Expérience", value=str(self.experience), inline=False)
        e.add_field(name="Spécialités", value=str(self.skills), inline=False)
        e.add_field(name="Disponibilités", value=str(self.availability), inline=False)
        e.add_field(
            name="Traitement",
            value=f"`/candidature_valider id:{application_id} accepte:True` ou `accepte:False`",
            inline=False,
        )
        await staff.send(embed=e, allowed_mentions=discord.AllowedMentions.none())

        logs = discord.utils.get(interaction.guild.text_channels, name="🧾・logs")
        if logs:
            await logs.send(
                embed=discord.Embed(
                    title="Candidature reçue",
                    description=f"#{application_id} • {interaction.user.mention} • {label}",
                    color=0x2B2D31,
                ),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        await interaction.response.send_message(f"Candidature **#{application_id}** envoyée.", ephemeral=True)


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

    @aide.command(name="trouver_helper", description="Trouver les Helpers disponibles les plus adaptés à ta question")
    async def trouver_helper(self, interaction: discord.Interaction, question: str) -> None:
        if not interaction.guild:
            return
        rows = await self.bot.db.available_helpers(interaction.guild.id, 25)
        candidates: list[tuple[int, int, int, str]] = []
        for row in rows:
            member = interaction.guild.get_member(row["user_id"])
            if member is None:
                continue
            score = _skill_score(question, row["skills"])
            candidates.append((score, int(row["reputation"]), member.id, row["skills"]))
        if not candidates:
            return await interaction.response.send_message(
                "Aucun Helper n'est marqué disponible pour le moment. Tu peux quand même utiliser `/aide demander`.",
                ephemeral=True,
            )
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        lines = []
        for score, reputation, member_id, skills in candidates[:5]:
            member = interaction.guild.get_member(member_id)
            if member is None:
                continue
            match = "très adapté" if score >= 4 else "adapté" if score > 0 else "disponible"
            lines.append(f"**{member.display_name}** — {match} • {reputation} rep\nCompétences : {skills or 'non renseignées'}")
        await interaction.response.send_message(
            embed=discord.Embed(title="Helpers disponibles", description="\n\n".join(lines), color=0x57F287),
            ephemeral=True,
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
        cleaned = competence.casefold().strip()[:60]
        if len(cleaned) < 2:
            return await interaction.response.send_message("Compétence trop courte.", ephemeral=True)
        await self.bot.db.add_skill(interaction.guild.id, interaction.user.id, cleaned)
        await interaction.response.send_message(f"Compétence ajoutée : **{cleaned}**.", ephemeral=True)

    @app_commands.command(name="profil", description="Voir un profil Aide Bot")
    async def profil(self, interaction: discord.Interaction, membre: discord.Member | None = None) -> None:
        if not interaction.guild:
            return
        target = membre or interaction.user
        row = await self.bot.db.profile(interaction.guild.id, target.id)
        average = (row["rating_sum"] / row["reviews_count"]) if row["reviews_count"] else 0
        badges = profile_badges(
            reputation=row["reputation"],
            helped=row["helped_count"],
            trainings=row["trainings_completed"],
            reviews=row["reviews_count"],
            average=average,
        )
        desc = (
            f"**Niveau communauté :** {community_level(row['reputation'])}\n"
            f"**Réputation :** {row['reputation']}\n"
            f"**Personnes aidées :** {row['helped_count']}\n"
            f"**Formations terminées :** {row['trainings_completed']}\n"
            f"**Note :** {average:.1f}/5 ({row['reviews_count']} avis)\n"
            f"**Disponible :** {'Oui' if row['helper_available'] else 'Non'}\n"
            f"**Compétences :** {row['skills'] or 'Aucune'}\n"
            f"**Badges :** {' • '.join(badges)}"
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
        await interaction.response.send_modal(ApplicationModal(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CommunityCog(bot))
