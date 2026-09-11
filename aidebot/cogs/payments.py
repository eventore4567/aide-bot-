from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.payments import PAYMENT_LABELS, REQUEST_STATUS_FOR_PAYMENT, normalize_payment_state
from aidebot.permissions import can


class PaymentsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="paiement_statut", description="Modifier le statut de paiement du ticket VIP actuel")
    @app_commands.describe(statut="pending / paid / refused / refunded", raison="Note interne optionnelle")
    async def paiement_statut(self, interaction: discord.Interaction, statut: str, raison: str = "") -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member) or not interaction.channel:
            return
        if not can(interaction.user, "payment.confirm"):
            return await interaction.response.send_message("Accès refusé : `payment.confirm` requis.", ephemeral=True)

        req = await self.bot.db.request_by_channel(interaction.channel.id)
        if not req:
            return await interaction.response.send_message("Utilise cette commande dans un ticket de formation.", ephemeral=True)
        if req["payment_status"] == "not_required":
            return await interaction.response.send_message("Ce ticket ne demande pas de paiement.", ephemeral=True)

        normalized = normalize_payment_state(statut)
        if normalized is None:
            return await interaction.response.send_message(
                "Statut invalide. Utilise `pending`, `paid`, `refused` ou `refunded`.",
                ephemeral=True,
            )

        await self.bot.db.update_request(
            req["id"],
            payment_status=normalized,
            status=REQUEST_STATUS_FOR_PAYMENT[normalized],
        )

        training = self.bot.get_cog("TrainingCog")
        if training:
            suffix = f" • {raison[:300]}" if raison.strip() else ""
            await training.log_action(
                interaction.guild,
                "Statut paiement",
                f"#{req['id']} → **{PAYMENT_LABELS[normalized]}** par {interaction.user.mention}{suffix}",
            )

        message = f"Paiement de la demande **#{req['id']}** : **{PAYMENT_LABELS[normalized]}**."
        if normalized == "paid":
            message += " Le ticket est maintenant disponible pour un Formateur."
        elif normalized == "refused":
            message += " Le ticket reste bloqué jusqu’à une nouvelle décision de la Direction."
        elif normalized == "refunded":
            message += " Le remboursement est enregistré dans l’historique du ticket."

        await interaction.response.send_message(message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PaymentsCog(bot))
