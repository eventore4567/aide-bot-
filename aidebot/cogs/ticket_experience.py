from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from aidebot.experience_content import BANNER_URL
from aidebot.payments import PAYMENT_LABELS, payment_transition_error
from aidebot.permissions import can


class PremiumPaymentView(discord.ui.View):
    """Remplace la commande slash de paiement par des boutons staff persistants."""

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

        changed, previous = await self.bot.db.transition_payment(req["id"], target)
        if not changed:
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

        training = self.bot.get_cog("TrainingCog")
        if training is not None:
            await training.log_action(
                interaction.guild,
                "Statut paiement",
                f"#{req['id']} • {PAYMENT_LABELS.get(previous or '', previous or '?')} → **{PAYMENT_LABELS[target]}** par {interaction.user.mention}",
            )

        refreshed = await self.bot.db.request_by_id(req["id"])
        state = refreshed["status"] if refreshed else "inconnu"
        text = f"Paiement **{PAYMENT_LABELS[target]}** • demande `#{req['id']}` • statut `{state}`."
        if target == "paid":
            text += " Le ticket peut maintenant être pris par un Formateur autorisé."
        elif target == "refused":
            text += " La prise en charge Premium reste bloquée."
        elif target == "refunded":
            text += " Le remboursement a été enregistré."
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

        # Le channel est créé avant que son ID soit enregistré dans la demande.
        for _ in range(6):
            await asyncio.sleep(0.5)
            req = await self.bot.db.request_by_channel(channel.id)
            if req is not None:
                break
        else:
            return

        is_help = req["training_key"] == "community_help"
        is_premium = req["payment_status"] in {"pending", "paid", "refunded", "refused"}

        e = discord.Embed(
            title="Aide Bot — ton espace de suivi",
            description=(
                "Ce ticket est ton espace privé avec l’équipe Aide Bot. Explique ton problème avec le plus de contexte possible : "
                "ce que tu veux obtenir, ce qui ne fonctionne pas, ce que tu as déjà essayé et les messages d’erreur exacts. "
                "Tu peux envoyer des captures d’écran si elles aident à comprendre.\n\n"
                "**Ne partage jamais de token Discord, mot de passe, code 2FA, cookie, clé API ou autre secret.** "
                "Un membre de l’équipe n’a pas besoin de ton mot de passe pour t’aider."
            ),
            color=0x5865F2,
        )
        e.add_field(
            name="Comment la prise en charge fonctionne",
            value=(
                "Un Helper/Formateur autorisé, un Responsable, un Administrateur Discord ou le propriétaire peut cliquer sur "
                "**Prendre**. L’attribution est protégée : si deux personnes essaient en même temps, une seule devient responsable du ticket. "
                "Ensuite, cette personne te guide jusqu’à la résolution."
            ),
            inline=False,
        )
        if is_help:
            e.add_field(
                name="Type de service — aide gratuite",
                value=(
                    "Cette demande fait partie de l’entraide gratuite. Le but est de t’expliquer la solution et de te permettre de la refaire seul. "
                    "Si ton besoin devient un projet complet, l’équipe peut te présenter une offre Premium sans rendre l’aide gratuite volontairement mauvaise."
                ),
                inline=False,
            )
        elif is_premium:
            e.add_field(
                name="Type de service — Premium",
                value=(
                    "Une demande Premium ne peut être prise en charge qu’après confirmation du paiement. La Direction, un administrateur Discord "
                    "ou le propriétaire utilise directement les boutons de paiement sous ce message ; aucune commande slash n’est nécessaire."
                ),
                inline=False,
            )
        else:
            e.add_field(
                name="Type de service — formation",
                value=(
                    "La formation avance étape par étape. Le Formateur explique, montre un exemple, te laisse pratiquer puis valide la progression. "
                    "À la fin, tu peux laisser un avis et garder les ressources utiles."
                ),
                inline=False,
            )

        e.add_field(
            name="Pour obtenir une réponse plus vite",
            value=(
                "1. Décris l’objectif final.\n"
                "2. Copie le message d’erreur exact s’il y en a un.\n"
                "3. Dis ce que tu as déjà testé.\n"
                "4. Envoie une capture seulement si elle apporte une information utile.\n"
                "5. Évite de ping plusieurs membres du staff : la personne assignée suit ton ticket."
            ),
            inline=False,
        )
        e.set_image(url=BANNER_URL)
        e.set_footer(text=f"Aide Bot • Ticket #{req['id']} • suivi jusqu’à résolution")

        try:
            await channel.send(
                embed=e,
                view=PremiumPaymentView(self.bot) if is_premium else None,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketExperienceCog(bot))
