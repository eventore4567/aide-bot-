from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.blueprint import CATEGORY_SPECS, ROLE_SPECS, role_permissions
from aidebot.catalog import CHALLENGES, FORMATIONS, INVITE_REWARDS
from aidebot.message_reconcile import find_bot_embed_by_title, upsert_bot_embed_by_title
from aidebot.setup_guard import canonical_collisions, format_collisions


class SetupServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _reconcile_category_permissions(self, guild: discord.Guild, category: discord.CategoryChannel, roles: dict[str, discord.Role]) -> None:
        if category.name != "━━ STAFF ━━":
            return
        await category.set_permissions(guild.default_role, view_channel=False, reason="Aide Bot — staff privé")
        await category.set_permissions(roles["👑・Direction"], view_channel=True, send_messages=True, read_message_history=True, reason="Aide Bot — Direction")
        await category.set_permissions(roles["📘・Responsable Formation"], view_channel=True, send_messages=True, read_message_history=True, reason="Aide Bot — Responsable Formation")
        for role_name in ("🎓・Formateur", "🤝・Helper", "👤・Membre"):
            await category.set_permissions(roles[role_name], view_channel=False, reason="Aide Bot — staff fail-closed")

    async def _reconcile_channel_permissions(self, guild: discord.Guild, channel: discord.TextChannel, roles: dict[str, discord.Role]) -> None:
        if channel.category and channel.category.name == "━━ STAFF ━━":
            await channel.set_permissions(guild.default_role, view_channel=False, reason="Aide Bot — salon staff privé")
            await channel.set_permissions(roles["👑・Direction"], view_channel=True, send_messages=True, read_message_history=True, reason="Aide Bot — Direction")
            await channel.set_permissions(roles["📘・Responsable Formation"], view_channel=True, send_messages=True, read_message_history=True, reason="Aide Bot — Responsable Formation")
            for role_name in ("🎓・Formateur", "🤝・Helper", "👤・Membre"):
                await channel.set_permissions(roles[role_name], view_channel=False, reason="Aide Bot — salon staff fail-closed")
            return

        if channel.name in {"📢・annonces", "📜・règlement"}:
            await channel.set_permissions(guild.default_role, view_channel=True, send_messages=False, reason="Aide Bot — lecture seule")
            await channel.set_permissions(roles["👑・Direction"], view_channel=True, send_messages=True, manage_messages=True, reason="Aide Bot — Direction")
        elif channel.name == "👋・bienvenue":
            await channel.set_permissions(guild.default_role, view_channel=True, send_messages=False, reason="Aide Bot — accueil lecture seule")
            await channel.set_permissions(roles["👑・Direction"], view_channel=True, send_messages=True, reason="Aide Bot — Direction")

    async def _upsert_info(self, channel: discord.TextChannel | None, embed: discord.Embed) -> str:
        if channel is None or self.bot.user is None:
            return "absent"
        result = await upsert_bot_embed_by_title(
            channel,
            bot_user_id=self.bot.user.id,
            embed=embed,
        )
        return result.action

    async def _ensure_training_panel(self, channel: discord.TextChannel | None) -> str:
        if channel is None or self.bot.user is None:
            return "absent"
        checked, existing = await find_bot_embed_by_title(
            channel,
            bot_user_id=self.bot.user.id,
            title="Aide Bot — Formations",
        )
        if existing is not None:
            return "reused"
        if not checked:
            return "skipped"
        training_cog = self.bot.get_cog("TrainingCog")
        if training_cog is None:
            return "absent"
        try:
            await training_cog.post_panel(channel)
            return "created"
        except (discord.Forbidden, discord.HTTPException):
            return "failed"

    @app_commands.command(name="setup", description="Configurer Aide Bot sans supprimer les salons/rôles existants")
    async def setup_server(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if interaction.guild.owner_id != interaction.user.id:
            return await interaction.response.send_message("Seul le propriétaire du serveur peut lancer le setup initial.", ephemeral=True)

        guild = interaction.guild
        me = guild.me
        if me is None:
            return await interaction.response.send_message("Impossible d’identifier le rôle du bot sur ce serveur.", ephemeral=True)
        missing = []
        if not me.guild_permissions.manage_roles:
            missing.append("Gérer les rôles")
        if not me.guild_permissions.manage_channels:
            missing.append("Gérer les salons")
        if missing:
            return await interaction.response.send_message(
                "Le setup est bloqué avant toute modification. Permissions manquantes pour Aide Bot : **" + ", ".join(missing) + "**.",
                ephemeral=True,
            )

        collisions = canonical_collisions(
            role_names=(role.name for role in guild.roles),
            category_names=(category.name for category in guild.categories),
            channel_names=(channel.name for channel in guild.text_channels),
        )
        if collisions:
            return await interaction.response.send_message(
                "Le setup est bloqué **avant toute modification** car plusieurs objets utilisent un nom canonique Aide Bot. "
                "Je refuse de choisir arbitrairement le mauvais rôle/salon. Renomme ou supprime les doublons puis relance `/setup`.\n\n"
                + format_collisions(collisions),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        created_roles = 0
        reused_roles = 0
        roles: dict[str, discord.Role] = {}
        for name, color, perm_spec in reversed(ROLE_SPECS):
            role = discord.utils.get(guild.roles, name=name)
            if role is None:
                role = await guild.create_role(name=name, colour=discord.Colour(color), permissions=role_permissions(perm_spec), reason="Setup Aide Bot")
                created_roles += 1
            else:
                reused_roles += 1
            roles[name] = role

        created_channels = 0
        reused_channels = 0
        for category_name, channel_names in CATEGORY_SPECS:
            category = discord.utils.get(guild.categories, name=category_name)
            if category is None:
                category = await guild.create_category(category_name, reason="Setup Aide Bot")
            await self._reconcile_category_permissions(guild, category, roles)

            for channel_name in channel_names:
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                if channel is None:
                    channel = await guild.create_text_channel(channel_name, category=category, reason="Setup Aide Bot")
                    created_channels += 1
                else:
                    reused_channels += 1
                    if channel.category_id != category.id:
                        await channel.edit(category=category, reason="Aide Bot — remettre le salon dans sa catégorie canonique")
                await self._reconcile_channel_permissions(guild, channel, roles)

        panel_actions: list[str] = []

        bienvenue = discord.utils.get(guild.text_channels, name="👋・bienvenue")
        welcome_embed = discord.Embed(
            title="Bienvenue sur Aide Bot",
            description=(
                "Apprends Discord, crée ton premier serveur ou ton premier bot, demande de l’aide puis aide à ton tour les nouveaux.\n\n"
                "**Commencer :** `/diagnostic`, `/apprendre reprendre`, `/chercher`, `/formation catalogue`, `/aide demander`."
            ),
            color=0x5865F2,
        )
        panel_actions.append(await self._upsert_info(bienvenue, welcome_embed))

        formations = discord.utils.get(guild.text_channels, name="🎓・formations")
        panel_actions.append(await self._ensure_training_panel(formations))

        ressources = discord.utils.get(guild.text_channels, name="📚・ressources")
        titles = "\n".join(f"• **{data['title']}** — `{key}`" for key, data in FORMATIONS.items())
        resources_embed = discord.Embed(
            title="Centre d’apprentissage",
            description=(
                "Utilise `/diagnostic` pour être orienté, `/chercher` pour trouver une réponse, `/ressource` pour une checklist "
                f"et `/favoris ajouter` pour sauvegarder ce qui t’aide.\n\n{titles}"
            ),
            color=0x3498DB,
        )
        panel_actions.append(await self._upsert_info(ressources, resources_embed))

        presets = discord.utils.get(guild.text_channels, name="🧩・presets")
        rewards = "\n".join(f"• **{threshold} invitation(s)** → {label}" for threshold, label in INVITE_REWARDS)
        challenge_names = "\n".join(f"• `{key}` — {data['title']}" for key, data in CHALLENGES.items())
        presets_embed = discord.Embed(
            title="Presets, challenges et récompenses",
            description=f"**Paliers d’invitations**\n{rewards}\n\n**Challenges pratiques**\n{challenge_names}",
            color=0xF1C40F,
        )
        panel_actions.append(await self._upsert_info(presets, presets_embed))

        recrutement = discord.utils.get(guild.text_channels, name="🧑‍🏫・recrutement")
        recruitment_embed = discord.Embed(
            title="Devenir Helper / Formateur",
            description="Utilise `/candidature` pour envoyer ton expérience, tes spécialités et tes disponibilités. Les permissions restent minimales et explicites.",
            color=0x57F287,
        )
        panel_actions.append(await self._upsert_info(recrutement, recruitment_embed))

        ops = self.bot.get_cog("OpsDashboardCog")
        if ops is not None:
            try:
                ops_ok, hub_ok = await ops.refresh_guild(guild)
                panel_actions.extend(["updated" if ops_ok else "failed", "reused" if hub_ok else "failed"])
            except (discord.Forbidden, discord.HTTPException):
                panel_actions.extend(["failed", "failed"])

        top_roles = [role for role in roles.values() if role.name != "👤・Membre"]
        hierarchy_warning = any(role >= me.top_role for role in top_roles)
        suffix = "\n⚠️ Le rôle du bot doit être placé au-dessus de tous les rôles qu’il doit attribuer ou gérer." if hierarchy_warning else ""
        failures = sum(1 for action in panel_actions if action in {"failed", "skipped", "absent"})
        panel_note = (
            f"\nPanneaux : **{len(panel_actions) - failures} OK**, **{failures} à vérifier**."
            if panel_actions
            else ""
        )
        await interaction.followup.send(
            (
                f"Setup terminé. Rôles : **{created_roles} créés / {reused_roles} réutilisés**. "
                f"Salons : **{created_channels} créés / {reused_channels} réutilisés**. "
                "Aucun salon/rôle existant n’a été supprimé. Les permissions sensibles ont été réconciliées en fail-closed."
                + panel_note
                + suffix
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupServerCog(bot))
