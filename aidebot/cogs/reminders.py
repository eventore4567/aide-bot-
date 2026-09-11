from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from aidebot.permissions import can


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
        if req["status"] in {"completed", "closed"}:
            return await interaction.response.send_message("Cette demande est déjà terminée.", ephemeral=True)

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
            "Rappel annulé." if count else "Aucun rappel n'était en attente.",
            ephemeral=True,
        )

    @tasks.loop(seconds=30)
    async def dispatch_reminders(self) -> None:
        rows = await self.bot.db.due_reminders(int(time.time()), 50)
        for row in rows:
            guild = self.bot.get_guild(row["guild_id"])
            if guild is None:
                await self.bot.db.finish_reminder(row["id"], "failed")
                continue

            req = await self.bot.db.request_by_id(row["request_id"])
            if not req or req["status"] in {"completed", "closed"}:
                await self.bot.db.finish_reminder(row["id"], "cancelled")
                continue

            channel = guild.get_channel(row["channel_id"])
            if not isinstance(channel, discord.TextChannel):
                await self.bot.db.finish_reminder(row["id"], "failed")
                continue

            mentions = [f"<@{row['user_id']}>"]
            if row["trainer_id"]:
                mentions.append(f"<@{row['trainer_id']}>")
            description = (
                f"{' '.join(mentions)}\n"
                f"La formation/demande **#{row['request_id']}** a un rendez-vous ou rappel prévu maintenant."
            )
            try:
                await channel.send(
                    embed=discord.Embed(title="Rappel de formation", description=description, color=0xF1C40F),
                    allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
                )
            except discord.HTTPException:
                await self.bot.db.finish_reminder(row["id"], "failed")
                continue

            for user_id in {row["user_id"], row["trainer_id"]}:
                if not user_id:
                    continue
                member = guild.get_member(user_id)
                if member:
                    try:
                        await member.send(f"Rappel Aide Bot : la demande **#{row['request_id']}** est prévue maintenant. {channel.mention}")
                    except discord.HTTPException:
                        pass

            await self.bot.db.finish_reminder(row["id"], "sent")
            logs = discord.utils.get(guild.text_channels, name="🧾・logs")
            if logs:
                try:
                    await logs.send(
                        embed=discord.Embed(
                            title="Rappel envoyé",
                            description=f"Demande #{row['request_id']} • rappel #{row['id']}",
                            color=0x2B2D31,
                        )
                    )
                except discord.HTTPException:
                    pass

    @dispatch_reminders.before_loop
    async def before_dispatch_reminders(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RemindersCog(bot))
