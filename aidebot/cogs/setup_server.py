from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.blueprint import CATEGORY_SPECS, ROLE_SPECS, role_permissions
from aidebot.catalog import CHALLENGES, FORMATIONS, INVITE_REWARDS


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
            # Une permission explicite au niveau salon peut contourner la catégorie :
            # on verrouille donc aussi chaque salon staff.
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

        await interaction.response.defer(ephemeral=True, thinking=True)

        roles: dict[str, discord.Role] = {}
        for name, color, perm_spec in reversed(ROLE_SPECS):
            role = discord.utils.get(guild.roles, name=name)
            if role is None:
                role = await guild.create_role(name=name, colour=discord.Colour(color), permissions=role_permissions(perm_spec), reason="Setup Aide Bot")
            roles[name] = role

        for category_name, channel_names in CATEGORY_SPECS:
            category = discord.utils.get(guild.categories, name=category_name)
            if category is None:
                category = await guild.create_category(category_name, reason="Setup Aide Bot")
            await self._reconcile_category_permissions(guild, category, roles)

            for channel_name in channel_names:
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                if channel is None:
                    channel = await guild.create_text_channel(channel_name, category=category, reason="Setup Aide Bot")
                elif channel.category_id != category.id:
                    await channel.edit(category=category, reason="Aide Bot — remettre le salon dans sa catégorie canonique")
                await self._reconcile_channel_permissions(guild, channel, roles)

        bienvenue = discord.utils.get(guild.text_channels, name="👋・bienvenue")
        if bienvenue:
            e = discord.Embed(
                title="Bienvenue sur Aide Bot",
                description=(
                    "Apprends Discord, crée ton premier serveur ou ton premier bot, demande de l’aide puis aide à ton tour les nouveaux.\n\n"
                    "**Commencer :** `/chercher`, `/formation catalogue`, `/aide demander`, `/challenge liste`, `/mentorat demander`."
                ),
                color=0x5865F2,
            )
            await bienvenue.send(embed=e)

        formations = discord.utils.get(guild.text_channels, name="🎓・formations")
        training_cog = self.bot.get_cog("TrainingCog")
        if formations and training_cog:
            await training_cog.post_panel(formations)

        ressources = discord.utils.get(guild.text_channels, name="📚・ressources")
        if ressources:
            titles = "\n".join(f"• **{data['title']}** — `{key}`" for key, data in FORMATIONS.items())
            await ressources.send(embed=discord.Embed(
                title="Centre d’apprentissage",
                description=f"Utilise `/chercher` pour trouver une réponse, `/ressource` pour une checklist et `/favoris ajouter` pour sauvegarder ce qui t’aide.\n\n{titles}",
                color=0x3498DB,
            ))

        presets = discord.utils.get(guild.text_channels, name="🧩・presets")
        if presets:
            rewards = "\n".join(f"• **{threshold} invitation(s)** → {label}" for threshold, label in INVITE_REWARDS)
            challenge_names = "\n".join(f"• `{key}` — {data['title']}" for key, data in CHALLENGES.items())
            await presets.send(embed=discord.Embed(
                title="Presets, challenges et récompenses",
                description=f"**Paliers d’invitations**\n{rewards}\n\n**Challenges pratiques**\n{challenge_names}",
                color=0xF1C40F,
            ))

        commencer = discord.utils.get(guild.text_channels, name="🎫・commencer")
        if commencer:
            await commencer.send(embed=discord.Embed(
                title="Comment commencer ?",
                description=(
                    "**1.** Cherche d’abord une réponse avec `/chercher`.\n"
                    "**2.** Besoin d’un humain ? `/aide demander`.\n"
                    "**3.** Besoin d’un parcours complet ? ouvre une formation depuis le panneau.\n"
                    "**4.** Tu veux pratiquer ? `/challenge liste`.\n"
                    "**5.** Tu veux être suivi plusieurs jours ? `/mentorat demander`."
                ),
                color=0x57F287,
            ))

        recrutement = discord.utils.get(guild.text_channels, name="🧑‍🏫・recrutement")
        if recrutement:
            await recrutement.send(embed=discord.Embed(
                title="Devenir Helper / Formateur",
                description="Utilise `/candidature` pour envoyer ton expérience, tes spécialités et tes disponibilités. Les permissions restent minimales et explicites.",
                color=0x57F287,
            ))

        top_roles = [role for role in roles.values() if role.name != "👤・Membre"]
        hierarchy_warning = any(role >= me.top_role for role in top_roles)
        suffix = "\n⚠️ Le rôle du bot doit être placé au-dessus de tous les rôles qu’il doit attribuer ou gérer." if hierarchy_warning else ""
        await interaction.followup.send(
            "Setup terminé. Aucun salon/rôle existant n’a été supprimé. Les permissions sensibles ont été réconciliées en fail-closed." + suffix,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupServerCog(bot))
