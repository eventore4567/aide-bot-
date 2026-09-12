from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.blueprint import CATEGORY_SPECS, ROLE_SPECS, role_permissions
from aidebot.cogs import product_experience_v51 as product_v51
from aidebot.cogs.assistant_guardian_v52 import (
    AI_CHANNEL,
    STAFF_CHANNEL,
    AssistantPanelView,
    GuardianPanelView,
    assistant_panel_embed,
    guardian_panel_embed,
)
from aidebot.cogs.help_system_v54 import (
    GUIDES_CHANNEL,
    QUICK_CHANNEL,
    GuidesView,
    HelpHomeView,
    QuickHelpView,
    guides_home_embed,
    help_home_embed,
    quick_help_embed,
)
from aidebot.cogs.recruitment_panel import RecruitmentView, recruitment_embed
from aidebot.cogs.training import TrainingPanel
from aidebot.experience_content import BANNER_URL
from aidebot.guardian import audit_guild, snapshot_guild, snapshot_hash
from aidebot.public_panels import TicketEntryView, ticket_embed
from aidebot.setup_guard import canonical_collisions, format_collisions

SETUP_TITLE = "Aide Bot — Installation & réparation"
SETUP_COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F
DANGER = 0xED4245
SNAPSHOT_RETENTION = 3

SETUP_STAGES = (
    "Analyse de sécurité",
    "Sauvegarde avant modification",
    "Migration des anciens éléments",
    "Rôles",
    "Catégories & salons",
    "Permissions",
    "Panneaux & modules",
    "Vérification finale",
)

REQUIRED_BOT_PERMISSIONS = (
    ("Gérer les rôles", "manage_roles"),
    ("Gérer les salons", "manage_channels"),
    ("Voir les salons", "view_channel"),
    ("Envoyer des messages", "send_messages"),
    ("Intégrer des liens", "embed_links"),
    ("Voir l’historique", "read_message_history"),
)

LEGACY_VIDEO_CHANNEL = "🎥・videos-guides"


@dataclass(frozen=True)
class SetupPreflight:
    missing_permissions: tuple[str, ...]
    collisions: tuple[Any, ...]
    roles_to_create: int
    categories_to_create: int
    channels_to_create: int
    channels_to_move: int
    hierarchy_warnings: tuple[str, ...]
    module_warnings: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return bool(self.missing_permissions or self.collisions or self.module_warnings)


class SetupSnapshotStore:
    def __init__(self, base_dir: Path, *, retention: int = SNAPSHOT_RETENTION) -> None:
        self.base_dir = base_dir
        self.retention = max(1, int(retention))
        self._lock = asyncio.Lock()

    def _save_sync(self, guild: discord.Guild, snapshot: dict[str, Any]) -> Path:
        directory = self.base_dir / str(guild.id)
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = directory / f"setup-{stamp}.json"
        payload = {
            "schema": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "guild_id": guild.id,
            "guild_name": guild.name,
            "snapshot_hash": snapshot_hash(snapshot),
            "contains_messages": False,
            "snapshot": snapshot,
        }
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
        files = sorted(directory.glob("setup-*.json"), reverse=True)
        for old in files[self.retention :]:
            try:
                old.unlink()
            except OSError:
                pass
        return path

    async def save(self, guild: discord.Guild) -> Path:
        snapshot = snapshot_guild(guild)
        async with self._lock:
            return await asyncio.to_thread(self._save_sync, guild, snapshot)


class SetupSessionView(discord.ui.View):
    def __init__(self, cog: "SetupExperienceV55Cog", user_id: int, *, install_disabled: bool) -> None:
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = int(user_id)
        self.install.disabled = bool(install_disabled)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.user_id:
            return True
        await interaction.response.send_message("Seule la personne qui a lancé `/setup` peut utiliser cette session.", ephemeral=True)
        return False

    @discord.ui.button(label="Installer / réparer", style=discord.ButtonStyle.primary, custom_id="aidebot:v55:setup:run")
    async def install(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.run_setup(interaction)

    @discord.ui.button(label="Vérifier seulement", style=discord.ButtonStyle.secondary, custom_id="aidebot:v55:setup:verify")
    async def verify(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.verify_only(interaction)

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.danger, custom_id="aidebot:v55:setup:cancel")
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        embed = discord.Embed(
            title="Setup annulé",
            description="Aucune modification n’a été appliquée par cette session.",
            color=WARNING,
        )
        await interaction.response.edit_message(embed=embed, view=None)


class SetupExperienceV55Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        base = Path(bot.settings.db_path).with_name("setup_snapshots")
        self.snapshots = SetupSnapshotStore(base)
        self._guild_locks: dict[int, asyncio.Lock] = {}

    def _base_setup(self):
        return self.bot.get_cog("SetupServerCog")

    def _lock_for(self, guild_id: int) -> asyncio.Lock:
        return self._guild_locks.setdefault(int(guild_id), asyncio.Lock())

    def _authorized(self, interaction: discord.Interaction) -> bool:
        return bool(
            interaction.guild
            and isinstance(interaction.user, discord.Member)
            and (interaction.guild.owner_id == interaction.user.id or interaction.user.guild_permissions.administrator)
        )

    def _preflight(self, guild: discord.Guild) -> SetupPreflight:
        me = guild.me
        if me is None:
            return SetupPreflight(
                ("Impossible d’identifier le membre bot",),
                tuple(),
                0,
                0,
                0,
                0,
                tuple(),
                ("Moteur Discord du bot indisponible",),
            )

        missing_permissions = tuple(
            label for label, attr in REQUIRED_BOT_PERMISSIONS if not bool(getattr(me.guild_permissions, attr, False))
        )
        collisions = tuple(
            canonical_collisions(
                role_names=(role.name for role in guild.roles),
                category_names=(category.name for category in guild.categories),
                channel_names=(channel.name for channel in guild.text_channels),
            )
        )

        roles_to_create = sum(1 for name, _color, _perms in ROLE_SPECS if discord.utils.get(guild.roles, name=name) is None)
        categories_to_create = sum(1 for name, _channels in CATEGORY_SPECS if discord.utils.get(guild.categories, name=name) is None)

        expected_category: dict[str, str] = {
            channel_name: category_name
            for category_name, channel_names in CATEGORY_SPECS
            for channel_name in channel_names
        }
        channels_to_create = 0
        channels_to_move = 0
        for channel_name, category_name in expected_category.items():
            channel = discord.utils.get(guild.text_channels, name=channel_name)
            if channel is None:
                if channel_name == AI_CHANNEL and discord.utils.get(guild.text_channels, name=LEGACY_VIDEO_CHANNEL) is not None:
                    continue
                channels_to_create += 1
            elif channel.category is None or channel.category.name != category_name:
                channels_to_move += 1

        hierarchy_warnings = tuple(
            role.name
            for role in guild.roles
            if role.name in {name for name, _color, _perms in ROLE_SPECS}
            and role != guild.default_role
            and role >= me.top_role
        )

        module_warnings: list[str] = []
        if self._base_setup() is None:
            module_warnings.append("Moteur SetupServerCog non chargé")
        if self.bot.get_cog("TrainingCog") is None:
            module_warnings.append("Module Formations non chargé")
        if self.bot.get_cog("HelpSystemV54Cog") is None:
            module_warnings.append("Moteur d’aide non chargé")
        if self.bot.get_cog("AssistantGuardianV52Cog") is None:
            module_warnings.append("Assistant IA / Guardian non chargé")

        return SetupPreflight(
            missing_permissions,
            collisions,
            roles_to_create,
            categories_to_create,
            channels_to_create,
            channels_to_move,
            hierarchy_warnings,
            tuple(module_warnings),
        )

    def _preflight_embed(self, guild: discord.Guild, report: SetupPreflight) -> discord.Embed:
        color = DANGER if report.blocked else WARNING if report.hierarchy_warnings else SETUP_COLOR
        e = discord.Embed(
            title=SETUP_TITLE,
            description=(
                "`/setup` analyse d’abord le serveur avant de toucher quoi que ce soit. "
                "Il **réutilise** les éléments Aide Bot existants, répare leur configuration et ne supprime pas les salons ou rôles personnels."
            ),
            color=color,
        )
        e.add_field(
            name="Plan détecté",
            value=(
                f"Rôles à créer : **{report.roles_to_create}**\n"
                f"Catégories à créer : **{report.categories_to_create}**\n"
                f"Salons à créer : **{report.channels_to_create}**\n"
                f"Salons Aide Bot à replacer : **{report.channels_to_move}**"
            ),
            inline=True,
        )
        e.add_field(
            name="Sécurité",
            value=(
                "Sauvegarde avant modification : **oui**\n"
                "Suppression de contenu utilisateur : **non**\n"
                "Collisions de noms : **" + ("bloquantes" if report.collisions else "aucune") + "**\n"
                "Exécution simultanée : **bloquée**"
            ),
            inline=True,
        )
        if report.missing_permissions:
            e.add_field(name="Permissions manquantes", value="\n".join(f"• {item}" for item in report.missing_permissions), inline=False)
        if report.collisions:
            e.add_field(name="Doublons à corriger avant installation", value=format_collisions(list(report.collisions)), inline=False)
        if report.module_warnings:
            e.add_field(name="Modules indisponibles", value="\n".join(f"• {item}" for item in report.module_warnings), inline=False)
        if report.hierarchy_warnings:
            e.add_field(
                name="Hiérarchie à surveiller",
                value="Le rôle du bot n’est pas au-dessus de : " + ", ".join(f"**{name}**" for name in report.hierarchy_warnings[:8]),
                inline=False,
            )
        e.add_field(
            name="Ce que le setup configure",
            value="Accueil • aide rapide • guides • assistant IA • formations • boutique • tickets • recrutement • Premium • Guardian • permissions • logs.",
            inline=False,
        )
        e.set_image(url=BANNER_URL)
        e.set_footer(text="Choisis Installer / réparer, Vérifier seulement ou Annuler")
        return e

    def _progress_embed(self, current: int, detail: str) -> discord.Embed:
        lines = []
        for index, stage in enumerate(SETUP_STAGES):
            if index < current:
                mark = "✅"
            elif index == current:
                mark = "⏳"
            else:
                mark = "▫️"
            lines.append(f"{mark} **{stage}**")
        e = discord.Embed(
            title="Aide Bot — Setup en cours",
            description="\n".join(lines),
            color=SETUP_COLOR,
        )
        e.add_field(name="Étape actuelle", value=detail[:1024], inline=False)
        e.set_footer(text="Ne relance pas /setup pendant cette installation")
        return e

    def _verification_embed(self, guild: discord.Guild, report: SetupPreflight) -> discord.Embed:
        audit = audit_guild(guild)
        expected_channels = [name for _category, names in CATEGORY_SPECS for name in names]
        present_channels = sum(1 for name in expected_channels if discord.utils.get(guild.text_channels, name=name) is not None)
        present_roles = sum(1 for name, _color, _perms in ROLE_SPECS if discord.utils.get(guild.roles, name=name) is not None)
        healthy = not report.blocked and present_channels == len(expected_channels) and present_roles == len(ROLE_SPECS)
        e = discord.Embed(
            title="Vérification Aide Bot — " + ("OK" if healthy else "À corriger"),
            color=SUCCESS if healthy else WARNING,
        )
        e.add_field(name="Rôles", value=f"**{present_roles}/{len(ROLE_SPECS)}** présents", inline=True)
        e.add_field(name="Salons", value=f"**{present_channels}/{len(expected_channels)}** présents", inline=True)
        e.add_field(name="Guardian", value=f"**{audit.score}/100**", inline=True)
        e.add_field(
            name="Préflight",
            value=(
                f"Permissions manquantes : **{len(report.missing_permissions)}**\n"
                f"Collisions : **{len(report.collisions)}**\n"
                f"Mauvaise catégorie : **{report.channels_to_move}**\n"
                f"Modules indisponibles : **{len(report.module_warnings)}**"
            ),
            inline=False,
        )
        if audit.risks:
            e.add_field(
                name="Risques principaux",
                value="\n".join(f"• **{risk.severity.upper()}** — {risk.title}" for risk in audit.risks[:6]),
                inline=False,
            )
        e.set_footer(text="Vérification uniquement : aucune modification effectuée")
        return e

    async def _publish_panels(self, guild: discord.Guild, channels: dict[str, discord.TextChannel], roles: dict[str, discord.Role]) -> list[tuple[str, str]]:
        base = self._base_setup()
        assert base is not None
        actions: list[tuple[str, str]] = []

        async def upsert(label: str, channel_name: str, embed: discord.Embed, view: discord.ui.View | None = None) -> None:
            actions.append((label, await base._upsert_panel(channels.get(channel_name), embed, view)))

        await upsert("Bienvenue", "👋・bienvenue", product_v51.welcome_embed_v51(), product_v51.WelcomeViewV51(self.bot))
        await upsert("Règlement", "📜・règlement", base._rules_embed())
        await upsert("Centre d’aide", "🎓・centre-aide", help_home_embed(), HelpHomeView(self.bot))
        await upsert("Aide rapide", QUICK_CHANNEL, quick_help_embed(), QuickHelpView(self.bot))
        await upsert("Guides", GUIDES_CHANNEL, guides_home_embed(), GuidesView(self.bot))

        training = self.bot.get_cog("TrainingCog")
        if training is not None:
            await upsert("Formations", "🎓・formations", base._training_embed(), TrainingPanel(training))
        else:
            actions.append(("Formations", "absent"))

        guardian = self.bot.get_cog("AssistantGuardianV52Cog")
        if guardian is not None:
            await upsert("Assistant IA", AI_CHANNEL, assistant_panel_embed(guardian.ai.configured), AssistantPanelView(guardian))
            await upsert("Guardian", STAFF_CHANNEL, guardian_panel_embed(), GuardianPanelView(guardian))
        else:
            actions.extend((("Assistant IA", "absent"), ("Guardian", "absent")))

        await upsert("Boutique", "🛒・shop", product_v51.shop_embed_v51(self.bot.settings.vip_price_robux), product_v51.ShopViewV51(self.bot))
        await upsert("Tickets", "🎫・ouvrir-ticket", ticket_embed(), TicketEntryView(self.bot))
        await upsert("Recrutement", "🧑‍🏫・recrutement", recruitment_embed(), RecruitmentView(self.bot))
        await upsert("Premium", "💎・espace-premium", product_v51.premium_hub_embed_v51(), product_v51.PremiumHubViewV51(self.bot))
        return actions

    async def verify_only(self, interaction: discord.Interaction) -> None:
        if not self._authorized(interaction) or interaction.guild is None:
            return await interaction.response.send_message("Le setup est réservé au propriétaire ou à un administrateur.", ephemeral=True)
        report = self._preflight(interaction.guild)
        await interaction.response.edit_message(embed=self._verification_embed(interaction.guild, report), view=None)

    async def run_setup(self, interaction: discord.Interaction) -> None:
        if not self._authorized(interaction) or interaction.guild is None:
            return await interaction.response.send_message("Le setup est réservé au propriétaire ou à un administrateur.", ephemeral=True)

        guild = interaction.guild
        lock = self._lock_for(guild.id)
        if lock.locked():
            return await interaction.response.send_message("Un setup est déjà en cours sur ce serveur. Attends qu’il se termine.", ephemeral=True)

        report = self._preflight(guild)
        if report.blocked:
            return await interaction.response.edit_message(embed=self._preflight_embed(guild, report), view=SetupSessionView(self, interaction.user.id, install_disabled=True))

        await interaction.response.edit_message(embed=self._progress_embed(0, "Préflight validé. Préparation de la sauvegarde…"), view=None)

        async with lock:
            created_roles = reused_roles = 0
            created_categories = reused_categories = 0
            created_channels = reused_channels = moved_channels = 0
            permission_updates = 0
            migrated_channels = 0
            failures: list[str] = []
            panel_actions: list[tuple[str, str]] = []
            snapshot_path: Path | None = None
            base = self._base_setup()
            if base is None:
                return await interaction.edit_original_response(
                    embed=discord.Embed(title="Setup interrompu", description="Le moteur de setup n’est plus disponible.", color=DANGER)
                )

            try:
                await interaction.edit_original_response(embed=self._progress_embed(1, "Création d’un snapshot de la structure actuelle, sans messages."))
                snapshot_path = await self.snapshots.save(guild)

                await interaction.edit_original_response(embed=self._progress_embed(2, "Migration sûre des anciens noms connus."))
                migrated_channels += await base._migrate_legacy_channels(guild)
                old_video = discord.utils.get(guild.text_channels, name=LEGACY_VIDEO_CHANNEL)
                ai_channel = discord.utils.get(guild.text_channels, name=AI_CHANNEL)
                if old_video is not None and ai_channel is None:
                    try:
                        await old_video.edit(name=AI_CHANNEL, reason="Aide Bot — migration vers Assistant IA")
                        migrated_channels += 1
                    except (discord.Forbidden, discord.HTTPException) as exc:
                        failures.append(f"Migration Assistant IA: {type(exc).__name__}")

                await interaction.edit_original_response(embed=self._progress_embed(3, "Création ou réutilisation des rôles Aide Bot."))
                roles: dict[str, discord.Role] = {}
                for name, color, perm_spec in reversed(ROLE_SPECS):
                    role = discord.utils.get(guild.roles, name=name)
                    if role is None:
                        try:
                            role = await guild.create_role(
                                name=name,
                                colour=discord.Colour(color),
                                permissions=role_permissions(perm_spec),
                                reason="Aide Bot — installation",
                            )
                            created_roles += 1
                        except (discord.Forbidden, discord.HTTPException) as exc:
                            failures.append(f"Rôle {name}: {type(exc).__name__}")
                            continue
                    else:
                        reused_roles += 1
                    roles[name] = role

                essential_roles = {name for name, _color, _perm in ROLE_SPECS}
                if not essential_roles.issubset(roles):
                    missing = sorted(essential_roles - set(roles))
                    raise RuntimeError("Rôles essentiels impossibles à préparer : " + ", ".join(missing))

                await interaction.edit_original_response(embed=self._progress_embed(4, "Réconciliation des catégories et salons. Aucun salon personnel n’est supprimé."))
                channels: dict[str, discord.TextChannel] = {}
                categories: dict[str, discord.CategoryChannel] = {}
                for category_name, channel_names in CATEGORY_SPECS:
                    category = discord.utils.get(guild.categories, name=category_name)
                    if category is None:
                        try:
                            category = await guild.create_category(category_name, reason="Aide Bot — installation")
                            created_categories += 1
                        except (discord.Forbidden, discord.HTTPException) as exc:
                            failures.append(f"Catégorie {category_name}: {type(exc).__name__}")
                            continue
                    else:
                        reused_categories += 1
                    categories[category_name] = category

                    for channel_name in channel_names:
                        channel = discord.utils.get(guild.text_channels, name=channel_name)
                        if channel is None:
                            try:
                                channel = await guild.create_text_channel(channel_name, category=category, reason="Aide Bot — installation")
                                created_channels += 1
                            except (discord.Forbidden, discord.HTTPException) as exc:
                                failures.append(f"Salon {channel_name}: {type(exc).__name__}")
                                continue
                        else:
                            reused_channels += 1
                            if channel.category_id != category.id:
                                try:
                                    await channel.edit(category=category, reason="Aide Bot — catégorie canonique")
                                    moved_channels += 1
                                except (discord.Forbidden, discord.HTTPException) as exc:
                                    failures.append(f"Déplacement {channel_name}: {type(exc).__name__}")
                        channels[channel_name] = channel

                await interaction.edit_original_response(embed=self._progress_embed(5, "Application des permissions publiques, Premium et staff."))
                for category in categories.values():
                    try:
                        await base._reconcile_category_permissions(guild, category, roles)
                        permission_updates += 1
                    except (discord.Forbidden, discord.HTTPException) as exc:
                        failures.append(f"Permissions catégorie {category.name}: {type(exc).__name__}")
                for channel in channels.values():
                    try:
                        await base._reconcile_channel_permissions(guild, channel, roles)
                        permission_updates += 1
                    except (discord.Forbidden, discord.HTTPException) as exc:
                        failures.append(f"Permissions salon {channel.name}: {type(exc).__name__}")

                help_cog = self.bot.get_cog("HelpSystemV54Cog")
                if help_cog is not None:
                    for name in ("🎓・centre-aide", QUICK_CHANNEL, GUIDES_CHANNEL):
                        channel = channels.get(name)
                        if channel is not None:
                            await help_cog._configure_channel(channel)

                await interaction.edit_original_response(embed=self._progress_embed(6, "Publication et réparation des panneaux utiles, sans mur de boutons."))
                bienvenue = channels.get("👋・bienvenue")
                if bienvenue is not None:
                    await base._remove_legacy_bot_embeds(bienvenue, base.LEGACY_WELCOME_TITLES if hasattr(base, "LEGACY_WELCOME_TITLES") else set())
                panel_actions = await self._publish_panels(guild, channels, roles)

                assistant_setup = self.bot.get_cog("AssistantGuardianSetupV52Cog")
                if assistant_setup is not None:
                    await assistant_setup._reconcile(guild)

                guardian = self.bot.get_cog("AssistantGuardianV52Cog")
                if guardian is not None:
                    current = snapshot_guild(guild)
                    await guardian.store.save_baseline(guild, current)
                    guardian._last_reported_hash.pop(guild.id, None)

                await interaction.edit_original_response(embed=self._progress_embed(7, "Contrôle final de la structure, des modules et de Guardian."))
                final_report = self._preflight(guild)
                audit = audit_guild(guild)
                panel_failures = [(name, state) for name, state in panel_actions if state in {"failed", "skipped", "absent"}]
                failures.extend(f"Panneau {name}: {state}" for name, state in panel_failures)

                expected_channels = [name for _category, names in CATEGORY_SPECS for name in names]
                present_channels = sum(1 for name in expected_channels if discord.utils.get(guild.text_channels, name=name) is not None)
                present_roles = sum(1 for name, _color, _perm in ROLE_SPECS if discord.utils.get(guild.roles, name=name) is not None)
                complete = not final_report.blocked and present_channels == len(expected_channels) and present_roles == len(ROLE_SPECS) and not failures

                result = discord.Embed(
                    title="Setup Aide Bot terminé" if complete else "Setup Aide Bot terminé avec vérifications",
                    description=(
                        "La structure Aide Bot a été installée/réparée de façon **idempotente** : relancer `/setup` réutilise les éléments existants au lieu de tout recréer. "
                        "Aucun salon ou rôle personnel n’a été supprimé."
                    ),
                    color=SUCCESS if complete else WARNING,
                )
                result.add_field(
                    name="Structure",
                    value=(
                        f"Rôles : **{created_roles} créés / {reused_roles} réutilisés**\n"
                        f"Catégories : **{created_categories} créées / {reused_categories} réutilisées**\n"
                        f"Salons : **{created_channels} créés / {reused_channels} réutilisés**\n"
                        f"Salons replacés : **{moved_channels}** • migrations : **{migrated_channels}**"
                    ),
                    inline=True,
                )
                ok_panels = len(panel_actions) - len(panel_failures)
                result.add_field(
                    name="Modules",
                    value=(
                        f"Panneaux : **{ok_panels}/{len(panel_actions)} OK**\n"
                        f"Permissions traitées : **{permission_updates}**\n"
                        f"Guardian : **{audit.score}/100**\n"
                        f"Structure : **{present_channels}/{len(expected_channels)} salons**"
                    ),
                    inline=True,
                )
                result.add_field(
                    name="Sauvegarde de sécurité",
                    value=(
                        f"Snapshot créé : **{snapshot_path.name if snapshot_path else 'indisponible'}**\n"
                        "Il contient la structure/permissions, **pas les messages**. Les 3 dernières sauvegardes sont conservées."
                    ),
                    inline=False,
                )
                result.add_field(
                    name="Système d’aide",
                    value="Centre d’aide • Aide rapide • Guides • Assistant IA • Formations sont configurés comme des fonctions différentes, avec seulement quelques salons dédiés.",
                    inline=False,
                )
                if final_report.hierarchy_warnings:
                    result.add_field(
                        name="Hiérarchie",
                        value="Place le rôle d’Aide Bot au-dessus des rôles qu’il doit attribuer : " + ", ".join(final_report.hierarchy_warnings[:6]),
                        inline=False,
                    )
                if failures:
                    result.add_field(name="À vérifier", value="\n".join(f"• {item}" for item in failures[:10])[:1024], inline=False)
                result.set_image(url=BANNER_URL)
                result.set_footer(text="Relancer /setup = vérifier et réparer, pas dupliquer le serveur")

                log_channel = channels.get("🧾・logs")
                if log_channel is not None:
                    try:
                        await log_channel.send(
                            embed=discord.Embed(
                                title="Setup exécuté",
                                description=(
                                    f"Par {interaction.user.mention} • {present_channels}/{len(expected_channels)} salons • "
                                    f"{ok_panels}/{len(panel_actions)} panneaux • Guardian {audit.score}/100"
                                ),
                                color=0x2B2D31,
                            ),
                            allowed_mentions=discord.AllowedMentions.none(),
                        )
                    except (discord.Forbidden, discord.HTTPException):
                        pass

                await interaction.edit_original_response(embed=result)
            except Exception as exc:
                error = discord.Embed(
                    title="Setup interrompu en sécurité",
                    description=(
                        "Une erreur a arrêté l’installation avant la fin. Les éléments déjà créés ne sont pas supprimés automatiquement pour éviter d’endommager le serveur. "
                        "Relance `/setup` après correction : il reprendra en réutilisant ce qui existe."
                    ),
                    color=DANGER,
                )
                error.add_field(name="Erreur", value=f"`{type(exc).__name__}: {str(exc)[:700]}`", inline=False)
                if snapshot_path is not None:
                    error.add_field(name="Snapshot avant setup", value=f"`{snapshot_path.name}`", inline=False)
                await interaction.edit_original_response(embed=error)

    @app_commands.command(name="setup", description="Analyser, installer ou réparer Aide Bot en sécurité")
    @app_commands.guild_only()
    async def setup_command(self, interaction: discord.Interaction) -> None:
        if not self._authorized(interaction) or interaction.guild is None:
            return await interaction.response.send_message(
                "Le setup est réservé au propriétaire du serveur ou à un administrateur Discord.",
                ephemeral=True,
            )
        report = self._preflight(interaction.guild)
        await interaction.response.send_message(
            embed=self._preflight_embed(interaction.guild, report),
            view=SetupSessionView(self, interaction.user.id, install_disabled=report.blocked),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    # Remplace proprement l’ancienne surface /setup sans muter callback,
    # ce qui évite l’incident discord.py rencontré sur une ancienne version.
    bot.tree.remove_command("setup")
    await bot.add_cog(SetupExperienceV55Cog(bot))
