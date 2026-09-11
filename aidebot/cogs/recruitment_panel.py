from __future__ import annotations

import re

import discord
from discord.ext import commands

from aidebot.experience_content import BANNER_URL
from aidebot.permissions import can


RECRUITMENT_TITLE = "Rejoindre l’équipe Aide Bot"
APPLICATION_ROLE_NAMES = {
    "helper": "🤝・Helper",
    "trainer": "🎓・Formateur",
}


def recruitment_embed() -> discord.Embed:
    e = discord.Embed(
        title=RECRUITMENT_TITLE,
        description=(
            "Le recrutement fonctionne maintenant avec un **vrai formulaire**, pas avec une commande à taper. "
            "Choisis le poste que tu veux rejoindre puis réponds aux questions sur ton expérience, tes compétences, ta motivation, "
            "ta manière d’aider quelqu’un et tes disponibilités.\n\n"
            "Une candidature complète arrive directement dans l’espace staff avec des boutons **Accepter** et **Refuser**. "
            "Si elle est acceptée, le rôle correspondant est attribué automatiquement."
        ),
        color=0x57F287,
    )
    e.add_field(
        name="Helper",
        value=(
            "Pour les personnes qui aiment diagnostiquer un problème, expliquer calmement, guider étape par étape et aider les membres "
            "sur Discord, permissions, configuration et problèmes courants."
        ),
        inline=True,
    )
    e.add_field(
        name="Formateur",
        value=(
            "Pour les personnes capables de suivre un membre sur plusieurs étapes, donner des exercices, vérifier les acquis et mener "
            "une formation ou un accompagnement jusqu’au résultat final."
        ),
        inline=True,
    )
    e.add_field(
        name="Ce que nous évaluons",
        value=(
            "Qualité des explications • patience • connaissances réelles • sécurité • capacité à ne jamais demander de secrets • "
            "disponibilité • réponse au mini-cas pratique."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Candidature complète • Traitement par boutons dans l’espace staff")
    return e


class DetailedApplicationModal(discord.ui.Modal):
    experience = discord.ui.TextInput(
        label="Ton expérience",
        placeholder="Depuis combien de temps ? Quels serveurs/bots/projets ?",
        style=discord.TextStyle.paragraph,
        min_length=30,
        max_length=700,
    )
    skills = discord.ui.TextInput(
        label="Tes compétences principales",
        placeholder="Permissions, modération, bots, sécurité, Python...",
        style=discord.TextStyle.paragraph,
        min_length=15,
        max_length=450,
    )
    motivation = discord.ui.TextInput(
        label="Pourquoi veux-tu rejoindre l’équipe ?",
        placeholder="Explique ce que tu veux apporter aux membres",
        style=discord.TextStyle.paragraph,
        min_length=30,
        max_length=600,
    )
    scenario = discord.ui.TextInput(
        label="Mini-cas pratique",
        placeholder="Un membre dit « mon bot n’a pas la permission ». Comment tu l’aides ?",
        style=discord.TextStyle.paragraph,
        min_length=40,
        max_length=700,
    )
    availability = discord.ui.TextInput(
        label="Tes disponibilités",
        placeholder="Ex: lundi-vendredi 18h-22h, week-end 14h-00h",
        min_length=5,
        max_length=180,
    )

    def __init__(self, bot: commands.Bot, target_role: str) -> None:
        label = "Helper" if target_role == "helper" else "Formateur"
        super().__init__(title=f"Candidature — {label}")
        self.bot = bot
        self.target_role = target_role
        self.role_label = label

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        combined_experience = (
            f"EXPÉRIENCE\n{str(self.experience).strip()}\n\n"
            f"MOTIVATION\n{str(self.motivation).strip()}\n\n"
            f"CAS PRATIQUE\n{str(self.scenario).strip()}"
        )
        application_id = await self.bot.db.create_application(
            interaction.guild.id,
            interaction.user.id,
            self.target_role,
            combined_experience,
            str(self.skills).strip(),
            str(self.availability).strip(),
        )
        if application_id is None:
            return await interaction.response.send_message(
                "Tu as déjà une candidature en attente. Attends qu’elle soit traitée avant d’en envoyer une autre.",
                ephemeral=True,
            )

        staff = discord.utils.get(interaction.guild.text_channels, name="📋・staff")
        if staff is None:
            return await interaction.response.send_message(
                f"Candidature **#{application_id}** enregistrée, mais le salon staff est introuvable. Préviens la Direction.",
                ephemeral=True,
            )

        e = discord.Embed(
            title=f"Candidature #{application_id} — {self.role_label}",
            description=f"Candidat : {interaction.user.mention}",
            color=0x57F287,
        )
        e.add_field(name="Expérience", value=str(self.experience)[:1024], inline=False)
        e.add_field(name="Compétences", value=str(self.skills)[:1024], inline=False)
        e.add_field(name="Motivation", value=str(self.motivation)[:1024], inline=False)
        e.add_field(name="Mini-cas pratique", value=str(self.scenario)[:1024], inline=False)
        e.add_field(name="Disponibilités", value=str(self.availability)[:1024], inline=False)
        e.add_field(
            name="Décision",
            value="Un Responsable/Direction utilise les boutons **Accepter** ou **Refuser** ci-dessous. Aucun slash command n’est nécessaire.",
            inline=False,
        )
        e.set_footer(text=f"Aide Bot • Candidature #{application_id} • en attente")
        await staff.send(
            embed=e,
            view=StaffApplicationReviewView(self.bot),
            allowed_mentions=discord.AllowedMentions.none(),
        )

        logs = discord.utils.get(interaction.guild.text_channels, name="🧾・logs")
        if logs:
            try:
                await logs.send(
                    embed=discord.Embed(
                        title="Candidature reçue",
                        description=f"#{application_id} • {interaction.user.mention} • {self.role_label}",
                        color=0x2B2D31,
                    ),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass
        await interaction.response.send_message(
            f"Candidature **#{application_id}** envoyée pour le poste **{self.role_label}**. Le staff la traitera depuis son panneau.",
            ephemeral=True,
        )


def _application_id_from_message(message: discord.Message | None) -> int | None:
    if message is None or not message.embeds:
        return None
    title = message.embeds[0].title or ""
    match = re.search(r"Candidature #(\d+)", title)
    return int(match.group(1)) if match else None


async def _mark_reviewed(message: discord.Message | None, verdict: str, reviewer: discord.Member, reason: str = "") -> None:
    if message is None or not message.embeds:
        return
    original = message.embeds[0]
    color = 0x57F287 if verdict == "acceptée" else 0xED4245
    e = discord.Embed(
        title=original.title,
        description=(original.description or "") + f"\n\n**Décision : {verdict.upper()}** par {reviewer.mention}",
        color=color,
    )
    for field in original.fields:
        if field.name == "Décision":
            continue
        e.add_field(name=field.name, value=field.value, inline=field.inline)
    if reason.strip():
        e.add_field(name="Raison / note staff", value=reason[:1024], inline=False)
    e.set_footer(text=f"Aide Bot • Candidature traitée • {verdict}")
    try:
        await message.edit(embed=e, view=None)
    except discord.HTTPException:
        pass


class RejectApplicationModal(discord.ui.Modal, title="Refuser la candidature"):
    reason = discord.ui.TextInput(
        label="Raison du refus",
        placeholder="Explique clairement la raison ou ce qui doit être amélioré",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=700,
    )

    def __init__(self, bot: commands.Bot, application_id: int, channel_id: int, message_id: int) -> None:
        super().__init__()
        self.bot = bot
        self.application_id = application_id
        self.channel_id = channel_id
        self.message_id = message_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "applications.review"):
            return await interaction.response.send_message("Tu n’as pas la permission de traiter cette candidature.", ephemeral=True)
        row = await self.bot.db.application(self.application_id)
        if not row or row["guild_id"] != interaction.guild.id or row["status"] != "pending":
            return await interaction.response.send_message("Cette candidature est introuvable ou déjà traitée.", ephemeral=True)
        changed = await self.bot.db.resolve_application(self.application_id, interaction.user.id, False, str(self.reason))
        if not changed:
            return await interaction.response.send_message("La candidature a été traitée entre-temps.", ephemeral=True)
        member = interaction.guild.get_member(row["user_id"])
        if member:
            try:
                await member.send(
                    f"Ta candidature **#{self.application_id}** a été **refusée**.\nRaison : {str(self.reason)[:600]}"
                )
            except discord.HTTPException:
                pass
        channel = interaction.guild.get_channel(self.channel_id)
        message = channel.get_partial_message(self.message_id) if isinstance(channel, discord.TextChannel) else None
        await _mark_reviewed(message, "refusée", interaction.user, str(self.reason))
        await interaction.response.send_message(f"Candidature **#{self.application_id} refusée**.", ephemeral=True)


class StaffApplicationReviewView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success, custom_id="aidebot:application:accept")
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "applications.review"):
            return await interaction.response.send_message("Tu n’as pas la permission de traiter cette candidature.", ephemeral=True)
        application_id = _application_id_from_message(interaction.message)
        if application_id is None:
            return await interaction.response.send_message("Impossible d’identifier cette candidature.", ephemeral=True)
        row = await self.bot.db.application(application_id)
        if not row or row["guild_id"] != interaction.guild.id or row["status"] != "pending":
            return await interaction.response.send_message("Cette candidature est introuvable ou déjà traitée.", ephemeral=True)
        member = interaction.guild.get_member(row["user_id"])
        role_name = APPLICATION_ROLE_NAMES.get(row["target_role"])
        role = discord.utils.get(interaction.guild.roles, name=role_name) if role_name else None
        if member is None:
            return await interaction.response.send_message("Le candidat n’est plus sur le serveur.", ephemeral=True)
        if role is None:
            return await interaction.response.send_message("Le rôle cible est absent. Relance `/setup`.", ephemeral=True)
        me = interaction.guild.me
        if me is None or role.managed or role >= me.top_role:
            return await interaction.response.send_message("Le bot ne peut pas attribuer ce rôle. Vérifie sa hiérarchie.", ephemeral=True)

        claimed = await self.bot.db.begin_application_acceptance(application_id, interaction.guild.id, interaction.user.id, "Acceptée depuis le panneau")
        if claimed is None:
            return await interaction.response.send_message("La candidature a été traitée entre-temps.", ephemeral=True)
        had_role = role in member.roles
        try:
            if not had_role:
                await member.add_roles(role, reason=f"Candidature Aide Bot #{application_id} acceptée")
        except (discord.Forbidden, discord.HTTPException):
            await self.bot.db.release_application_acceptance(application_id, interaction.guild.id)
            return await interaction.response.send_message("Discord refuse l’attribution du rôle. La candidature reste en attente.", ephemeral=True)
        finalized = await self.bot.db.finish_application_acceptance(application_id, interaction.guild.id)
        if not finalized:
            if not had_role:
                try:
                    await member.remove_roles(role, reason=f"Rollback candidature Aide Bot #{application_id}")
                except discord.HTTPException:
                    pass
            await self.bot.db.release_application_acceptance(application_id, interaction.guild.id)
            return await interaction.response.send_message("La candidature n’a pas pu être finalisée.", ephemeral=True)

        try:
            await member.send(f"Ta candidature **#{application_id}** a été **acceptée**. Le rôle **{role.name}** t’a été attribué.")
        except discord.HTTPException:
            pass
        await _mark_reviewed(interaction.message, "acceptée", interaction.user)
        await interaction.response.send_message(f"Candidature **#{application_id} acceptée** et rôle attribué.", ephemeral=True)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger, custom_id="aidebot:application:reject")
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member) or interaction.message is None:
            return
        if not can(interaction.user, "applications.review"):
            return await interaction.response.send_message("Tu n’as pas la permission de traiter cette candidature.", ephemeral=True)
        application_id = _application_id_from_message(interaction.message)
        if application_id is None:
            return await interaction.response.send_message("Impossible d’identifier cette candidature.", ephemeral=True)
        await interaction.response.send_modal(
            RejectApplicationModal(self.bot, application_id, interaction.channel_id, interaction.message.id)
        )


class RecruitmentView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Candidater Helper", style=discord.ButtonStyle.primary, custom_id="aidebot:recruitment:helper")
    async def helper(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(DetailedApplicationModal(self.bot, "helper"))

    @discord.ui.button(label="Candidater Formateur", style=discord.ButtonStyle.success, custom_id="aidebot:recruitment:trainer")
    async def trainer(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(DetailedApplicationModal(self.bot, "trainer"))


class RecruitmentPanelCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(RecruitmentView(self.bot))
        self.bot.add_view(StaffApplicationReviewView(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RecruitmentPanelCog(bot))
