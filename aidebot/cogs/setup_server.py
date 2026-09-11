from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.blueprint import CATEGORY_SPECS, ROLE_SPECS, role_permissions
from aidebot.cogs.center import CenterView, center_embed
from aidebot.cogs.recruitment_panel import RecruitmentView, recruitment_embed
from aidebot.cogs.training import TrainingPanel
from aidebot.experience_content import BANNER_URL
from aidebot.message_reconcile import find_bot_embed_by_title
from aidebot.public_panels import (
    SHOP_TITLE,
    TICKET_TITLE,
    VIDEOS_TITLE,
    WELCOME_TITLE,
    ShopView,
    TicketEntryView,
    VideosPanelView,
    WelcomeView,
    shop_embed,
    ticket_embed,
    videos_panel_embed,
    welcome_embed,
)
from aidebot.setup_guard import canonical_collisions, format_collisions


READ_ONLY_PUBLIC = {
    "👋・bienvenue",
    "📜・règlement",
    "📢・annonces",
    "🎓・centre-aide",
    "🎓・formations",
    "🎥・videos-guides",
    "🛒・shop",
    "🎫・ouvrir-ticket",
    "⭐・avis",
    "🧑‍🏫・recrutement",
}

LEGACY_CHANNEL_MIGRATIONS = {
    "🎫・commencer": "🎫・ouvrir-ticket",
    "💎・vip": "🛒・shop",
}

LEGACY_WELCOME_TITLES = {
    "Bienvenue sur Aide Bot",
    "Aide Bot — Centre d’aide & formations",
    "Aide Bot — Formations",
    "Centre d’apprentissage",
    "Presets, challenges et récompenses",
}


class SetupServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _reconcile_category_permissions(
        self,
        guild: discord.Guild,
        category: discord.CategoryChannel,
        roles: dict[str, discord.Role],
    ) -> None:
        if category.name != "━━ STAFF ━━":
            return
        await category.set_permissions(guild.default_role, view_channel=False, reason="Aide Bot — staff privé")
        await category.set_permissions(
            roles["👑・Direction"],
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            reason="Aide Bot — Direction",
        )
        await category.set_permissions(
            roles["📘・Responsable Formation"],
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            reason="Aide Bot — Responsable Formation",
        )
        for role_name in ("🎓・Formateur", "🤝・Helper", "👤・Membre"):
            await category.set_permissions(roles[role_name], view_channel=False, reason="Aide Bot — staff fail-closed")

    async def _reconcile_channel_permissions(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        roles: dict[str, discord.Role],
    ) -> None:
        if channel.category and channel.category.name == "━━ STAFF ━━":
            await channel.set_permissions(guild.default_role, view_channel=False, reason="Aide Bot — salon staff privé")
            await channel.set_permissions(
                roles["👑・Direction"],
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                reason="Aide Bot — Direction",
            )
            await channel.set_permissions(
                roles["📘・Responsable Formation"],
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                reason="Aide Bot — Responsable Formation",
            )
            for role_name in ("🎓・Formateur", "🤝・Helper", "👤・Membre"):
                await channel.set_permissions(roles[role_name], view_channel=False, reason="Aide Bot — salon staff fail-closed")
            return

        if channel.name in READ_ONLY_PUBLIC:
            await channel.set_permissions(
                guild.default_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True,
                reason="Aide Bot — panneau public lecture seule",
            )
            await channel.set_permissions(
                roles["👑・Direction"],
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True,
                reason="Aide Bot — Direction",
            )
            await channel.set_permissions(
                roles["📘・Responsable Formation"],
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True,
                reason="Aide Bot — Responsable Formation",
            )

    async def _upsert_panel(
        self,
        channel: discord.TextChannel | None,
        embed: discord.Embed,
        view: discord.ui.View | None = None,
    ) -> str:
        if channel is None or self.bot.user is None:
            return "absent"
        checked, existing = await find_bot_embed_by_title(
            channel,
            bot_user_id=self.bot.user.id,
            title=embed.title or "",
            limit=100,
        )
        if existing is not None:
            try:
                await existing.edit(embed=embed, view=view)
                return "updated"
            except (discord.Forbidden, discord.HTTPException):
                return "failed"
        if not checked:
            return "skipped"
        try:
            await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())
            return "created"
        except (discord.Forbidden, discord.HTTPException):
            return "failed"

    async def _remove_legacy_bot_embeds(self, channel: discord.TextChannel | None, titles: set[str]) -> int:
        if channel is None or self.bot.user is None:
            return 0
        removed = 0
        try:
            async for message in channel.history(limit=100):
                if message.author.id != self.bot.user.id:
                    continue
                if not any(embed.title in titles for embed in message.embeds):
                    continue
                try:
                    await message.delete()
                    removed += 1
                except (discord.Forbidden, discord.HTTPException):
                    pass
        except (discord.Forbidden, discord.HTTPException):
            return removed
        return removed

    async def _migrate_legacy_channels(self, guild: discord.Guild) -> int:
        migrated = 0
        for old_name, new_name in LEGACY_CHANNEL_MIGRATIONS.items():
            old = discord.utils.get(guild.text_channels, name=old_name)
            new = discord.utils.get(guild.text_channels, name=new_name)
            if old is None or new is not None:
                continue
            try:
                await old.edit(name=new_name, reason="Aide Bot V41 — migration du setup")
                migrated += 1
            except (discord.Forbidden, discord.HTTPException):
                pass
        return migrated

    def _training_embed(self) -> discord.Embed:
        price = self.bot.settings.vip_price_robux
        e = discord.Embed(
            title="Aide Bot — Formations",
            description=(
                "Ce salon est **uniquement consacré aux formations**. Choisis réellement le parcours que tu veux suivre dans le menu ci-dessous.\n\n"
                "Chaque choix ouvre désormais **un formulaire différent et adapté au sujet** : créer un serveur ne pose pas les mêmes questions que "
                "les permissions, la sécurité ou le développement d’un bot."
            ),
            color=0x5865F2,
        )
        e.add_field(
            name="Formations classiques",
            value=(
                "Discord, création de serveur, permissions/sécurité et premier bot. Le formulaire demande le contexte utile à ce sujet, puis un ticket "
                "clair est créé avec la prochaine étape."
            ),
            inline=True,
        )
        e.add_field(
            name="Parcours Premium",
            value=(
                f"L’abonnement est configuré à **{price} Robux** et s’achète uniquement dans `🛒・shop` ou avec `/buy`. "
                "Sans rôle **💎・VIP**, un choix Premium affiche **Abonnement Premium manquant** au lieu d’ouvrir un formulaire."
            ),
            inline=True,
        )
        e.set_image(url=BANNER_URL)
        e.set_footer(text="Aide Bot • Choisis un parcours • Formulaire adapté au choix sélectionné")
        return e

    def _rules_embed(self) -> discord.Embed:
        e = discord.Embed(
            title="Règlement — Aide Bot",
            description=(
                "**1. Respect.** Pas d’insultes, harcèlement, spam ou contenu nuisible.\n"
                "**2. Sécurité.** Ne partage jamais token, mot de passe, cookie, code 2FA ou code de récupération.\n"
                "**3. Tickets.** Un ticket = un problème. Explique clairement ce que tu veux obtenir et ce que tu as déjà essayé.\n"
                "**4. Paiements.** L’achat Premium passe par la boutique et seule la validation enregistrée par la Direction fait foi.\n"
                "**5. Staff.** Évite de ping plusieurs personnes ; le membre assigné est responsable du suivi.\n"
                "**6. Aide.** Le but est de comprendre et pouvoir refaire seul, pas simplement copier une solution sans explication."
            ),
            color=0x2B2D31,
        )
        e.set_image(url=BANNER_URL)
        return e

    def _staff_embed(self) -> discord.Embed:
        e = discord.Embed(
            title="Aide Bot — Espace staff",
            description=(
                "Le serveur fonctionne principalement avec des **panneaux et boutons**. Dans les tickets, utilise les boutons de prise en charge, "
                "progression, paiement et fermeture. Les candidatures arrivent ici avec des boutons **Accepter / Refuser**.\n\n"
                "Les salons staff restent privés et les actions sensibles continuent d’être contrôlées par les rôles Aide Bot et les permissions Discord."
            ),
            color=0xF1C40F,
        )
        e.set_image(url=BANNER_URL)
        return e

    @app_commands.command(name="setup", description="Installer ou réparer complètement Aide Bot sur ce serveur")
    async def setup_server(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        is_owner = interaction.guild.owner_id == interaction.user.id
        is_admin = interaction.user.guild_permissions.administrator
        if not (is_owner or is_admin):
            return await interaction.response.send_message(
                "Le setup est réservé au propriétaire du serveur ou à un administrateur Discord.",
                ephemeral=True,
            )

        guild = interaction.guild
        me = guild.me
        if me is None:
            return await interaction.response.send_message("Impossible d’identifier le rôle du bot sur ce serveur.", ephemeral=True)

        required = {
            "Gérer les rôles": me.guild_permissions.manage_roles,
            "Gérer les salons": me.guild_permissions.manage_channels,
            "Voir les salons": me.guild_permissions.view_channel,
            "Envoyer des messages": me.guild_permissions.send_messages,
            "Intégrer des liens": me.guild_permissions.embed_links,
            "Voir l’historique": me.guild_permissions.read_message_history,
        }
        missing = [label for label, allowed in required.items() if not allowed]
        if missing:
            return await interaction.response.send_message(
                "**Setup bloqué avant toute modification.**\nPermissions manquantes pour Aide Bot : **"
                + ", ".join(missing)
                + "**.",
                ephemeral=True,
            )

        collisions = canonical_collisions(
            role_names=(role.name for role in guild.roles),
            category_names=(category.name for category in guild.categories),
            channel_names=(channel.name for channel in guild.text_channels),
        )
        if collisions:
            return await interaction.response.send_message(
                "**Setup bloqué avant toute modification.** Plusieurs objets utilisent le même nom Aide Bot. "
                "Je refuse de modifier arbitrairement le mauvais salon ou rôle. Renomme les doublons puis relance `/setup`.\n\n"
                + format_collisions(collisions),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        migrated_channels = await self._migrate_legacy_channels(guild)

        created_roles = 0
        reused_roles = 0
        roles: dict[str, discord.Role] = {}
        for name, color, perm_spec in reversed(ROLE_SPECS):
            role = discord.utils.get(guild.roles, name=name)
            if role is None:
                role = await guild.create_role(
                    name=name,
                    colour=discord.Colour(color),
                    permissions=role_permissions(perm_spec),
                    reason="Setup Aide Bot V41",
                )
                created_roles += 1
            else:
                reused_roles += 1
            roles[name] = role

        created_categories = 0
        reused_categories = 0
        created_channels = 0
        reused_channels = 0
        canonical_channels: dict[str, discord.TextChannel] = {}

        for category_name, channel_names in CATEGORY_SPECS:
            category = discord.utils.get(guild.categories, name=category_name)
            if category is None:
                category = await guild.create_category(category_name, reason="Setup Aide Bot V41")
                created_categories += 1
            else:
                reused_categories += 1
            await self._reconcile_category_permissions(guild, category, roles)

            for channel_name in channel_names:
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                if channel is None:
                    channel = await guild.create_text_channel(channel_name, category=category, reason="Setup Aide Bot V41")
                    created_channels += 1
                else:
                    reused_channels += 1
                    if channel.category_id != category.id:
                        await channel.edit(category=category, reason="Aide Bot V41 — catégorie canonique")
                canonical_channels[channel_name] = channel
                await self._reconcile_channel_permissions(guild, channel, roles)

        bienvenue = canonical_channels.get("👋・bienvenue")
        removed_legacy = await self._remove_legacy_bot_embeds(bienvenue, LEGACY_WELCOME_TITLES)
        formations = canonical_channels.get("🎓・formations")
        if formations is not None:
            removed_legacy += await self._remove_legacy_bot_embeds(
                formations,
                {"Aide Bot — Centre d’aide & formations", "Aide Bot — Formations"},
            )

        panel_actions: list[tuple[str, str]] = []
        panel_actions.append(("Bienvenue", await self._upsert_panel(bienvenue, welcome_embed(), WelcomeView(self.bot))))
        panel_actions.append(
            (
                "Règlement",
                await self._upsert_panel(canonical_channels.get("📜・règlement"), self._rules_embed()),
            )
        )

        center_cog = self.bot.get_cog("CenterCog")
        if center_cog is not None:
            panel_actions.append(
                (
                    "Centre d’aide",
                    await self._upsert_panel(
                        canonical_channels.get("🎓・centre-aide"),
                        center_embed(self.bot.settings.vip_price_robux),
                        CenterView(center_cog),
                    ),
                )
            )
        else:
            panel_actions.append(("Centre d’aide", "absent"))

        training_cog = self.bot.get_cog("TrainingCog")
        if training_cog is not None:
            panel_actions.append(
                (
                    "Formations",
                    await self._upsert_panel(
                        formations,
                        self._training_embed(),
                        TrainingPanel(training_cog),
                    ),
                )
            )
        else:
            panel_actions.append(("Formations", "absent"))

        panel_actions.append(
            (
                "Vidéos",
                await self._upsert_panel(
                    canonical_channels.get("🎥・videos-guides"),
                    videos_panel_embed(),
                    VideosPanelView(),
                ),
            )
        )
        panel_actions.append(
            (
                "Boutique",
                await self._upsert_panel(
                    canonical_channels.get("🛒・shop"),
                    shop_embed(self.bot.settings.vip_price_robux),
                    ShopView(self.bot),
                ),
            )
        )
        panel_actions.append(
            (
                "Tickets",
                await self._upsert_panel(
                    canonical_channels.get("🎫・ouvrir-ticket"),
                    ticket_embed(),
                    TicketEntryView(self.bot),
                ),
            )
        )
        panel_actions.append(
            (
                "Recrutement",
                await self._upsert_panel(
                    canonical_channels.get("🧑‍🏫・recrutement"),
                    recruitment_embed(),
                    RecruitmentView(self.bot),
                ),
            )
        )
        panel_actions.append(
            (
                "Staff",
                await self._upsert_panel(canonical_channels.get("📋・staff"), self._staff_embed()),
            )
        )

        top_roles = [role for role in roles.values() if role.name != "👤・Membre"]
        hierarchy_warning = any(role >= me.top_role for role in top_roles)
        failures = [(name, action) for name, action in panel_actions if action in {"failed", "skipped", "absent"}]

        result = discord.Embed(
            title="Setup Aide Bot terminé",
            description=(
                "Le serveur a été réconcilié avec la structure **panel-first** : accueil, centre d’aide, formations détaillées, vidéos, "
                "boutique Premium, tickets clairs et recrutement par formulaire sont des espaces distincts."
            ),
            color=0x57F287 if not failures and not hierarchy_warning else 0xF1C40F,
        )
        result.add_field(
            name="Structure",
            value=(
                f"Rôles : **{created_roles} créés / {reused_roles} réutilisés**\n"
                f"Catégories : **{created_categories} créées / {reused_categories} réutilisées**\n"
                f"Salons : **{created_channels} créés / {reused_channels} réutilisés**\n"
                f"Migrations d’anciens salons : **{migrated_channels}**"
            ),
            inline=True,
        )
        panel_ok = len(panel_actions) - len(failures)
        result.add_field(
            name="Panneaux",
            value=f"**{panel_ok}/{len(panel_actions)} OK**\nAnciens panneaux nettoyés : **{removed_legacy}**",
            inline=True,
        )
        result.add_field(
            name="Premium",
            value="Achat via **`/buy` / `🛒・shop`** → ticket paiement → validation staff → rôle **💎・VIP** → accès aux boutons/parcours Premium.",
            inline=False,
        )
        result.add_field(
            name="Commandes membres",
            value="Le bot reste limité à **`/setup`** et **`/buy`** ; le reste passe par les boutons, menus et formulaires.",
            inline=False,
        )
        if failures:
            result.add_field(
                name="À vérifier",
                value="\n".join(f"• {name}: `{action}`" for name, action in failures[:8]),
                inline=False,
            )
        if hierarchy_warning:
            result.add_field(
                name="Hiérarchie des rôles",
                value="Place le rôle d’Aide Bot au-dessus des rôles qu’il doit gérer ou attribuer, notamment **💎・VIP**.",
                inline=False,
            )
        result.set_image(url=BANNER_URL)
        result.set_footer(text="Aide Bot V41 • Relancer /setup met à jour les panneaux sans supprimer les salons utilisateurs")

        logs = canonical_channels.get("🧾・logs")
        if logs is not None:
            try:
                await logs.send(
                    embed=discord.Embed(
                        title="Setup exécuté",
                        description=f"Par {interaction.user.mention} • {panel_ok}/{len(panel_actions)} panneaux OK • {removed_legacy} ancien(s) panneau(x) nettoyé(s)",
                        color=0x2B2D31,
                    ),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

        await interaction.followup.send(embed=result, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupServerCog(bot))
