from __future__ import annotations

import asyncio
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands

from aidebot.cogs.assistant_guardian_v52 import (
    GUARDIAN_TITLE,
    GuardianPanelView,
    _upsert_panel,
    guardian_panel_embed,
)
from aidebot.cogs.setup_experience_v55 import SetupExperienceV55Cog
from aidebot.experience_content import BANNER_URL
from aidebot.guardian import audit_guild, effective_permissions_for_roles
from aidebot.message_reconcile import find_bot_embed_by_title
from aidebot.permissions import decide

COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F
DANGER = 0xED4245
STAFF_CHANNEL = "📋・staff"
POWER_TITLE = "Aide Bot — Outils avancés"
STAFF_TOPIC = (
    "Outils administration : Server Doctor, Permission Lab, Guardian, Mode incident et Studio de structure."
)

SENSITIVE_EVERYONE_PERMISSIONS = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "mention_everyone",
)

KEY_PERMISSION_GROUPS = {
    "Accès": (
        "view_channel",
        "send_messages",
        "read_message_history",
        "connect",
        "speak",
    ),
    "Modération": (
        "manage_messages",
        "moderate_members",
        "kick_members",
        "ban_members",
    ),
    "Administration": (
        "manage_channels",
        "manage_roles",
        "manage_webhooks",
        "manage_guild",
        "mention_everyone",
        "administrator",
    ),
}

PERMISSION_LABELS = {
    "view_channel": "Voir le salon",
    "send_messages": "Envoyer des messages",
    "read_message_history": "Lire l’historique",
    "connect": "Se connecter au vocal",
    "speak": "Parler en vocal",
    "manage_messages": "Gérer les messages",
    "moderate_members": "Exclure temporairement",
    "kick_members": "Expulser",
    "ban_members": "Bannir",
    "manage_channels": "Gérer les salons",
    "manage_roles": "Gérer les rôles",
    "manage_webhooks": "Gérer les webhooks",
    "manage_guild": "Gérer le serveur",
    "mention_everyone": "Mentionner everyone/here",
    "administrator": "Administrateur",
}


@dataclass(frozen=True)
class BlueprintChannel:
    name: str
    kind: str = "text"
    read_only: bool = False


@dataclass(frozen=True)
class BlueprintCategory:
    name: str
    channels: tuple[BlueprintChannel, ...]


@dataclass(frozen=True)
class Blueprint:
    label: str
    description: str
    roles: tuple[str, ...]
    categories: tuple[BlueprintCategory, ...]


BLUEPRINTS: dict[str, Blueprint] = {
    "community": Blueprint(
        label="Communauté",
        description="Structure compacte pour communauté générale, événements et médias.",
        roles=("Modérateur", "Membre"),
        categories=(
            BlueprintCategory(
                "INFORMATIONS",
                (
                    BlueprintChannel("règlement", read_only=True),
                    BlueprintChannel("annonces", read_only=True),
                ),
            ),
            BlueprintCategory(
                "COMMUNAUTÉ",
                (
                    BlueprintChannel("général"),
                    BlueprintChannel("médias"),
                    BlueprintChannel("suggestions"),
                    BlueprintChannel("Général", kind="voice"),
                ),
            ),
            BlueprintCategory(
                "ÉVÉNEMENTS",
                (
                    BlueprintChannel("événements"),
                    BlueprintChannel("inscriptions"),
                ),
            ),
        ),
    ),
    "gaming": Blueprint(
        label="Gaming",
        description="Serveur jeu avec recherche de groupe, clips et vocaux dédiés.",
        roles=("Modérateur", "Joueur"),
        categories=(
            BlueprintCategory(
                "START",
                (
                    BlueprintChannel("règlement", read_only=True),
                    BlueprintChannel("annonces", read_only=True),
                ),
            ),
            BlueprintCategory(
                "JEU",
                (
                    BlueprintChannel("général"),
                    BlueprintChannel("recherche-groupe"),
                    BlueprintChannel("clips"),
                    BlueprintChannel("guides"),
                    BlueprintChannel("Escouade 1", kind="voice"),
                    BlueprintChannel("Escouade 2", kind="voice"),
                ),
            ),
        ),
    ),
    "creator": Blueprint(
        label="Créateur",
        description="Serveur pour créateur avec annonces, communauté, contenus et collaborations.",
        roles=("Modérateur", "Créateur", "Membre"),
        categories=(
            BlueprintCategory(
                "OFFICIEL",
                (
                    BlueprintChannel("annonces", read_only=True),
                    BlueprintChannel("nouveaux-contenus", read_only=True),
                ),
            ),
            BlueprintCategory(
                "COMMUNAUTÉ",
                (
                    BlueprintChannel("général"),
                    BlueprintChannel("fan-art"),
                    BlueprintChannel("suggestions"),
                    BlueprintChannel("Communauté", kind="voice"),
                ),
            ),
            BlueprintCategory(
                "COLLABORATIONS",
                (
                    BlueprintChannel("demandes-collab"),
                    BlueprintChannel("projets"),
                ),
            ),
        ),
    ),
    "support": Blueprint(
        label="Support",
        description="Structure dédiée au support client, statut, FAQ et retours.",
        roles=("Support", "Responsable Support", "Client"),
        categories=(
            BlueprintCategory(
                "INFORMATIONS",
                (
                    BlueprintChannel("statut-service", read_only=True),
                    BlueprintChannel("faq", read_only=True),
                ),
            ),
            BlueprintCategory(
                "SUPPORT",
                (
                    BlueprintChannel("ouvrir-une-demande"),
                    BlueprintChannel("questions"),
                    BlueprintChannel("retours"),
                ),
            ),
            BlueprintCategory(
                "ÉQUIPE",
                (
                    BlueprintChannel("suivi-support"),
                    BlueprintChannel("Support", kind="voice"),
                ),
            ),
        ),
    ),
}


class PowerStateStore:
    """Small persistent state for reversible V58 actions.

    It stores only permission values and ids created by the blueprint builder;
    no Discord messages or member content are stored.
    """

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._lock = asyncio.Lock()

    def _read_sync(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"guilds": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"guilds": {}}
        if not isinstance(payload, dict):
            return {"guilds": {}}
        payload.setdefault("guilds", {})
        return payload

    def _write_sync(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    async def _mutate(self, guild_id: int, key: str, value: Any | None) -> None:
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            guilds = payload.setdefault("guilds", {})
            guild_state = guilds.setdefault(str(guild_id), {})
            if value is None:
                guild_state.pop(key, None)
            else:
                guild_state[key] = value
            await asyncio.to_thread(self._write_sync, payload)

    async def get(self, guild_id: int, key: str) -> Any | None:
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            state = payload.get("guilds", {}).get(str(guild_id), {})
            return state.get(key) if isinstance(state, dict) else None

    async def save_incident(self, guild_id: int, permissions_value: int) -> None:
        await self._mutate(guild_id, "incident", {"everyone_permissions": int(permissions_value)})

    async def clear_incident(self, guild_id: int) -> None:
        await self._mutate(guild_id, "incident", None)

    async def save_build(self, guild_id: int, payload: dict[str, Any]) -> None:
        await self._mutate(guild_id, "last_build", payload)

    async def clear_build(self, guild_id: int) -> None:
        await self._mutate(guild_id, "last_build", None)


def staff_power_embed_v58() -> discord.Embed:
    e = discord.Embed(
        title=POWER_TITLE,
        description=(
            "Un seul panneau staff pour les outils qui changent réellement la gestion d’un serveur. "
            "Choisis une action dans le menu : chaque outil a un rôle différent."
        ),
        color=COLOR,
    )
    e.add_field(name="Server Doctor", value="Score le serveur, détecte les risques et donne les priorités à corriger.", inline=True)
    e.add_field(name="Permission Lab", value="Simule les permissions réelles d’un membre ou d’un rôle dans un salon précis.", inline=True)
    e.add_field(name="Guardian", value="État sûr, changements détectés et restauration contrôlée des permissions.", inline=True)
    e.add_field(name="Mode incident", value="Retire temporairement les permissions dangereuses de @everyone puis permet de les rétablir.", inline=True)
    e.add_field(name="Studio structure", value="Prévisualise puis construit une structure Community, Gaming, Creator ou Support sans écraser l’existant.", inline=True)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • outils staff visibles • actions sensibles confirmées")
    return e


@dataclass(frozen=True)
class DoctorReport:
    score: int
    status: str
    findings: tuple[str, ...]
    metrics: dict[str, int]


def server_doctor(guild: discord.Guild) -> DoctorReport:
    guardian = audit_guild(guild)
    findings: list[str] = [f"[{risk.severity.upper()}] {risk.title} — {risk.detail}" for risk in guardian.risks]
    score = int(guardian.score)

    duplicate_names: dict[str, int] = {}
    for channel in guild.channels:
        duplicate_names[channel.name] = duplicate_names.get(channel.name, 0) + 1
    duplicates = sum(1 for count in duplicate_names.values() if count > 1)

    empty_categories = sum(1 for category in guild.categories if not category.channels)
    uncategorized = sum(1 for channel in guild.text_channels if channel.category is None)
    admin_roles = sum(1 for role in guild.roles if role != guild.default_role and role.permissions.administrator)

    me = guild.me
    if me is None:
        findings.insert(0, "[CRITICAL] Impossible d’identifier le rôle du bot dans ce serveur.")
        score -= 25
    else:
        for permission, label in (
            ("manage_roles", "Gérer les rôles"),
            ("manage_channels", "Gérer les salons"),
            ("view_audit_log", "Voir le journal d’audit"),
        ):
            if not getattr(me.guild_permissions, permission, False):
                findings.insert(0, f"[HIGH] Aide Bot n’a pas la permission **{label}**.")
                score -= 8
        blocked_roles = sum(1 for role in guild.roles if not role.managed and role != guild.default_role and role >= me.top_role)
        if blocked_roles:
            findings.append(f"[MEDIUM] {blocked_roles} rôle(s) sont au-dessus du rôle Aide Bot et ne peuvent pas être gérés par lui.")
            score -= min(12, blocked_roles * 2)

    if empty_categories:
        findings.append(f"[LOW] {empty_categories} catégorie(s) vide(s) peuvent être nettoyées.")
        score -= min(6, empty_categories * 2)
    if uncategorized > 4:
        findings.append(f"[LOW] {uncategorized} salons texte sont hors catégorie ; la navigation peut devenir confuse.")
        score -= 4
    if duplicates:
        findings.append(f"[LOW] {duplicates} nom(s) de salon/catégorie sont utilisés plusieurs fois.")
        score -= min(6, duplicates * 2)

    score = max(0, min(100, score))
    if score >= 90:
        status = "Excellent"
    elif score >= 75:
        status = "Solide"
    elif score >= 55:
        status = "À améliorer"
    else:
        status = "Risque élevé"
    metrics = {
        "roles": len(guild.roles),
        "channels": len(guild.channels),
        "admin_roles": admin_roles,
        "empty_categories": empty_categories,
        "uncategorized_text": uncategorized,
        "duplicate_names": duplicates,
    }
    return DoctorReport(score, status, tuple(findings), metrics)


def doctor_embed_v58(guild: discord.Guild, report: DoctorReport) -> discord.Embed:
    color = SUCCESS if report.score >= 75 else WARNING if report.score >= 55 else DANGER
    e = discord.Embed(
        title=f"Server Doctor — {report.score}/100",
        description=f"État : **{report.status}**. Analyse de la structure, de la hiérarchie et des permissions sensibles.",
        color=color,
    )
    e.add_field(
        name="Inventaire",
        value=(
            f"Rôles : **{report.metrics['roles']}**\n"
            f"Salons/catégories : **{report.metrics['channels']}**\n"
            f"Rôles Administrateur : **{report.metrics['admin_roles']}**"
        ),
        inline=True,
    )
    e.add_field(
        name="Organisation",
        value=(
            f"Catégories vides : **{report.metrics['empty_categories']}**\n"
            f"Salons hors catégorie : **{report.metrics['uncategorized_text']}**\n"
            f"Noms en double : **{report.metrics['duplicate_names']}**"
        ),
        inline=True,
    )
    if report.findings:
        e.add_field(name="Priorités", value="\n".join(f"• {item}" for item in report.findings[:8])[:1024], inline=False)
    else:
        e.add_field(name="Priorités", value="Aucun problème important détecté dans l’analyse actuelle.", inline=False)
    e.set_footer(text="Server Doctor analyse la configuration, pas le contenu privé des messages")
    return e


def doctor_payload(guild: discord.Guild, report: DoctorReport) -> bytes:
    payload = {
        "guild": {"id": guild.id, "name": guild.name},
        "score": report.score,
        "status": report.status,
        "metrics": report.metrics,
        "findings": list(report.findings),
        "contains_messages": False,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _yes_no(value: bool) -> str:
    return "Oui" if value else "Non"


def permission_embed_v58(target: str, channel: discord.abc.GuildChannel, permissions: discord.Permissions) -> discord.Embed:
    color = DANGER if permissions.administrator else COLOR
    e = discord.Embed(
        title="Permission Lab",
        description=f"Simulation pour **{target}** dans **#{channel.name}**.",
        color=color,
    )
    for group, names in KEY_PERMISSION_GROUPS.items():
        lines = [f"**{PERMISSION_LABELS[name]}** : {_yes_no(bool(getattr(permissions, name, False)))}" for name in names]
        e.add_field(name=group, value="\n".join(lines), inline=False)
    if permissions.administrator:
        e.add_field(
            name="Attention",
            value="Administrateur contourne la majorité des restrictions de salon. Une simulation détaillée des overwrites devient secondaire.",
            inline=False,
        )
    e.set_footer(text="Permission Lab calcule le résultat effectif dans le salon choisi")
    return e


def blueprint_embed_v58(key: str) -> discord.Embed:
    blueprint = BLUEPRINTS[key]
    channel_count = sum(len(category.channels) for category in blueprint.categories)
    e = discord.Embed(
        title=f"Studio structure — {blueprint.label}",
        description=blueprint.description,
        color=COLOR,
    )
    e.add_field(name="Rôles", value=" • ".join(blueprint.roles), inline=False)
    for category in blueprint.categories:
        lines = []
        for channel in category.channels:
            kind = "Vocal" if channel.kind == "voice" else "Texte"
            suffix = " • lecture seule" if channel.read_only else ""
            lines.append(f"• {channel.name} — {kind}{suffix}")
        e.add_field(name=category.name, value="\n".join(lines), inline=False)
    e.set_footer(text=f"Prévisualisation non destructive • {channel_count} salons prévus")
    return e


def blueprint_payload(key: str) -> bytes:
    blueprint = BLUEPRINTS[key]
    payload = {
        "template": key,
        "label": blueprint.label,
        "description": blueprint.description,
        "roles": list(blueprint.roles),
        "categories": [
            {
                "name": category.name,
                "channels": [
                    {"name": channel.name, "kind": channel.kind, "read_only": channel.read_only}
                    for channel in category.channels
                ],
            }
            for category in blueprint.categories
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _clean_snowflake(text: str) -> int | None:
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _resolve_channel(guild: discord.Guild, text: str) -> discord.abc.GuildChannel | None:
    snowflake = _clean_snowflake(text)
    if snowflake:
        channel = guild.get_channel(snowflake)
        if channel is not None:
            return channel
    needle = text.strip().lstrip("#").casefold()
    return next((channel for channel in guild.channels if channel.name.casefold() == needle), None)


def _resolve_target(guild: discord.Guild, text: str) -> tuple[str, discord.Member | discord.Role] | None:
    snowflake = _clean_snowflake(text)
    if snowflake:
        member = guild.get_member(snowflake)
        if member is not None:
            return member.display_name, member
        role = guild.get_role(snowflake)
        if role is not None:
            return role.name, role
    needle = text.strip().lstrip("@").casefold()
    member = next(
        (
            member
            for member in guild.members
            if member.display_name.casefold() == needle or member.name.casefold() == needle
        ),
        None,
    )
    if member is not None:
        return member.display_name, member
    role = next((role for role in guild.roles if role.name.casefold() == needle), None)
    return (role.name, role) if role is not None else None


class DoctorResultViewV58(discord.ui.View):
    def __init__(self, guild: discord.Guild, report: DoctorReport) -> None:
        super().__init__(timeout=600)
        self.guild = guild
        self.report = report

    @discord.ui.button(label="Exporter le rapport", style=discord.ButtonStyle.secondary)
    async def export(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        payload = doctor_payload(self.guild, self.report)
        await interaction.response.send_message(
            file=discord.File(io.BytesIO(payload), filename=f"server-doctor-{self.guild.id}.json"),
            ephemeral=True,
        )


class PermissionLabModalV58(discord.ui.Modal, title="Permission Lab"):
    target = discord.ui.TextInput(
        label="Membre ou rôle",
        placeholder="Mention, ID ou nom exact",
        max_length=120,
    )
    channel = discord.ui.TextInput(
        label="Salon",
        placeholder="#salon, ID ou nom exact",
        max_length=120,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "audit.run").allowed:
            return await interaction.response.send_message("Permission Lab est réservé au staff autorisé.", ephemeral=True)
        resolved_target = _resolve_target(interaction.guild, str(self.target))
        resolved_channel = _resolve_channel(interaction.guild, str(self.channel))
        if resolved_target is None:
            return await interaction.response.send_message("Membre/rôle introuvable. Utilise une mention, un ID ou le nom exact.", ephemeral=True)
        if resolved_channel is None:
            return await interaction.response.send_message("Salon introuvable. Utilise une mention, un ID ou le nom exact.", ephemeral=True)

        label, target = resolved_target
        if isinstance(target, discord.Member):
            permissions = resolved_channel.permissions_for(target)
        else:
            roles = [] if target == interaction.guild.default_role else [target]
            permissions = effective_permissions_for_roles(interaction.guild, resolved_channel, roles)
        await interaction.response.send_message(
            embed=permission_embed_v58(label, resolved_channel, permissions),
            ephemeral=True,
        )


class IncidentConfirmModalV58(discord.ui.Modal, title="Activer le mode incident"):
    confirmation = discord.ui.TextInput(label="Écris PROTEGER", placeholder="PROTEGER", max_length=12)

    def __init__(self, cog: "PowerSuiteV58Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Cette action est réservée à la Direction.", ephemeral=True)
        if str(self.confirmation).strip().upper() != "PROTEGER":
            return await interaction.response.send_message("Confirmation incorrecte. Rien n’a été modifié.", ephemeral=True)
        await self.cog.activate_incident(interaction)


class IncidentRestoreModalV58(discord.ui.Modal, title="Rétablir avant incident"):
    confirmation = discord.ui.TextInput(label="Écris RETABLIR", placeholder="RETABLIR", max_length=12)

    def __init__(self, cog: "PowerSuiteV58Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Cette action est réservée à la Direction.", ephemeral=True)
        if str(self.confirmation).strip().upper() != "RETABLIR":
            return await interaction.response.send_message("Confirmation incorrecte. Rien n’a été modifié.", ephemeral=True)
        await self.cog.restore_incident(interaction)


class IncidentViewV58(discord.ui.View):
    def __init__(self, cog: "PowerSuiteV58Cog") -> None:
        super().__init__(timeout=600)
        self.cog = cog

    @discord.ui.button(label="Activer la protection", style=discord.ButtonStyle.danger)
    async def activate(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(IncidentConfirmModalV58(self.cog))

    @discord.ui.button(label="Rétablir l’état précédent", style=discord.ButtonStyle.secondary)
    async def restore(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(IncidentRestoreModalV58(self.cog))


class BlueprintBuildModalV58(discord.ui.Modal, title="Construire la structure"):
    confirmation = discord.ui.TextInput(label="Écris CONSTRUIRE", placeholder="CONSTRUIRE", max_length=12)

    def __init__(self, cog: "PowerSuiteV58Cog", key: str) -> None:
        super().__init__()
        self.cog = cog
        self.key = key

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("La construction est réservée à la Direction.", ephemeral=True)
        if str(self.confirmation).strip().upper() != "CONSTRUIRE":
            return await interaction.response.send_message("Confirmation incorrecte. Aucune structure n’a été créée.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await self.cog.build_blueprint(interaction.guild, self.key)
        await interaction.followup.send(
            (
                f"Structure **{BLUEPRINTS[self.key].label}** terminée : "
                f"**{result['roles']} rôle(s)**, **{result['categories']} catégorie(s)** et **{result['channels']} salon(s)** créés. "
                f"Éléments déjà présents : **{result['skipped']}**."
            ),
            ephemeral=True,
        )


class BlueprintUndoModalV58(discord.ui.Modal, title="Annuler la dernière structure"):
    confirmation = discord.ui.TextInput(label="Écris ANNULER", placeholder="ANNULER", max_length=10)

    def __init__(self, cog: "PowerSuiteV58Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Cette action est réservée à la Direction.", ephemeral=True)
        if str(self.confirmation).strip().upper() != "ANNULER":
            return await interaction.response.send_message("Confirmation incorrecte. Rien n’a été supprimé.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await self.cog.undo_blueprint(interaction.guild)
        await interaction.followup.send(result, ephemeral=True)


class BlueprintPreviewViewV58(discord.ui.View):
    def __init__(self, cog: "PowerSuiteV58Cog", key: str) -> None:
        super().__init__(timeout=600)
        self.cog = cog
        self.key = key

    @discord.ui.button(label="Construire", style=discord.ButtonStyle.success)
    async def build(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(BlueprintBuildModalV58(self.cog, self.key))

    @discord.ui.button(label="Exporter le plan", style=discord.ButtonStyle.secondary)
    async def export(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            file=discord.File(io.BytesIO(blueprint_payload(self.key)), filename=f"blueprint-{self.key}.json"),
            ephemeral=True,
        )


class BlueprintSelectV58(discord.ui.Select):
    def __init__(self, cog: "PowerSuiteV58Cog") -> None:
        self.cog = cog
        super().__init__(
            placeholder="Choisis un type de serveur",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=blueprint.label, value=key, description=blueprint.description[:100])
                for key, blueprint in BLUEPRINTS.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        key = self.values[0]
        await interaction.response.send_message(
            embed=blueprint_embed_v58(key),
            view=BlueprintPreviewViewV58(self.cog, key),
            ephemeral=True,
        )


class BlueprintHomeViewV58(discord.ui.View):
    def __init__(self, cog: "PowerSuiteV58Cog") -> None:
        super().__init__(timeout=600)
        self.cog = cog
        self.add_item(BlueprintSelectV58(cog))

    @discord.ui.button(label="Annuler ma dernière création", style=discord.ButtonStyle.danger, row=1)
    async def undo(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(BlueprintUndoModalV58(self.cog))


class StaffPowerSelectV58(discord.ui.Select):
    def __init__(self, cog: "PowerSuiteV58Cog") -> None:
        self.cog = cog
        super().__init__(
            placeholder="Choisis un outil avancé",
            min_values=1,
            max_values=1,
            custom_id="aidebot:v58:staff:tool",
            options=[
                discord.SelectOption(label="Server Doctor", value="doctor", description="Score + risques + priorités à corriger"),
                discord.SelectOption(label="Permission Lab", value="permissions", description="Simuler membre/rôle dans un salon"),
                discord.SelectOption(label="Guardian", value="guardian", description="État sûr, différences et restauration"),
                discord.SelectOption(label="Mode incident", value="incident", description="Protection temporaire et réversible"),
                discord.SelectOption(label="Studio structure", value="blueprint", description="Prévisualiser et construire un serveur"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "audit.run").allowed:
            return await interaction.response.send_message("Ces outils sont réservés au staff autorisé.", ephemeral=True)

        choice = self.values[0]
        if choice == "doctor":
            report = server_doctor(interaction.guild)
            return await interaction.response.send_message(
                embed=doctor_embed_v58(interaction.guild, report),
                view=DoctorResultViewV58(interaction.guild, report),
                ephemeral=True,
            )
        if choice == "permissions":
            return await interaction.response.send_modal(PermissionLabModalV58())
        if choice == "guardian":
            core = interaction.client.get_cog("AssistantGuardianV52Cog")
            if core is None:
                return await interaction.response.send_message("Guardian est temporairement indisponible.", ephemeral=True)
            return await interaction.response.send_message(
                embed=guardian_panel_embed(),
                view=GuardianPanelView(core),
                ephemeral=True,
            )
        if choice == "incident":
            e = discord.Embed(
                title="Mode incident",
                description=(
                    "Protection d’urgence **réversible** : Aide Bot sauvegarde les permissions actuelles de `@everyone`, "
                    "puis retire uniquement les permissions administratives dangereuses présentes sur ce rôle."
                ),
                color=DANGER,
            )
            e.add_field(
                name="Ce que ça ne fait pas",
                value="Aucun salon n’est supprimé, aucun rôle n’est supprimé et aucun membre n’est sanctionné.",
                inline=False,
            )
            return await interaction.response.send_message(embed=e, view=IncidentViewV58(self.cog), ephemeral=True)
        if choice == "blueprint":
            e = discord.Embed(
                title="Studio structure",
                description=(
                    "Choisis un modèle. Tu verras le plan complet **avant** toute création. "
                    "La construction ajoute seulement les éléments manquants et n’écrase jamais ce qui existe déjà."
                ),
                color=COLOR,
            )
            return await interaction.response.send_message(embed=e, view=BlueprintHomeViewV58(self.cog), ephemeral=True)


class StaffPowerViewV58(discord.ui.View):
    def __init__(self, cog: "PowerSuiteV58Cog") -> None:
        super().__init__(timeout=None)
        self.add_item(StaffPowerSelectV58(cog))


class PowerSuiteV58Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        state_path = str(Path(bot.settings.db_path).with_name("power_suite_v58.json"))
        self.store = PowerStateStore(state_path)

    async def cog_load(self) -> None:
        self.bot.add_view(StaffPowerViewV58(self))
        self._patch_setup_pipeline()

    def _patch_setup_pipeline(self) -> None:
        if getattr(SetupExperienceV55Cog, "_aidebot_v58_power_suite", False):
            return
        original_publish = SetupExperienceV55Cog._publish_panels

        async def publish(setup_self, guild, channels, roles):
            actions = await original_publish(setup_self, guild, channels, roles)
            cog = setup_self.bot.get_cog("PowerSuiteV58Cog")
            if cog is not None:
                staff = channels.get(STAFF_CHANNEL) if isinstance(channels, dict) else None
                action = await cog._reconcile_staff(guild, staff)
                actions.append(("Outils avancés", action))
            return actions

        SetupExperienceV55Cog._publish_panels = publish
        SetupExperienceV55Cog._aidebot_v58_power_suite = True

    async def _remove_legacy_guardian_panel(self, channel: discord.TextChannel) -> None:
        if self.bot.user is None:
            return
        checked, message = await find_bot_embed_by_title(
            channel,
            bot_user_id=self.bot.user.id,
            title=GUARDIAN_TITLE,
            limit=100,
        )
        if not checked or message is None:
            return
        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _reconcile_staff(self, guild: discord.Guild, channel: discord.TextChannel | None = None) -> str:
        channel = channel or discord.utils.get(guild.text_channels, name=STAFF_CHANNEL)
        if channel is None:
            return "absent"
        if channel.topic != STAFF_TOPIC:
            try:
                await channel.edit(topic=STAFF_TOPIC, reason="Aide Bot V58 — outils staff distincts")
            except (discord.Forbidden, discord.HTTPException):
                pass
        await self._remove_legacy_guardian_panel(channel)
        return await _upsert_panel(self.bot, channel, embed=staff_power_embed_v58(), view=StaffPowerViewV58(self))

    async def activate_incident(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        if await self.store.get(guild.id, "incident") is not None:
            return await interaction.response.send_message(
                "Le mode incident est déjà actif. Utilise **Rétablir l’état précédent** pour revenir en arrière.",
                ephemeral=True,
            )
        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "Aide Bot a besoin de **Gérer les rôles** pour activer cette protection.",
                ephemeral=True,
            )
        original = int(guild.default_role.permissions.value)
        permissions = discord.Permissions(original)
        removed = []
        for name in SENSITIVE_EVERYONE_PERMISSIONS:
            if getattr(permissions, name, False):
                setattr(permissions, name, False)
                removed.append(name)
        await self.store.save_incident(guild.id, original)
        if not removed:
            return await interaction.response.send_message(
                "Protection enregistrée. `@everyone` n’avait déjà aucune permission administrative dangereuse.",
                ephemeral=True,
            )
        try:
            await guild.default_role.edit(
                permissions=permissions,
                reason=f"Aide Bot V58 — mode incident activé par {interaction.user}",
            )
        except (discord.Forbidden, discord.HTTPException):
            await self.store.clear_incident(guild.id)
            return await interaction.response.send_message(
                "Discord a refusé la modification de `@everyone`. Rien n’a été laissé en état intermédiaire.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            "Mode incident actif. Permissions retirées de `@everyone` : " + ", ".join(f"`{name}`" for name in removed) + ".",
            ephemeral=True,
        )

    async def restore_incident(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None
        state = await self.store.get(guild.id, "incident")
        if not isinstance(state, dict) or "everyone_permissions" not in state:
            return await interaction.response.send_message("Aucun état pré-incident n’est enregistré.", ephemeral=True)
        try:
            await guild.default_role.edit(
                permissions=discord.Permissions(int(state["everyone_permissions"])),
                reason=f"Aide Bot V58 — fin du mode incident par {interaction.user}",
            )
        except (discord.Forbidden, discord.HTTPException):
            return await interaction.response.send_message(
                "Impossible de rétablir `@everyone`. L’état sauvegardé est conservé pour réessayer.",
                ephemeral=True,
            )
        await self.store.clear_incident(guild.id)
        await interaction.response.send_message("État `@everyone` rétabli exactement comme avant le mode incident.", ephemeral=True)

    async def build_blueprint(self, guild: discord.Guild, key: str) -> dict[str, int]:
        blueprint = BLUEPRINTS[key]
        result = {"roles": 0, "categories": 0, "channels": 0, "skipped": 0}
        created: dict[str, list[int] | str] = {"roles": [], "categories": [], "channels": [], "template": key}

        role_objects: dict[str, discord.Role] = {}
        for role_name in blueprint.roles:
            existing = discord.utils.get(guild.roles, name=role_name)
            if existing is not None:
                role_objects[role_name] = existing
                result["skipped"] += 1
                continue
            permissions = discord.Permissions.none()
            if role_name in {"Modérateur", "Support", "Responsable Support"}:
                permissions.manage_messages = True
                permissions.moderate_members = True
            if role_name == "Responsable Support":
                permissions.manage_channels = True
            try:
                role = await guild.create_role(
                    name=role_name,
                    permissions=permissions,
                    reason=f"Aide Bot V58 — blueprint {blueprint.label}",
                )
            except (discord.Forbidden, discord.HTTPException):
                continue
            role_objects[role_name] = role
            result["roles"] += 1
            created["roles"].append(role.id)  # type: ignore[union-attr]

        for category_spec in blueprint.categories:
            category = discord.utils.get(guild.categories, name=category_spec.name)
            if category is None:
                try:
                    category = await guild.create_category(
                        category_spec.name,
                        reason=f"Aide Bot V58 — blueprint {blueprint.label}",
                    )
                except (discord.Forbidden, discord.HTTPException):
                    continue
                result["categories"] += 1
                created["categories"].append(category.id)  # type: ignore[union-attr]
            else:
                result["skipped"] += 1

            for channel_spec in category_spec.channels:
                existing = next(
                    (
                        channel
                        for channel in guild.channels
                        if channel.name.casefold() == channel_spec.name.casefold()
                        and ((channel_spec.kind == "voice" and isinstance(channel, discord.VoiceChannel)) or (channel_spec.kind == "text" and isinstance(channel, discord.TextChannel)))
                    ),
                    None,
                )
                if existing is not None:
                    result["skipped"] += 1
                    continue
                try:
                    if channel_spec.kind == "voice":
                        channel = await guild.create_voice_channel(
                            channel_spec.name,
                            category=category,
                            reason=f"Aide Bot V58 — blueprint {blueprint.label}",
                        )
                    else:
                        overwrites = None
                        if channel_spec.read_only:
                            overwrites = {
                                guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)
                            }
                        channel = await guild.create_text_channel(
                            channel_spec.name,
                            category=category,
                            overwrites=overwrites,
                            reason=f"Aide Bot V58 — blueprint {blueprint.label}",
                        )
                except (discord.Forbidden, discord.HTTPException):
                    continue
                result["channels"] += 1
                created["channels"].append(channel.id)  # type: ignore[union-attr]

        await self.store.save_build(guild.id, created)
        return result

    async def undo_blueprint(self, guild: discord.Guild) -> str:
        state = await self.store.get(guild.id, "last_build")
        if not isinstance(state, dict):
            return "Aucune création V58 récente n’est enregistrée pour ce serveur."
        deleted_channels = 0
        deleted_categories = 0
        deleted_roles = 0
        skipped = 0

        for channel_id in reversed(list(state.get("channels", []))):
            channel = guild.get_channel(int(channel_id))
            if channel is None:
                continue
            try:
                await channel.delete(reason="Aide Bot V58 — annulation de la dernière structure")
                deleted_channels += 1
            except (discord.Forbidden, discord.HTTPException):
                skipped += 1

        for category_id in reversed(list(state.get("categories", []))):
            category = guild.get_channel(int(category_id))
            if not isinstance(category, discord.CategoryChannel):
                continue
            if category.channels:
                skipped += 1
                continue
            try:
                await category.delete(reason="Aide Bot V58 — annulation de la dernière structure")
                deleted_categories += 1
            except (discord.Forbidden, discord.HTTPException):
                skipped += 1

        me = guild.me
        for role_id in reversed(list(state.get("roles", []))):
            role = guild.get_role(int(role_id))
            if role is None:
                continue
            if role.managed or me is None or role >= me.top_role:
                skipped += 1
                continue
            try:
                await role.delete(reason="Aide Bot V58 — annulation de la dernière structure")
                deleted_roles += 1
            except (discord.Forbidden, discord.HTTPException):
                skipped += 1

        await self.store.clear_build(guild.id)
        return (
            f"Annulation terminée : **{deleted_channels} salon(s)**, **{deleted_categories} catégorie(s)** et "
            f"**{deleted_roles} rôle(s)** créés par le dernier blueprint ont été supprimés. Ignorés : **{skipped}**."
        )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            await self._reconcile_staff(guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if isinstance(channel, discord.TextChannel) and channel.name == STAFF_CHANNEL:
            await self._reconcile_staff(channel.guild, channel)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PowerSuiteV58Cog(bot))
