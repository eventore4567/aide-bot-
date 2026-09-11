from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from aidebot.experience_content import BANNER_URL
from aidebot.payments import PAYMENT_LABELS, can_transition_payment, payment_transition_error
from aidebot.permissions import can
from aidebot.premium_access import premium_role


class PremiumPaymentView(discord.ui.View):
    """Contrôles persistants de validation d’un achat Premium."""

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    async def _transition(self, interaction: discord.Interaction, target: str) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member) or not interaction.channel:
            return
        if not can(interaction.user, "payment.confirm"):
            return await interaction.response.send_message(
                "Seule la Direction, un administrateur Discord ou le propriétaire peut modifier le paiement.",
                ephemeral=True,
            )
        req = await self.bot.db.request_by_channel(interaction.channel.id)
        if not req:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        if req["payment_status"] == "not_required":
            return await interaction.response.send_message("Ce ticket ne demande pas de paiement.", ephemeral=True)

        current = str(req["payment_status"])
        member = interaction.guild.get_member(req["user_id"])
        role = premium_role(interaction.guild)
        role_added = False

        # Pour une validation, on vérifie d’abord que Discord permettra vraiment
        # d’attribuer l’abonnement. On évite un paiement "Payé" sans rôle Premium.
        if target == "paid" and current != "paid":
            if not can_transition_payment(current, target):
                return await interaction.response.send_message(payment_transition_error(current, target), ephemeral=True)
            if member is None:
                return await interaction.response.send_message("Le client n’est plus présent sur le serveur.", ephemeral=True)
            if role is None:
                return await interaction.response.send_message(
                    "Le rôle Premium est introuvable. Relance `/setup` avant de valider le paiement.",
                    ephemeral=True,
                )
            me = interaction.guild.me
            if me is None or role.managed or role >= me.top_role:
                return await interaction.response.send_message(
                    "Le paiement n’a pas été modifié : le bot ne peut pas attribuer le rôle **💎・VIP**. Place son rôle au-dessus puis réessaie.",
                    ephemeral=True,
                )
            if role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Aide Bot Premium — paiement ticket #{req['id']}")
                    role_added = True
                except (discord.Forbidden, discord.HTTPException):
                    return await interaction.response.send_message(
                        "Le paiement n’a pas été modifié car Discord refuse l’attribution du rôle Premium.",
                        ephemeral=True,
                    )

        changed, previous = await self.bot.db.transition_payment(req["id"], target)
        if not changed:
            if role_added and member is not None and role is not None:
                try:
                    await member.remove_roles(role, reason=f"Rollback paiement Aide Bot #{req['id']}")
                except discord.HTTPException:
                    pass
            if previous is None:
                message = "Demande introuvable."
            elif previous == "not_required":
                message = "Ce ticket ne demande pas de paiement."
            else:
                message = payment_transition_error(previous, target)
            return await interaction.response.send_message(message, ephemeral=True)

        if previous == target:
            return await interaction.response.send_message(
                f"Le paiement est déjà **{PAYMENT_LABELS[target]}**.",
                ephemeral=True,
            )

        role_note = ""
        if target == "paid":
            role_note = " Le rôle **💎・VIP** est maintenant actif pour le client."
        elif target == "refunded" and member is not None and role is not None and role in member.roles:
            try:
                await member.remove_roles(role, reason=f"Aide Bot Premium — remboursement ticket #{req['id']}")
                role_note = " Le rôle **💎・VIP** a été retiré."
            except (discord.Forbidden, discord.HTTPException):
                role_note = " **Attention :** le remboursement est enregistré mais Discord a refusé le retrait du rôle VIP."

        training = self.bot.get_cog("TrainingCog")
        if training is not None:
            await training.log_action(
                interaction.guild,
                "Statut paiement",
                f"#{req['id']} • {PAYMENT_LABELS.get(previous or '', previous or '?')} → **{PAYMENT_LABELS[target]}** par {interaction.user.mention}",
            )

        refreshed = await self.bot.db.request_by_id(req["id"])
        state = refreshed["status"] if refreshed else "inconnu"
        text = f"Paiement **{PAYMENT_LABELS[target]}** • ticket `#{req['id']}` • état `{state}`.{role_note}"
        if target == "paid":
            text += " Un Formateur peut maintenant cliquer sur **Prendre**."
        elif target == "refused":
            text += " L’abonnement reste verrouillé."
        elif target == "refunded":
            text += " L’accès Premium est annulé."
        await interaction.response.send_message(text)

    @discord.ui.button(
        label="Paiement validé",
        style=discord.ButtonStyle.success,
        custom_id="aidebot:payment:paid",
        row=0,
    )
    async def paid(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._transition(interaction, "paid")

    @discord.ui.button(
        label="Paiement refusé",
        style=discord.ButtonStyle.danger,
        custom_id="aidebot:payment:refused",
        row=0,
    )
    async def refused(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._transition(interaction, "refused")

    @discord.ui.button(
        label="Remboursé",
        style=discord.ButtonStyle.secondary,
        custom_id="aidebot:payment:refunded",
        row=0,
    )
    async def refunded(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._transition(interaction, "refunded")


class TicketExperienceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(PremiumPaymentView(self.bot))

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("ticket-"):
            return

        # Le premier message clair du ticket est envoyé par TrainingCog. Ce listener
        # n’ajoute qu’un petit bloc financier quand un paiement est réellement requis.
        for _ in range(8):
            await asyncio.sleep(0.4)
            req = await self.bot.db.request_by_channel(channel.id)
            if req is not None:
                break
        else:
            return

        if req["payment_status"] == "not_required":
            return

        e = discord.Embed(
            title="Premium — validation de l’achat",
            description=(
                f"**État du paiement : {PAYMENT_LABELS.get(req['payment_status'], req['payment_status'])}.**\n\n"
                "La Direction vérifie le paiement puis utilise les boutons ci-dessous. "
                "Quand **Paiement validé** est utilisé, le rôle **💎・VIP** est attribué automatiquement et l’abonnement devient utilisable.\n\n"
                "Le client ne doit envoyer ici **aucun mot de passe, token, cookie, code 2FA ou code de récupération**."
            ),
            color=0x9B59B6,
        )
        e.set_image(url=BANNER_URL)
        e.set_footer(text=f"Aide Bot • Ticket #{req['id']} • contrôle financier réservé au staff autorisé")

        try:
            await channel.send(
                embed=e,
                view=PremiumPaymentView(self.bot),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketExperienceCog(bot))
