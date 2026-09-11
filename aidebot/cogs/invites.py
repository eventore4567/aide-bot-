from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands, tasks


class InvitesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.cache: dict[int, dict[str, int]] = {}

    async def cog_load(self) -> None:
        self.validate_pending.start()

    async def cog_unload(self) -> None:
        self.validate_pending.cancel()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            await self._refresh(guild)

    async def _refresh(self, guild: discord.Guild) -> list[discord.Invite]:
        try:
            invites = await guild.invites()
        except (discord.Forbidden, discord.HTTPException):
            return []
        self.cache[guild.id] = {i.code: i.uses or 0 for i in invites}
        return invites

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return
        before = self.cache.get(member.guild.id, {})
        current = await self._refresh(member.guild)
        used = next((i for i in current if (i.uses or 0) > before.get(i.code, 0)), None)
        if not used or not used.inviter or used.inviter.bot:
            return
        hours = self.bot.settings.invite_validation_hours
        await self.bot.db.add_pending_invite(member.guild.id, used.inviter.id, member.id, int(time.time()) + hours * 3600)

    @tasks.loop(minutes=10)
    async def validate_pending(self) -> None:
        due = await self.bot.db.due_pending_invites(int(time.time()))
        for row in due:
            guild = self.bot.get_guild(row["guild_id"])
            valid = bool(guild and guild.get_member(row["invitee_id"]) and not guild.get_member(row["invitee_id"]).bot)
            if valid:
                await self.bot.db.add_invite_credit(row["guild_id"], row["inviter_id"], 1)
            await self.bot.db.finish_pending_invite(row["id"], valid)

    @validate_pending.before_loop
    async def before_validate(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(name="invites", description="Voir tes invitations validées disponibles")
    async def invites(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        credits = await self.bot.db.invite_credits(interaction.guild.id, interaction.user.id)
        await interaction.response.send_message(f"Tu as **{credits} invitation(s) valide(s)** disponible(s).", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InvitesCog(bot))
