from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.catalog import FORMATIONS, INVITE_REWARDS
from aidebot.member_experience import invite_progress, progress_bar, recommend_next_action
from aidebot.progression import community_level, profile_badges


def _catalogue_text(price_robux: int) -> str:
    lines: list[str] = []
    for data in FORMATIONS.values():
        access = f"{price_robux} Robux • validation staff" if data["vip"] else "1 invitation valide"
        lines.append(
            f"**{data['title']}**\n"
            f"{data.get('difficulty', 'Tous niveaux')} • {data.get('duration', 'Durée variable')} • {access}\n"
            f"{data['description']}"
        )
    return "\n\n".join(lines)[:3900]


async def _profile_embed(bot: commands.Bot, guild: discord.Guild, member: discord.Member) -> discord.Embed:
    row = await bot.db.profile(guild.id, member.id)
    average = row["rating_sum"] / row["reviews_count"] if row["reviews_count"] else 0
    badges = profile_badges(
        reputation=row["reputation"],
        helped=row["helped_count"],
        trainings=row["trainings_completed"],
        reviews=row["reviews_count"],
        average=average,
    )
    title, advice = recommend_next_action(
        credits=await bot.db.invite_credits(guild.id, member.id),
        reputation=row["reputation"],
        helped=row["helped_count"],
        trainings=row["trainings_completed"],
        helper_available=bool(row["helper_available"]),
    )
    description = (
        f"**Niveau :** {community_level(row['reputation'])}\n"
        f"**Réputation :** {row['reputation']}\n"
        f"**Aides terminées :** {row['helped_count']}\n"
        f"**Formations terminées :** {row['trainings_completed']}\n"
        f"**Note :** {average:.1f}/5 ({row['reviews_count']} avis)\n"
        f"**Compétences :** {row['skills'] or 'Aucune renseignée'}\n"
        f"**Badges :** {' • '.join(badges)}\n\n"
        f"**Prochaine étape — {title}**\n{advice}"
    )
    return discord.Embed(title=f"Mon espace — {member.display_name}", description=description, color=0x3498DB)


class MemberHubView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Formations", style=discord.ButtonStyle.primary, custom_id="aidebot:hub:formations")
    async def formations(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Catalogue des formations",
                description=_catalogue_text(self.bot.settings.vip_price_robux),
                color=0x5865F2,
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="J’ai besoin d’aide", style=discord.ButtonStyle.success, custom_id="aidebot:hub:help")
    async def help(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Obtenir de l’aide",
                description=(
                    "**1.** Essaie `/chercher question:...` pour une réponse immédiate.\n"
                    "**2.** Si ça ne suffit pas, utilise `/aide demander question:...`.\n"
                    "**3.** Pour un parcours complet, choisis une formation dans `#🎓・formations`.\n\n"
                    "Ne partage jamais de token, mot de passe ou code de récupération."
                ),
                color=0x57F287,
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="Mon profil", style=discord.ButtonStyle.secondary, custom_id="aidebot:hub:profile")
    async def profile(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(
            embed=await _profile_embed(self.bot, interaction.guild, interaction.user),
            ephemeral=True,
        )

    @discord.ui.button(label="Récompenses", style=discord.ButtonStyle.secondary, custom_id="aidebot:hub:rewards")
    async def rewards(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild:
            return
        credits = await self.bot.db.invite_credits(interaction.guild.id, interaction.user.id)
        total = await self.bot.db.validated_invites(interaction.guild.id, interaction.user.id)
        state = invite_progress(total, credits)
        lines = [f"• **{threshold}** invitation(s) → {label}" for threshold, label in INVITE_REWARDS]
        if state.next_threshold:
            progress = progress_bar(total, state.next_threshold)
            next_line = f"\n**Prochain palier :** {state.next_reward}\n`{progress}` {total}/{state.next_threshold} — encore {state.remaining}"
        else:
            next_line = "\n**Tous les paliers actuels sont débloqués.**"
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Invitations et récompenses",
                description=f"Crédits formation disponibles : **{credits}**\nInvitations validées : **{total}**\n\n" + "\n".join(lines) + next_line,
                color=0xF1C40F,
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="Aider la communauté", style=discord.ButtonStyle.secondary, custom_id="aidebot:hub:contribute")
    async def contribute(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Devenir utile à la communauté",
                description=(
                    "Tu peux progresser sans être staff : fais `/challenge liste`, complète tes compétences et aide les nouveaux.\n\n"
                    "Pour rejoindre officiellement l’équipe : `/candidature`.\n"
                    "Une fois Helper : `/aide competence`, puis `/aide disponible actif:True`.\n"
                    "Les aides validées alimentent ton profil et ta réputation."
                ),
                color=0x57F287,
            ),
            ephemeral=True,
        )


class MemberExperienceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(MemberHubView(self.bot))

    @app_commands.command(name="commencer", description="Voir quoi faire maintenant selon ta progression")
    async def commencer(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(
            embed=await _profile_embed(self.bot, interaction.guild, interaction.user),
            view=MemberHubView(self.bot),
            ephemeral=True,
        )

    @app_commands.command(name="centre", description="Ouvrir le centre interactif Aide Bot")
    async def centre(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Aide Bot — Centre membre",
                description="Apprendre, demander de l’aide, suivre ta progression, débloquer des récompenses ou commencer à aider les autres.",
                color=0x5865F2,
            ),
            view=MemberHubView(self.bot),
            ephemeral=True,
        )

    @app_commands.command(name="parcours", description="Voir le détail d’une formation ou extension")
    async def parcours(self, interaction: discord.Interaction, formation: str) -> None:
        key = formation.casefold().strip()
        data = FORMATIONS.get(key)
        if not data:
            return await interaction.response.send_message(
                "Parcours inconnu. Clés disponibles : " + ", ".join(f"`{name}`" for name in FORMATIONS),
                ephemeral=True,
            )
        access = f"{self.bot.settings.vip_price_robux} Robux • confirmation staff" if data["vip"] else "1 invitation valide"
        steps = "\n".join(f"**{idx}.** {step}" for idx, step in enumerate(data["steps"], 1))
        await interaction.response.send_message(
            embed=discord.Embed(
                title=data["title"],
                description=(
                    f"{data['description']}\n\n"
                    f"**Niveau :** {data.get('difficulty', 'Tous niveaux')}\n"
                    f"**Durée indicative :** {data.get('duration', 'Variable')}\n"
                    f"**Accès :** {access}\n\n"
                    f"**Programme**\n{steps}"
                ),
                color=0xEB459E if data["vip"] else 0x5865F2,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="recompenses", description="Voir tes crédits, invitations et prochains paliers")
    async def recompenses(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        credits = await self.bot.db.invite_credits(interaction.guild.id, interaction.user.id)
        total = await self.bot.db.validated_invites(interaction.guild.id, interaction.user.id)
        state = invite_progress(total, credits)
        if state.next_threshold:
            detail = f"Prochain palier : **{state.next_reward}** dans **{state.remaining}** invitation(s)."
        else:
            detail = "Tous les paliers actuels sont débloqués."
        await interaction.response.send_message(
            f"Crédits disponibles : **{credits}** • Invitations validées : **{total}**\n{detail}",
            ephemeral=True,
        )

    @app_commands.command(name="certificat", description="Afficher ton certificat Aide Bot si tu as terminé une formation")
    async def certificat(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        row = await self.bot.db.profile(interaction.guild.id, interaction.user.id)
        completed = int(row["trainings_completed"])
        if completed <= 0:
            return await interaction.response.send_message(
                "Tu dois terminer au moins une formation avant d’obtenir ton certificat Aide Bot.",
                ephemeral=True,
            )
        e = discord.Embed(
            title="Certificat de progression — Aide Bot",
            description=(
                f"**{interaction.user.display_name}** a terminé **{completed} formation(s)** sur Aide Bot.\n\n"
                f"Niveau communauté : **{community_level(row['reputation'])}**\n"
                f"Réputation : **{row['reputation']}**\n\n"
                "Ce certificat représente la progression enregistrée sur la communauté Aide Bot et ne constitue pas un diplôme officiel."
            ),
            color=0x3498DB,
        )
        e.set_footer(text=f"Membre Discord : {interaction.user.id}")
        await interaction.response.send_message(embed=e)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MemberExperienceCog(bot))
