from __future__ import annotations

import os

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.health import missing_permission_labels, persistence_check
from aidebot.permissions import can


class HealthCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="sante", description="Vérifier si Aide Bot est prêt pour les tests et la production")
    async def sante(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "audit.run"):
            return await interaction.response.send_message("Accès refusé : `audit.run` requis.", ephemeral=True)

        guild = interaction.guild
        me = guild.me
        lines: list[str] = []
        critical = False

        if me is None:
            lines.append("❌ Impossible d’identifier le membre bot sur ce serveur.")
            critical = True
        else:
            missing = missing_permission_labels(me.guild_permissions)
            if missing:
                lines.append("❌ Permissions bot manquantes : **" + ", ".join(missing) + "**")
                critical = True
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
                critical = True
            else:
                lines.append("✅ Hiérarchie des rôles compatible.")

        try:
            cur = await self.bot.db._db().execute("SELECT 1 AS ok")
            row = await cur.fetchone()
            if row and int(row["ok"]) == 1:
                lines.append("✅ Base de données accessible.")
            else:
                lines.append("❌ La base de données ne répond pas correctement.")
                critical = True
        except Exception:
            lines.append("❌ Impossible d’interroger la base de données.")
            critical = True

        railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
        persistence = persistence_check(self.bot.settings.db_path, railway)
        lines.append(("✅ " if persistence.ok else "⚠️ ") + persistence.message)

        staff = discord.utils.get(guild.categories, name="━━ STAFF ━━")
        formations = discord.utils.get(guild.text_channels, name="🎓・formations")
        logs = discord.utils.get(guild.text_channels, name="🧾・logs")
        if staff and formations and logs:
            lines.append("✅ Structure Aide Bot détectée.")
        else:
            lines.append("⚠️ Setup incomplet : lance `/setup` puis `/audit_serveur`.")

        lines.append(f"✅ Latence Discord : **{round(self.bot.latency * 1000)} ms**.")
        lines.append("ℹ️ `Server Members Intent` doit être activé dans le Developer Portal ; Discord le valide au démarrage du bot.")

        title = "Aide Bot — prêt" if not critical and persistence.ok else "Aide Bot — vérifications nécessaires"
        color = 0x57F287 if not critical and persistence.ok else 0xF1C40F
        await interaction.response.send_message(
            embed=discord.Embed(title=title, description="\n".join(lines), color=color),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HealthCog(bot))
