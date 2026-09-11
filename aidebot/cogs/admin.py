from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.permissions import CAPABILITIES, can, decide


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="permissions_test", description="Diagnostiquer les permissions Aide Bot d’un membre")
    async def permissions_test(self, interaction: discord.Interaction, membre: discord.Member) -> None:
        if not isinstance(interaction.user, discord.Member) or not can(interaction.user, "config.manage"):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)
        lines = []
        for capability in CAPABILITIES:
            d = decide(membre, capability)
            icon = "✅" if d.allowed else "❌"
            lines.append(f"{icon} `{capability}` — {d.reason}")
        await interaction.response.send_message(embed=discord.Embed(title=f"Permissions — {membre.display_name}", description="\n".join(lines), color=0x5865F2), ephemeral=True)

    @app_commands.command(name="paiement_confirmer", description="Confirmer manuellement le paiement du ticket actuel")
    async def paiement_confirmer(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not can(interaction.user, "payment.confirm"):
            return await interaction.response.send_message("Accès refusé : `payment.confirm` requis.", ephemeral=True)
        if not interaction.channel:
            return
        req = await self.bot.db.request_by_channel(interaction.channel.id)
        if not req:
            return await interaction.response.send_message("Utilise cette commande dans un ticket.", ephemeral=True)
        await self.bot.db.update_request(req["id"], payment_status="paid", status="open")
        await interaction.response.send_message("Paiement marqué **payé**. Le ticket peut maintenant être pris par un formateur.")

    @app_commands.command(name="staff_stats", description="Voir les statistiques d’un Helper/Formateur")
    async def staff_stats(self, interaction: discord.Interaction, membre: discord.Member) -> None:
        if not interaction.guild:
            return
        row = await self.bot.db.profile(interaction.guild.id, membre.id)
        avg = row["rating_sum"] / row["reviews_count"] if row["reviews_count"] else 0
        desc = f"Réputation : **{row['reputation']}**\nAides : **{row['helped_count']}**\nFormations : **{row['trainings_completed']}**\nAvis : **{avg:.1f}/5** ({row['reviews_count']})"
        await interaction.response.send_message(embed=discord.Embed(title=f"Stats staff — {membre.display_name}", description=desc, color=0x57F287), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
