from __future__ import annotations

import os

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.health import missing_permission_labels, persistence_check
from aidebot.permissions import can
from aidebot.preflight import database_integrity_counts, format_integrity_issues, summarize_preflight
from aidebot.setup_guard import canonical_collisions, format_collisions


class HealthCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _collect(self, guild: discord.Guild) -> tuple[list[str], int, int, dict[str, int]]:
        lines: list[str] = []
        hard_blockers = 0
        warnings = 0
        me = guild.me

        if me is None:
            lines.append("❌ Impossible d’identifier le membre bot sur ce serveur.")
            hard_blockers += 1
        else:
            missing = missing_permission_labels(me.guild_permissions)
            if missing:
                lines.append("❌ Permissions bot manquantes : **" + ", ".join(missing) + "**")
                hard_blockers += 1
            else:
                lines.append("✅ Permissions Discord essentielles présentes.")

            managed_roles = {
                "👑・Direction",
                "📘・Responsable Formation",
                "🎓・Formateur",
                "🤝・Helper",
                "✅・Apprenant certifié",
                "💎・VIP",
                "🛡️・Expert Sécurité",
                "🤖・Expert Bots",
                "🌟・Ambassadeur",
                "👤・Membre",
            }
            blocked = [role.name for role in guild.roles if role.name in managed_roles and role >= me.top_role]
            if blocked:
                lines.append("❌ Hiérarchie bloquante : le rôle du bot doit être au-dessus de **" + ", ".join(blocked[:8]) + "**.")
                hard_blockers += 1
            else:
                lines.append("✅ Hiérarchie des rôles compatible.")

        collisions = canonical_collisions(
            role_names=(role.name for role in guild.roles),
            category_names=(category.name for category in guild.categories),
            channel_names=(channel.name for channel in guild.text_channels),
        )
        if collisions:
            lines.append("❌ Noms Aide Bot ambigus :\n" + format_collisions(collisions))
            hard_blockers += len(collisions)
        else:
            lines.append("✅ Aucun doublon sur les noms canoniques Aide Bot.")

        staff = discord.utils.get(guild.categories, name="━━ STAFF ━━")
        formations = discord.utils.get(guild.text_channels, name="🎓・formations")
        logs = discord.utils.get(guild.text_channels, name="🧾・logs")
        if not (staff and formations and logs):
            lines.append("❌ Setup incomplet : lance `/setup` puis `/audit_serveur`.")
            hard_blockers += 1
        else:
            lines.append("✅ Structure Aide Bot détectée.")
            if staff.permissions_for(guild.default_role).view_channel:
                lines.append("❌ La catégorie STAFF est visible par `@everyone`.")
                hard_blockers += 1
            else:
                lines.append("✅ Catégorie STAFF masquée pour `@everyone`.")

        railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
        persistence = persistence_check(self.bot.settings.db_path, railway)
        if persistence.ok:
            lines.append("✅ " + persistence.message)
        else:
            lines.append("❌ " + persistence.message)
            hard_blockers += 1

        integrity: dict[str, int] = {}
        try:
            cur = await self.bot.db._db().execute("SELECT 1 AS ok")
            row = await cur.fetchone()
            if not row or int(row["ok"]) != 1:
                raise RuntimeError("database ping failed")
            integrity = await database_integrity_counts(self.bot.db._db())
            lines.append("✅ Base de données accessible.")
        except Exception:
            lines.append("❌ Impossible d’interroger complètement la base de données.")
            hard_blockers += 1

        lines.extend(format_integrity_issues(integrity))

        if self.bot.intents.members:
            lines.append("✅ Server Members Intent demandé et session Discord connectée.")
        else:
            lines.append("❌ Server Members Intent n’est pas demandé par le bot.")
            hard_blockers += 1

        latency_ms = round(self.bot.latency * 1000)
        if latency_ms >= 1000:
            lines.append(f"⚠️ Latence Discord élevée : **{latency_ms} ms**.")
            warnings += 1
        else:
            lines.append(f"✅ Latence Discord : **{latency_ms} ms**.")

        return lines, hard_blockers, warnings, integrity

    @app_commands.command(name="sante", description="Vérifier si Aide Bot est prêt pour les tests et la production")
    async def sante(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "audit.run"):
            return await interaction.response.send_message("Accès refusé : `audit.run` requis.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        lines, hard_blockers, warnings, integrity = await self._collect(interaction.guild)
        summary = summarize_preflight(hard_blockers=hard_blockers, integrity_counts=integrity, warnings=warnings)
        title = "Aide Bot — READY" if summary.ready else "Aide Bot — BLOQUÉ"
        color = 0x57F287 if summary.ready else 0xED4245
        footer = f"Bloquants : {summary.blocking_count} • Avertissements : {summary.warning_count}"
        embed = discord.Embed(title=title, description="\n".join(lines)[:3900], color=color)
        embed.set_footer(text=footer)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="preflight", description="Audit complet avant autorisation de déploiement public")
    async def preflight(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "audit.run"):
            return await interaction.response.send_message("Accès refusé : `audit.run` requis.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        lines, hard_blockers, warnings, integrity = await self._collect(interaction.guild)
        summary = summarize_preflight(hard_blockers=hard_blockers, integrity_counts=integrity, warnings=warnings)
        if summary.ready:
            verdict = (
                "✅ **READY** — aucun blocage connu détecté par les contrôles automatiques. "
                "Un test Discord réel reste nécessaire avant ouverture publique."
            )
            color = 0x57F287
        else:
            verdict = (
                f"❌ **BLOQUÉ** — {summary.blocking_count} blocage(s) détecté(s). "
                "Ne déploie pas publiquement tant qu’ils ne sont pas corrigés."
            )
            color = 0xED4245

        embed = discord.Embed(
            title="Aide Bot — Pré-production",
            description=verdict + "\n\n" + "\n".join(lines)[:3500],
            color=color,
        )
        embed.set_footer(text=f"Bloquants : {summary.blocking_count} • Avertissements : {summary.warning_count}")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HealthCog(bot))
