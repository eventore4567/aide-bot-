from __future__ import annotations

import logging
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from aidebot.invite_integrity import finalize_pending_invite
from aidebot.worker_resilience import run_isolated_batch

log = logging.getLogger("aidebot.invites")


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
        async def refresh_one(guild: discord.Guild) -> None:
            await self._refresh(guild)

        async def refresh_error(guild: discord.Guild, exc: Exception) -> None:
            log.exception("Échec du cache d'invitations pour guild=%s", guild.id, exc_info=exc)

        await run_isolated_batch(self.bot.guilds, refresh_one, refresh_error)

    async def _refresh(self, guild: discord.Guild) -> list[discord.Invite]:
        try:
            invites = await guild.invites()
        except discord.Forbidden:
            log.warning("Impossible de lire les invitations de guild=%s: permission refusée", guild.id)
            return []
        except discord.HTTPException as exc:
            log.warning("Impossible de rafraîchir les invitations de guild=%s: %s", guild.id, exc)
            return []
        self.cache[guild.id] = {i.code: i.uses or 0 for i in invites}
        return invites

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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return

        member_role = discord.utils.get(member.guild.roles, name="👤・Membre")
        if member_role:
            try:
                await member.add_roles(member_role, reason="Rôle membre automatique Aide Bot")
            except discord.Forbidden:
                await self._log(
                    member.guild,
                    "Rôle membre non attribué",
                    f"Impossible d'attribuer {member_role.mention} à {member.mention}. Vérifie la hiérarchie du bot.",
                )
            except discord.HTTPException as exc:
                log.warning("Échec temporaire d'attribution du rôle membre à %s: %s", member.id, exc)

        before = self.cache.get(member.guild.id, {})
        current = await self._refresh(member.guild)
        used = next((i for i in current if (i.uses or 0) > before.get(i.code, 0)), None)
        if not used or not used.inviter or used.inviter.bot:
            return
        hours = self.bot.settings.invite_validation_hours
        validate_after = int(time.time()) + hours * 3600
        await self.bot.db.add_pending_invite(member.guild.id, used.inviter.id, member.id, validate_after)
        await self._log(
            member.guild,
            "Invitation en validation",
            f"{member.mention} semble avoir été invité par {used.inviter.mention}. Validation dans {hours}h s'il reste sur le serveur.",
        )

    async def _award_invite_roles(self, guild: discord.Guild, inviter_id: int) -> None:
        total = await self.bot.db.validated_invites(guild.id, inviter_id)
        inviter = guild.get_member(inviter_id)
        if not inviter:
            return
        if total >= 10:
            role = discord.utils.get(guild.roles, name="🌟・Ambassadeur")
            if role and role not in inviter.roles:
                try:
                    await inviter.add_roles(role, reason="10 invitations validées sur Aide Bot")
                    await self._log(
                        guild,
                        "Rôle Ambassadeur débloqué",
                        f"{inviter.mention} atteint **{total} invitations validées**.",
                    )
                except discord.Forbidden:
                    await self._log(
                        guild,
                        "Ambassadeur non attribué",
                        f"Impossible d'attribuer {role.mention} à {inviter.mention}. Vérifie la hiérarchie du bot.",
                    )
                except discord.HTTPException as exc:
                    log.warning("Échec temporaire attribution Ambassadeur à %s: %s", inviter_id, exc)

    async def _validate_one(self, row) -> None:
        guild = self.bot.get_guild(row["guild_id"])
        if guild is None:
            # Do not invalidate a real invite just because the guild is
            # temporarily absent from cache during a reconnect. It remains
            # pending and will be checked again on a later iteration.
            log.warning("Validation invitation #%s reportée: guild %s indisponible", row["id"], row["guild_id"])
            return

        member = guild.get_member(row["invitee_id"])
        valid = bool(member and not member.bot)
        finalized = await finalize_pending_invite(self.bot.db, row["id"], valid)
        if finalized is None:
            return

        if valid:
            total = await self.bot.db.validated_invites(guild.id, row["inviter_id"])
            await self._log(
                guild,
                "Invitation validée",
                f"<@{row['inviter_id']}> gagne **1 crédit formation** grâce à <@{row['invitee_id']}>. Total validé : **{total}**.",
            )
            await self._award_invite_roles(guild, row["inviter_id"])
        else:
            await self._log(
                guild,
                "Invitation refusée",
                f"L'invitation liée à <@{row['invitee_id']}> n'a pas été validée : le membre n'est plus présent.",
            )

    async def _validation_error(self, row, exc: Exception) -> None:
        log.exception("Échec isolé de validation invitation #%s", row["id"], exc_info=exc)
        guild = self.bot.get_guild(row["guild_id"])
        if guild:
            await self._log(
                guild,
                "Erreur validation invitation",
                f"Invitation #{row['id']} non traitée à cette itération. Elle sera retentée automatiquement.",
            )

    @tasks.loop(minutes=10)
    async def validate_pending(self) -> None:
        try:
            due = await self.bot.db.due_pending_invites(int(time.time()))
        except Exception:
            log.exception("Impossible de charger les invitations à valider; worker conservé actif")
            return
        await run_isolated_batch(due, self._validate_one, self._validation_error)

    @validate_pending.before_loop
    async def before_validate(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(name="invites", description="Voir tes invitations validées disponibles")
    async def invites(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        credits = await self.bot.db.invite_credits(interaction.guild.id, interaction.user.id)
        total = await self.bot.db.validated_invites(interaction.guild.id, interaction.user.id)
        await interaction.response.send_message(
            f"Tu as **{credits} crédit(s)** disponible(s) et **{total} invitation(s)** validée(s) au total. Utilise `/bonus_invites` pour voir les paliers.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InvitesCog(bot))
