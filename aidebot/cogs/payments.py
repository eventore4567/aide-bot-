from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.payments import PAYMENT_LABELS, normalize_payment_state, payment_transition_error
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

        changed, previous = await self.bot.db.transition_payment(req["id"], normalized)
        if not changed:
            if previous == "not_required":
                message = "Ce ticket ne demande pas de paiement."
            elif previous is None:
                message = "Demande introuvable."
            else:
                message = payment_transition_error(previous, normalized)
            return await interaction.response.send_message(message, ephemeral=True)

        if previous == normalized:
            return await interaction.response.send_message(
                f"Le paiement est déjà **{PAYMENT_LABELS[normalized]}**. Aucune modification appliquée.",
                ephemeral=True,
            )

        training = self.bot.get_cog("TrainingCog")
        if training:
            suffix = f" • {raison[:300]}" if raison.strip() else ""
            await training.log_action(
                interaction.guild,
                "Statut paiement",
                f"#{req['id']} • {PAYMENT_LABELS.get(previous or '', previous or '?')} → **{PAYMENT_LABELS[normalized]}** par {interaction.user.mention}{suffix}",
            )

        refreshed = await self.bot.db.request_by_id(req["id"])
        request_state = refreshed["status"] if refreshed else "inconnu"
        message = (
            f"Paiement de la demande **#{req['id']}** : **{PAYMENT_LABELS[normalized]}**.\n"
            f"Statut de la demande : `{request_state}`."
        )
        if normalized == "paid":
            message += " Le ticket est disponible pour un Formateur s’il n’est pas déjà terminé."
        elif normalized == "refused":
            message += " Le ticket reste bloqué jusqu’à une nouvelle décision de la Direction."
        elif normalized == "refunded":
            message += " Le remboursement est enregistré sans effacer une formation déjà terminée."

        await interaction.response.send_message(message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PaymentsCog(bot))
