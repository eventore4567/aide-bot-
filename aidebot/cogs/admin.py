from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.audit import dangerous_permissions, format_permission_names
from aidebot.blueprint import ROLE_SPECS
from aidebot.payments import PAYMENT_LABELS, payment_transition_error
from aidebot.permissions import CAPABILITIES, can, decide


APPLICATION_ROLES = {
    "helper": "🤝・Helper",
    "trainer": "🎓・Formateur",
}


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _audit(self, guild: discord.Guild, title: str, description: str) -> None:
        channel = discord.utils.get(guild.text_channels, name="🧾・logs")
        if channel:
            try:
                await channel.send(
                    embed=discord.Embed(title=title, description=description, color=0x2B2D31),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass

    @app_commands.command(name="permissions_test", description="Diagnostiquer les permissions Aide Bot d’un membre")
    async def permissions_test(self, interaction: discord.Interaction, membre: discord.Member) -> None:
        if not isinstance(interaction.user, discord.Member) or not can(interaction.user, "config.manage"):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)
        lines = []
        for capability in CAPABILITIES:
            d = decide(membre, capability)
            icon = "✅" if d.allowed else "❌"
            roles = ", ".join(d.allowed_roles) if d.allowed_roles else "aucun"
            lines.append(f"{icon} `{capability}` — {d.reason}\nRôles : {roles}")
        await interaction.response.send_message(
            embed=discord.Embed(title=f"Permissions — {membre.display_name}", description="\n\n".join(lines), color=0x5865F2),
            ephemeral=True,
        )

    @app_commands.command(name="audit_serveur", description="Auditer les permissions et la structure sensible du serveur")
    async def audit_serveur(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "audit.run"):
            return await interaction.response.send_message("Accès refusé : `audit.run` requis.", ephemeral=True)

        guild = interaction.guild
        findings: list[str] = []

        everyone_risks = dangerous_permissions(guild.default_role.permissions)
        if everyone_risks:
            findings.append("🔴 **@everyone** possède : " + format_permission_names(everyone_risks))

        risky_roles = []
        for role in guild.roles:
            if role.is_default() or role.managed:
                continue
            risks = dangerous_permissions(role.permissions)
            if risks:
                risky_roles.append(f"• {role.mention} — {format_permission_names(risks)}")
        if risky_roles:
            findings.append("🟠 **Rôles sensibles**\n" + "\n".join(risky_roles[:8]))
            if len(risky_roles) > 8:
                findings.append(f"🟠 **{len(risky_roles) - 8} autre(s) rôle(s) sensible(s)** non affiché(s).")

        staff_category = discord.utils.get(guild.categories, name="━━ STAFF ━━")
        if staff_category is None:
            findings.append("🟡 Catégorie staff Aide Bot absente.")
        elif staff_category.permissions_for(guild.default_role).view_channel:
            findings.append("🔴 La catégorie **STAFF** est visible par `@everyone`.")

        logs = discord.utils.get(guild.text_channels, name="🧾・logs")
        if logs is None:
            findings.append("🟡 Salon de logs Aide Bot absent.")

        me = guild.me
        if me:
            canonical_names = {name for name, _, _ in ROLE_SPECS if name not in {"👤・Membre"}}
            blocked = [role.mention for role in guild.roles if role.name in canonical_names and role >= me.top_role]
            if blocked:
                findings.append("🔴 Le bot ne peut pas gérer ces rôles car ils sont au-dessus ou au même niveau que lui : " + ", ".join(blocked[:8]))

        description = "\n\n".join(findings) if findings else "✅ Aucun problème critique détecté par l’audit automatique. Vérifie quand même les cas métiers et les permissions Discord manuellement."
        await interaction.response.send_message(
            embed=discord.Embed(title="Audit sécurité Aide Bot", description=description[:4000], color=0x57F287 if not findings else 0xF1C40F),
            ephemeral=True,
        )

    @app_commands.command(name="paiement_confirmer", description="Confirmer manuellement le paiement du ticket actuel")
    async def paiement_confirmer(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not can(interaction.user, "payment.confirm"):
            return await interaction.response.send_message("Accès refusé : `payment.confirm` requis.", ephemeral=True)
        if not interaction.channel or not interaction.guild:
            return
        req = await self.bot.db.request_by_channel(interaction.channel.id)
        if not req:
            return await interaction.response.send_message("Utilise cette commande dans un ticket.", ephemeral=True)
        if req["payment_status"] == "not_required":
            return await interaction.response.send_message("Ce ticket ne demande pas de paiement.", ephemeral=True)

        changed, previous = await self.bot.db.transition_payment(req["id"], "paid")
        if not changed:
            if previous is None:
                message = "Demande introuvable."
            else:
                message = payment_transition_error(previous, "paid")
            return await interaction.response.send_message(message, ephemeral=True)
        if previous == "paid":
            return await interaction.response.send_message("Ce paiement est déjà confirmé.", ephemeral=True)

        training = self.bot.get_cog("TrainingCog")
        if training:
            await training.log_action(
                interaction.guild,
                "Paiement confirmé",
                f"#{req['id']} • {PAYMENT_LABELS.get(previous or '', previous or '?')} → **Payé** par {interaction.user.mention}",
            )
        await interaction.response.send_message("Paiement marqué **payé**. Le ticket peut maintenant être pris par un Formateur.")

    @app_commands.command(name="candidatures", description="Voir les candidatures Helper/Formateur en attente")
    async def candidatures(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "applications.review"):
            return await interaction.response.send_message("Accès refusé : `applications.review` requis.", ephemeral=True)
        rows = await self.bot.db.pending_applications(interaction.guild.id, 20)
        if not rows:
            return await interaction.response.send_message("Aucune candidature en attente.", ephemeral=True)
        lines = []
        for row in rows:
            label = "Formateur" if row["target_role"] == "trainer" else "Helper"
            lines.append(f"**#{row['id']}** • <@{row['user_id']}> • {label} • {row['skills'] or 'compétences non renseignées'}")
        await interaction.response.send_message(
            embed=discord.Embed(title="Candidatures en attente", description="\n".join(lines)[:4000], color=0xF1C40F),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="candidature_valider", description="Accepter ou refuser une candidature Helper/Formateur")
    @app_commands.describe(id="Identifiant de la candidature", accepte="True pour accepter, False pour refuser", raison="Raison optionnelle")
    async def candidature_valider(self, interaction: discord.Interaction, id: int, accepte: bool, raison: str = "") -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "applications.review"):
            return await interaction.response.send_message("Accès refusé : `applications.review` requis.", ephemeral=True)

        row = await self.bot.db.application(id)
        if not row or row["guild_id"] != interaction.guild.id:
            return await interaction.response.send_message("Candidature introuvable.", ephemeral=True)
        if row["status"] != "pending":
            return await interaction.response.send_message("Cette candidature a déjà été traitée.", ephemeral=True)

        member = interaction.guild.get_member(row["user_id"])
        role_name = APPLICATION_ROLES.get(row["target_role"])
        role = discord.utils.get(interaction.guild.roles, name=role_name) if role_name else None

        if accepte:
            if member is None:
                return await interaction.response.send_message("Le candidat n'est plus sur le serveur.", ephemeral=True)
            if role is None:
                return await interaction.response.send_message("Le rôle cible est introuvable. Relance `/setup` puis réessaie.", ephemeral=True)
            me = interaction.guild.me
            if me is None or role.managed or role >= me.top_role:
                return await interaction.response.send_message(
                    "Le bot ne peut pas attribuer ce rôle. Vérifie sa hiérarchie Discord.",
                    ephemeral=True,
                )
            try:
                await member.add_roles(role, reason=f"Candidature Aide Bot #{id} acceptée")
            except discord.Forbidden:
                return await interaction.response.send_message("Discord refuse l'attribution du rôle. Vérifie les permissions du bot.", ephemeral=True)

        changed = await self.bot.db.resolve_application(id, interaction.user.id, accepte, raison)
        if not changed:
            return await interaction.response.send_message("La candidature a été traitée entre-temps.", ephemeral=True)

        verdict = "acceptée" if accepte else "refusée"
        role_label = "Formateur" if row["target_role"] == "trainer" else "Helper"
        await self._audit(
            interaction.guild,
            "Candidature traitée",
            f"#{id} • {role_label} • {verdict} par {interaction.user.mention} • candidat <@{row['user_id']}>",
        )

        if member:
            try:
                detail = f"\nRaison : {raison[:500]}" if raison.strip() else ""
                await member.send(f"Ta candidature **#{id}** pour devenir **{role_label}** a été **{verdict}**.{detail}")
            except discord.HTTPException:
                pass

        await interaction.response.send_message(f"Candidature **#{id} {verdict}**.", ephemeral=True)

    @app_commands.command(name="staff_stats", description="Voir les statistiques d’un Helper/Formateur")
    async def staff_stats(self, interaction: discord.Interaction, membre: discord.Member) -> None:
        if not interaction.guild:
            return
        row = await self.bot.db.profile(interaction.guild.id, membre.id)
        avg = row["rating_sum"] / row["reviews_count"] if row["reviews_count"] else 0
        desc = (
            f"Réputation : **{row['reputation']}**\n"
            f"Aides : **{row['helped_count']}**\n"
            f"Formations : **{row['trainings_completed']}**\n"
            f"Avis : **{avg:.1f}/5** ({row['reviews_count']})\n"
            f"Disponible : **{'Oui' if row['helper_available'] else 'Non'}**\n"
            f"Compétences : **{row['skills'] or 'Aucune'}**"
        )
        await interaction.response.send_message(
            embed=discord.Embed(title=f"Stats staff — {membre.display_name}", description=desc, color=0x57F287),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
