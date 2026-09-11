from __future__ import annotations

import logging
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from aidebot.permissions import can
from aidebot.reminder_delivery import (
    claim_due_reminders,
    delivery_marker,
    finish_processing_reminder,
    processing_reminders,
    release_processing_reminder,
)

log = logging.getLogger("aidebot.reminders")

ACTIVE_REQUEST_STATUSES = {"open", "assigned", "in_progress", "payment_pending"}


class RemindersCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.dispatch_reminders.start()

    async def cog_unload(self) -> None:
        self.dispatch_reminders.cancel()

    async def _can_manage_request(self, interaction: discord.Interaction, req) -> bool:
        return bool(
            isinstance(interaction.user, discord.Member)
            and (interaction.user.id == req["trainer_id"] or can(interaction.user, "training.manage"))
        )

    async def _log(self, guild: discord.Guild, title: str, description: str) -> None:
        channel = discord.utils.get(guild.text_channels, name="🧾・logs")
        if channel:
            try:
                await channel.send(
                    embed=discord.Embed(title=title, description=description, color=0x2B2D31),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass

    async def _delivery_found(self, channel: discord.TextChannel, reminder_id: int) -> bool | None:
        """Return True/False when history is readable, None when it is not.

        The deterministic footer lets the bot distinguish "message was sent but
        DB commit never happened" from "message was never sent" after a crash.
        """
        marker = delivery_marker(reminder_id)
        try:
            async for message in channel.history(limit=100):
                if self.bot.user and message.author.id != self.bot.user.id:
                    continue
                for item in message.embeds:
                    if item.footer and item.footer.text == marker:
                        return True
            return False
        except (discord.Forbidden, discord.HTTPException):
            return None

    async def _recover_processing(self) -> None:
        rows = await processing_reminders(self.bot.db._db(), 100)
        for row in rows:
            guild = self.bot.get_guild(row["guild_id"])
            if guild is None:
                await finish_processing_reminder(self.bot.db._db(), row["id"], "failed")
                continue

            channel = guild.get_channel(row["channel_id"])
            if not isinstance(channel, discord.TextChannel):
                await finish_processing_reminder(self.bot.db._db(), row["id"], "failed")
                await self._log(guild, "Rappel irrécupérable", f"Rappel #{row['id']} : salon introuvable après récupération.")
                continue

            delivered = await self._delivery_found(channel, row["id"])
            if delivered is True:
                await finish_processing_reminder(self.bot.db._db(), row["id"], "sent")
                await self._log(guild, "Rappel récupéré", f"Rappel #{row['id']} déjà envoyé avant le redémarrage : état réparé sans doublon.")
                continue

            req = await self.bot.db.request_by_id(row["request_id"])
            if not req or req["status"] not in ACTIVE_REQUEST_STATUSES:
                await finish_processing_reminder(self.bot.db._db(), row["id"], "cancelled")
                continue

            if delivered is False:
                await release_processing_reminder(self.bot.db._db(), row["id"])
                continue

            # Fail closed when Discord history cannot be inspected. Retrying here
            # could duplicate a reminder that was actually delivered just before
            # a crash, so keep the row in `processing` for staff diagnosis.
            await self._log(
                guild,
                "Rappel en vérification",
                f"Rappel #{row['id']} : impossible de vérifier l'historique du salon. Aucun renvoi automatique pour éviter un doublon.",
            )

    @app_commands.command(name="formation_rappel", description="Programmer un rappel automatique pour la formation du ticket actuel")
    @app_commands.describe(minutes="Nombre de minutes avant le rappel (5 min à 30 jours)")
    async def formation_rappel(
        self,
        interaction: discord.Interaction,
        minutes: app_commands.Range[int, 5, 43200],
    ) -> None:
        if not interaction.guild or not interaction.channel:
            return
        req = await self.bot.db.request_by_channel(interaction.channel.id)
        if not req:
            return await interaction.response.send_message("Utilise cette commande dans un ticket de formation.", ephemeral=True)
        if not await self._can_manage_request(interaction, req):
            return await interaction.response.send_message("Seul le formateur assigné ou un responsable peut programmer le rappel.", ephemeral=True)
        if req["status"] not in ACTIVE_REQUEST_STATUSES:
            return await interaction.response.send_message("Cette demande n'est plus active.", ephemeral=True)

        remind_at = int(time.time()) + int(minutes) * 60
        reminder_id = await self.bot.db.create_reminder(
            interaction.guild.id,
            req["id"],
            interaction.channel.id,
            req["user_id"],
            req["trainer_id"],
            remind_at,
        )
        await self.bot.db.update_request(req["id"], scheduled_for=f"<t:{remind_at}:F>")

        training = self.bot.get_cog("TrainingCog")
        if training:
            await training.log_action(
                interaction.guild,
                "Rappel programmé",
                f"Demande #{req['id']} • rappel #{reminder_id} • <t:{remind_at}:F> • par {interaction.user.mention}",
            )
        await interaction.response.send_message(
            f"Rappel **#{reminder_id}** programmé pour <t:{remind_at}:F> (**<t:{remind_at}:R>**).",
            ephemeral=True,
        )

    @app_commands.command(name="formation_rappel_annuler", description="Annuler le rappel en attente du ticket actuel")
    async def formation_rappel_annuler(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not interaction.channel:
            return
        req = await self.bot.db.request_by_channel(interaction.channel.id)
        if not req:
            return await interaction.response.send_message("Utilise cette commande dans un ticket de formation.", ephemeral=True)
        if not await self._can_manage_request(interaction, req):
            return await interaction.response.send_message("Seul le formateur assigné ou un responsable peut annuler le rappel.", ephemeral=True)
        count = await self.bot.db.cancel_reminders_for_request(req["id"])
        await interaction.response.send_message(
            "Rappel annulé." if count else "Aucun rappel en attente n'a pu être annulé.",
            ephemeral=True,
        )

    @tasks.loop(seconds=30)
    async def dispatch_reminders(self) -> None:
        # First reconcile reminders left in `processing` by a crash/restart.
        await self._recover_processing()

        rows = await claim_due_reminders(self.bot.db._db(), int(time.time()), 50)
        for row in rows:
            try:
                guild = self.bot.get_guild(row["guild_id"])
                if guild is None:
                    await finish_processing_reminder(self.bot.db._db(), row["id"], "failed")
                    continue

                req = await self.bot.db.request_by_id(row["request_id"])
                if not req or req["status"] not in ACTIVE_REQUEST_STATUSES:
                    await finish_processing_reminder(self.bot.db._db(), row["id"], "cancelled")
                    continue

                channel = guild.get_channel(row["channel_id"])
                if not isinstance(channel, discord.TextChannel):
                    await finish_processing_reminder(self.bot.db._db(), row["id"], "failed")
                    continue

                mentions = [f"<@{row['user_id']}>"]
                if row["trainer_id"]:
                    mentions.append(f"<@{row['trainer_id']}>")
                description = (
                    f"{' '.join(mentions)}\n"
                    f"La formation/demande **#{row['request_id']}** a un rendez-vous ou rappel prévu maintenant."
                )
                reminder_embed = discord.Embed(title="Rappel de formation", description=description, color=0xF1C40F)
                reminder_embed.set_footer(text=delivery_marker(row["id"]))

                try:
                    await channel.send(
                        embed=reminder_embed,
                        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
                    )
                except discord.Forbidden:
                    await finish_processing_reminder(self.bot.db._db(), row["id"], "failed")
                    continue
                except discord.HTTPException:
                    # A normal HTTP failure means Discord did not acknowledge the
                    # send. Mark failed instead of looping forever every 30 sec.
                    await finish_processing_reminder(self.bot.db._db(), row["id"], "failed")
                    continue

                # Persist primary delivery before optional DMs. If the process
                # crashes between send() and this write, recovery finds the
                # footer in channel history and marks it sent without resending.
                await finish_processing_reminder(self.bot.db._db(), row["id"], "sent")

                for user_id in {row["user_id"], row["trainer_id"]}:
                    if not user_id:
                        continue
                    member = guild.get_member(user_id)
                    if member:
                        try:
                            await member.send(
                                f"Rappel Aide Bot : la demande **#{row['request_id']}** est prévue maintenant. {channel.mention}"
                            )
                        except discord.HTTPException:
                            pass

                await self._log(
                    guild,
                    "Rappel envoyé",
                    f"Demande #{row['request_id']} • rappel #{row['id']}",
                )
            except Exception:
                # Keep `processing` on unexpected failures. The next loop will
                # reconcile it safely using the marker instead of blindly
                # sending the same reminder again.
                log.exception("Erreur inattendue pendant le rappel #%s", row["id"])

    @dispatch_reminders.before_loop
    async def before_dispatch_reminders(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RemindersCog(bot))
