from __future__ import annotations

import asyncio
import io
import ipaddress
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp
import discord
from discord.ext import commands

from aidebot.blueprint import CATEGORY_SPECS, ROLE_SPECS, role_permissions
from aidebot.cogs.assistant_guardian_v52 import GuardianPanelView, _upsert_panel, guardian_panel_embed
from aidebot.cogs.power_suite_v58 import (
    BLUEPRINTS,
    DANGER,
    POWER_TITLE,
    STAFF_CHANNEL,
    BlueprintHomeViewV58,
    DoctorResultViewV58,
    IncidentViewV58,
    PermissionLabModalV58,
    PowerSuiteV58Cog,
    doctor_embed_v58,
    server_doctor,
)
from aidebot.cogs.setup_experience_v55 import SetupExperienceV55Cog
from aidebot.experience_content import BANNER_URL
from aidebot.permissions import decide

COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F
BRAND_ROLE_TITLE = "Aide Bot — Outils avancés"
SELF_ROLE_TITLE = "Aide Bot — Mes centres d’intérêt"
WELCOME_CHANNEL = "👋・bienvenue"
STAFF_TOPIC = (
    "Outils administration : Doctor, permissions, Guardian, incident, structures, Branding Studio et Role Studio."
)

SAFE_IMAGE_HOSTS = {
    "cdn.discordapp.com",
    "media.discordapp.net",
    "raw.githubusercontent.com",
    "i.imgur.com",
}

SELF_ROLE_SPECS = (
    ("🎮・Gaming", 0x57F287),
    ("💻・Développement", 0x5865F2),
    ("🎨・Création", 0xEB459E),
    ("🛡️・Sécurité", 0xE74C3C),
)

DANGEROUS_ROLE_PERMISSIONS = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "ban_members",
    "kick_members",
    "mention_everyone",
)

CUSTOM_ROLE_PRESETS: dict[str, tuple[str, dict[str, bool]]] = {
    "lecture": ("Lecture seule", {"view_channel": True, "read_message_history": True}),
    "membre": (
        "Membre standard",
        {"view_channel": True, "send_messages": True, "read_message_history": True, "connect": True, "speak": True},
    ),
    "helper": (
        "Helper support",
        {"view_channel": True, "send_messages": True, "read_message_history": True, "manage_messages": True},
    ),
    "moderation": (
        "Modération ciblée",
        {
            "view_channel": True,
            "send_messages": True,
            "read_message_history": True,
            "manage_messages": True,
            "moderate_members": True,
        },
    ),
}

BRAND_PANEL_CHANNELS = {
    "👋・bienvenue",
    "📜・règlement",
    "📢・annonces",
    "🎓・centre-aide",
    "🎓・formations",
    "🛒・shop",
    "💎・espace-premium",
    "🧑‍🏫・recrutement",
    "📋・staff",
    "🧠・suivi-formations",
}


def _hex_color(text: str, default: int = COLOR) -> int:
    raw = text.strip().lstrip("#")
    if not raw:
        return default
    if not re.fullmatch(r"[0-9a-fA-F]{6}", raw):
        raise ValueError("La couleur doit être au format HEX, par exemple #5865F2.")
    return int(raw, 16)


def _safe_https_image_url(value: str, *, allow_empty: bool = True) -> str:
    value = value.strip()
    if not value and allow_empty:
        return ""
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Utilise une URL HTTPS directe vers une image.")
    host = parsed.hostname.casefold()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
        raise ValueError("Cette adresse réseau n’est pas autorisée.")
    if host not in SAFE_IMAGE_HOSTS:
        allowed = ", ".join(sorted(SAFE_IMAGE_HOSTS))
        raise ValueError(f"Hôte non autorisé. Utilise une image hébergée sur : {allowed}.")
    return value


class BrandRoleStore:
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

    async def get_brand(self, guild_id: int) -> dict[str, str]:
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            state = payload.get("guilds", {}).get(str(guild_id), {})
            brand = state.get("brand", {}) if isinstance(state, dict) else {}
            return dict(brand) if isinstance(brand, dict) else {}

    async def save_brand(self, guild_id: int, brand: dict[str, str]) -> None:
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            state = payload.setdefault("guilds", {}).setdefault(str(guild_id), {})
            state["brand"] = dict(brand)
            await asyncio.to_thread(self._write_sync, payload)

    async def clear_brand(self, guild_id: int) -> None:
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            state = payload.setdefault("guilds", {}).setdefault(str(guild_id), {})
            state.pop("brand", None)
            await asyncio.to_thread(self._write_sync, payload)


def branding_embed_v59(guild: discord.Guild, brand: dict[str, str]) -> discord.Embed:
    accent = _hex_color(brand.get("accent", "5865F2"))
    banner = brand.get("panel_banner") or BANNER_URL
    e = discord.Embed(
        title="Branding Studio",
        description=(
            "Personnalise l’apparence visible d’Aide Bot sans toucher au code : bannière des panneaux, couleur d’accent, "
            "icône du serveur et bannière Discord quand le serveur la prend en charge."
        ),
        color=accent,
    )
    e.add_field(name="Serveur", value=guild.name, inline=True)
    e.add_field(name="Accent", value=f"#{accent:06X}", inline=True)
    e.add_field(name="Bannière panneaux", value="Personnalisée" if brand.get("panel_banner") else "Aide Bot par défaut", inline=True)
    e.add_field(name="Icône serveur", value="Prête" if brand.get("server_icon") else "Non configurée", inline=True)
    e.add_field(
        name="Bannière serveur",
        value=("Prête" if brand.get("server_banner") else "Non configurée") + (" • compatible" if "BANNER" in guild.features else " • non disponible sur ce serveur"),
        inline=True,
    )
    e.set_image(url=banner)
    e.set_footer(text="Aperçu uniquement • les modifications du serveur demandent une confirmation")
    return e


def role_studio_report(guild: discord.Guild) -> dict[str, Any]:
    canonical_names = [name for name, _color, _spec in ROLE_SPECS]
    counts: dict[str, int] = {}
    for role in guild.roles:
        counts[role.name] = counts.get(role.name, 0) + 1
    missing = [name for name in canonical_names if counts.get(name, 0) == 0]
    duplicates = [name for name, count in counts.items() if count > 1 and name != "@everyone"]
    dangerous: list[str] = []
    for role in guild.roles:
        if role == guild.default_role:
            continue
        found = [name for name in DANGEROUS_ROLE_PERMISSIONS if getattr(role.permissions, name, False)]
        if found:
            dangerous.append(f"{role.name}: {', '.join(found)}")
    me = guild.me
    blocked = []
    if me is not None:
        blocked = [role.name for role in guild.roles if role != guild.default_role and not role.managed and role >= me.top_role]
    return {
        "missing": missing,
        "duplicates": duplicates,
        "dangerous": dangerous,
        "blocked": blocked,
        "total": len(guild.roles),
    }


def role_report_embed_v59(guild: discord.Guild) -> discord.Embed:
    report = role_studio_report(guild)
    severity = len(report["missing"]) + len(report["duplicates"]) + len(report["dangerous"])
    color = SUCCESS if severity == 0 else WARNING
    e = discord.Embed(
        title="Role Studio — Audit",
        description="Analyse visible de la hiérarchie et des rôles sensibles avant toute réparation.",
        color=color,
    )
    e.add_field(name="Rôles", value=f"**{report['total']}** au total", inline=True)
    e.add_field(name="Canoniques manquants", value=str(len(report["missing"])), inline=True)
    e.add_field(name="Doublons", value=str(len(report["duplicates"])), inline=True)
    e.add_field(
        name="Manquants",
        value="\n".join(f"• {name}" for name in report["missing"][:10]) or "Aucun",
        inline=False,
    )
    e.add_field(
        name="Rôles sensibles",
        value="\n".join(f"• {item}" for item in report["dangerous"][:8])[:1024] or "Aucun rôle avec permission sensible détecté.",
        inline=False,
    )
    if report["blocked"]:
        e.add_field(
            name="Au-dessus d’Aide Bot",
            value="\n".join(f"• {name}" for name in report["blocked"][:8]),
            inline=False,
        )
    e.set_footer(text="Role Studio ne supprime jamais un rôle existant automatiquement")
    return e


def self_role_embed_v59() -> discord.Embed:
    e = discord.Embed(
        title=SELF_ROLE_TITLE,
        description=(
            "Choisis jusqu’à **2 centres d’intérêt**. Ces rôles n’accordent aucune permission sensible : ils servent uniquement "
            "à personnaliser ton profil et à mieux orienter l’aide et les formations."
        ),
        color=COLOR,
    )
    e.add_field(
        name="Disponibles",
        value=" • ".join(name for name, _color in SELF_ROLE_SPECS),
        inline=False,
    )
    e.set_footer(text="Tu peux modifier ton choix quand tu veux • maximum 2")
    return e


def staff_power_embed_v59() -> discord.Embed:
    e = discord.Embed(
        title=BRAND_ROLE_TITLE,
        description=(
            "Un seul panneau staff. Chaque outil a une mission différente : diagnostiquer, simuler, protéger, construire, "
            "personnaliser l’image du serveur ou gérer les rôles."
        ),
        color=COLOR,
    )
    e.add_field(name="Server Doctor", value="Score, risques et priorités.", inline=True)
    e.add_field(name="Permission Lab", value="Permissions effectives membre/rôle/salon.", inline=True)
    e.add_field(name="Guardian", value="État sûr, diff et restauration.", inline=True)
    e.add_field(name="Mode incident", value="Protection d’urgence réversible.", inline=True)
    e.add_field(name="Studio structure", value="Prévisualiser et construire une structure.", inline=True)
    e.add_field(name="Branding Studio", value="Bannières, couleurs, icône et identité visuelle.", inline=True)
    e.add_field(name="Role Studio", value="Audit, réparation, création sûre et self-roles.", inline=True)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • 7 outils réellement différents • pas de dashboard externe")
    return e


class BrandingConfigModalV59(discord.ui.Modal, title="Branding Studio"):
    panel_banner = discord.ui.TextInput(
        label="Bannière des panneaux",
        placeholder="URL HTTPS Discord CDN / GitHub raw / Imgur (vide = défaut)",
        required=False,
        max_length=500,
    )
    accent = discord.ui.TextInput(label="Couleur d’accent", placeholder="#5865F2", required=False, max_length=7)
    server_icon = discord.ui.TextInput(label="Icône serveur", placeholder="URL HTTPS directe (optionnel)", required=False, max_length=500)
    server_banner = discord.ui.TextInput(label="Bannière serveur", placeholder="URL HTTPS directe (optionnel)", required=False, max_length=500)

    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Branding Studio est réservé à la Direction.", ephemeral=True)
        try:
            panel_banner = _safe_https_image_url(str(self.panel_banner))
            server_icon = _safe_https_image_url(str(self.server_icon))
            server_banner = _safe_https_image_url(str(self.server_banner))
            accent = f"{_hex_color(str(self.accent) or '5865F2'):06X}"
        except ValueError as exc:
            return await interaction.response.send_message(str(exc), ephemeral=True)
        brand = {
            "panel_banner": panel_banner,
            "accent": accent,
            "server_icon": server_icon,
            "server_banner": server_banner,
        }
        await self.cog.store.save_brand(interaction.guild.id, brand)
        await interaction.response.send_message(
            embed=branding_embed_v59(interaction.guild, brand),
            view=BrandPreviewViewV59(self.cog),
            ephemeral=True,
        )


class ApplyServerBrandModalV59(discord.ui.Modal, title="Appliquer l’identité au serveur"):
    confirmation = discord.ui.TextInput(label="Écris APPLIQUER", placeholder="APPLIQUER", max_length=10)

    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Cette action est réservée à la Direction.", ephemeral=True)
        if str(self.confirmation).strip().upper() != "APPLIQUER":
            return await interaction.response.send_message("Confirmation incorrecte. Rien n’a été modifié.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await self.cog.apply_server_brand(interaction.guild)
        await interaction.followup.send(result, ephemeral=True)


class BrandPreviewViewV59(discord.ui.View):
    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        super().__init__(timeout=600)
        self.cog = cog

    @discord.ui.button(label="Appliquer aux panneaux", style=discord.ButtonStyle.success)
    async def apply_panels(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Cette action est réservée à la Direction.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        changed = await self.cog.apply_panel_brand(interaction.guild)
        await interaction.followup.send(f"Branding appliqué à **{changed} panneau(x)** existant(s).", ephemeral=True)

    @discord.ui.button(label="Appliquer au serveur", style=discord.ButtonStyle.primary)
    async def apply_server(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(ApplyServerBrandModalV59(self.cog))

    @discord.ui.button(label="Réinitialiser", style=discord.ButtonStyle.secondary)
    async def reset(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Cette action est réservée à la Direction.", ephemeral=True)
        await self.cog.store.clear_brand(interaction.guild.id)
        await interaction.response.send_message("Configuration visuelle réinitialisée. `/setup` republiera le style Aide Bot par défaut.", ephemeral=True)


class RepairRolesModalV59(discord.ui.Modal, title="Réparer les rôles Aide Bot"):
    confirmation = discord.ui.TextInput(label="Écris REPARER", placeholder="REPARER", max_length=8)

    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Cette action est réservée à la Direction.", ephemeral=True)
        if str(self.confirmation).strip().upper() != "REPARER":
            return await interaction.response.send_message("Confirmation incorrecte. Rien n’a été modifié.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await self.cog.repair_roles(interaction.guild)
        await interaction.followup.send(
            f"Role Studio : **{result['created']} créé(s)**, **{result['updated']} réparé(s)**, **{result['skipped']} ignoré(s)**.",
            ephemeral=True,
        )


class CreateSafeRoleModalV59(discord.ui.Modal, title="Créer un rôle sûr"):
    role_name = discord.ui.TextInput(label="Nom du rôle", placeholder="Ex: Support Junior", max_length=80)
    color = discord.ui.TextInput(label="Couleur HEX", placeholder="#5865F2", required=False, max_length=7)
    preset = discord.ui.TextInput(
        label="Preset",
        placeholder="lecture / membre / helper / moderation",
        max_length=12,
    )

    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Cette action est réservée à la Direction.", ephemeral=True)
        name = str(self.role_name).strip()
        preset_key = str(self.preset).strip().casefold()
        if preset_key not in CUSTOM_ROLE_PRESETS:
            return await interaction.response.send_message("Preset invalide : lecture, membre, helper ou moderation.", ephemeral=True)
        if discord.utils.get(interaction.guild.roles, name=name):
            return await interaction.response.send_message("Un rôle porte déjà exactement ce nom.", ephemeral=True)
        try:
            colour = _hex_color(str(self.color) or "5865F2")
        except ValueError as exc:
            return await interaction.response.send_message(str(exc), ephemeral=True)
        me = interaction.guild.me
        if me is None or not me.guild_permissions.manage_roles:
            return await interaction.response.send_message("Aide Bot n’a pas la permission **Gérer les rôles**.", ephemeral=True)
        label, spec = CUSTOM_ROLE_PRESETS[preset_key]
        permissions = discord.Permissions.none()
        for key, value in spec.items():
            setattr(permissions, key, value)
        try:
            role = await interaction.guild.create_role(
                name=name,
                colour=discord.Colour(colour),
                permissions=permissions,
                reason=f"Aide Bot Role Studio — preset {preset_key}",
            )
        except (discord.Forbidden, discord.HTTPException):
            return await interaction.response.send_message("Impossible de créer le rôle. Vérifie la hiérarchie et les permissions du bot.", ephemeral=True)
        await interaction.response.send_message(
            f"Rôle **{role.name}** créé avec le preset **{label}**. Aucun droit Administrateur n’a été ajouté.",
            ephemeral=True,
        )


class RoleStudioViewV59(discord.ui.View):
    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        super().__init__(timeout=600)
        self.cog = cog

    @discord.ui.button(label="Auditer les rôles", style=discord.ButtonStyle.primary)
    async def audit(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild:
            return
        await interaction.response.send_message(embed=role_report_embed_v59(interaction.guild), ephemeral=True)

    @discord.ui.button(label="Réparer les rôles Aide Bot", style=discord.ButtonStyle.success)
    async def repair(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(RepairRolesModalV59(self.cog))

    @discord.ui.button(label="Créer un rôle sûr", style=discord.ButtonStyle.secondary)
    async def create_role(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(CreateSafeRoleModalV59(self.cog))

    @discord.ui.button(label="Réparer le panneau self-role", style=discord.ButtonStyle.secondary)
    async def self_roles(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild:
            return
        result = await self.cog.reconcile_self_roles(interaction.guild)
        await interaction.response.send_message(f"Panneau self-role : **{result}**.", ephemeral=True)


class SelfRoleSelectV59(discord.ui.Select):
    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        self.cog = cog
        super().__init__(
            placeholder="Choisis jusqu’à 2 centres d’intérêt",
            min_values=0,
            max_values=2,
            custom_id="aidebot:v59:selfroles:select",
            options=[discord.SelectOption(label=name, value=name, description="Rôle d’intérêt sans permission sensible") for name, _color in SELF_ROLE_SPECS],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        role_map = {role.name: role for role in interaction.guild.roles if role.name in {name for name, _ in SELF_ROLE_SPECS}}
        if len(role_map) != len(SELF_ROLE_SPECS):
            return await interaction.response.send_message("Les rôles d’intérêt ne sont pas prêts. Un administrateur doit relancer `/setup`.", ephemeral=True)
        selected = set(self.values)
        to_add = [role for name, role in role_map.items() if name in selected and role not in interaction.user.roles]
        to_remove = [role for name, role in role_map.items() if name not in selected and role in interaction.user.roles]
        me = interaction.guild.me
        if me is None or any(role >= me.top_role for role in [*to_add, *to_remove]):
            return await interaction.response.send_message("Aide Bot ne peut pas gérer un de ces rôles à cause de la hiérarchie.", ephemeral=True)
        try:
            if to_add:
                await interaction.user.add_roles(*to_add, reason="Aide Bot — choix centres d’intérêt")
            if to_remove:
                await interaction.user.remove_roles(*to_remove, reason="Aide Bot — mise à jour centres d’intérêt")
        except (discord.Forbidden, discord.HTTPException):
            return await interaction.response.send_message("Impossible de modifier tes rôles pour le moment.", ephemeral=True)
        text = ", ".join(sorted(selected)) if selected else "aucun"
        await interaction.response.send_message(f"Centres d’intérêt enregistrés : **{text}**.", ephemeral=True)


class SelfRoleViewV59(discord.ui.View):
    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        super().__init__(timeout=None)
        self.add_item(SelfRoleSelectV59(cog))


class StaffPowerSelectV59(discord.ui.Select):
    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        self.cog = cog
        super().__init__(
            placeholder="Choisis un outil avancé",
            min_values=1,
            max_values=1,
            custom_id="aidebot:v59:staff:tool",
            options=[
                discord.SelectOption(label="Server Doctor", value="doctor", description="Score + risques + priorités"),
                discord.SelectOption(label="Permission Lab", value="permissions", description="Simuler les permissions effectives"),
                discord.SelectOption(label="Guardian", value="guardian", description="État sûr, différences, restauration"),
                discord.SelectOption(label="Mode incident", value="incident", description="Protection temporaire réversible"),
                discord.SelectOption(label="Studio structure", value="blueprint", description="Prévisualiser et construire un serveur"),
                discord.SelectOption(label="Branding Studio", value="branding", description="Bannières, couleur, icône serveur"),
                discord.SelectOption(label="Role Studio", value="roles", description="Audit, réparation, rôles sûrs, self-roles"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "audit.run").allowed:
            return await interaction.response.send_message("Ces outils sont réservés au staff autorisé.", ephemeral=True)
        choice = self.values[0]
        v58 = interaction.client.get_cog("PowerSuiteV58Cog")
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
            return await interaction.response.send_message(embed=guardian_panel_embed(), view=GuardianPanelView(core), ephemeral=True)
        if choice == "incident":
            if not isinstance(v58, PowerSuiteV58Cog):
                return await interaction.response.send_message("Mode incident temporairement indisponible.", ephemeral=True)
            e = discord.Embed(
                title="Mode incident",
                description="Protection d’urgence réversible de `@everyone`. Aucun salon, rôle ou membre n’est supprimé.",
                color=DANGER,
            )
            return await interaction.response.send_message(embed=e, view=IncidentViewV58(v58), ephemeral=True)
        if choice == "blueprint":
            if not isinstance(v58, PowerSuiteV58Cog):
                return await interaction.response.send_message("Studio structure temporairement indisponible.", ephemeral=True)
            e = discord.Embed(
                title="Studio structure",
                description=f"Choisis parmi **{len(BLUEPRINTS)} modèles**. Prévisualisation avant toute création et ajout non destructif.",
                color=COLOR,
            )
            return await interaction.response.send_message(embed=e, view=BlueprintHomeViewV58(v58), ephemeral=True)
        if choice == "branding":
            brand = await self.cog.store.get_brand(interaction.guild.id)
            e = branding_embed_v59(interaction.guild, brand)
            view = BrandPreviewViewV59(self.cog)
            view.add_item(discord.ui.Button(label="Configurer", style=discord.ButtonStyle.primary, custom_id=None))
            # Discord buttons added dynamically cannot have a callback; expose the modal through the dedicated view below.
            return await interaction.response.send_message(embed=e, view=BrandingHomeViewV59(self.cog), ephemeral=True)
        if choice == "roles":
            return await interaction.response.send_message(embed=role_report_embed_v59(interaction.guild), view=RoleStudioViewV59(self.cog), ephemeral=True)


class BrandingHomeViewV59(discord.ui.View):
    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        super().__init__(timeout=600)
        self.cog = cog

    @discord.ui.button(label="Configurer le branding", style=discord.ButtonStyle.primary)
    async def configure(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(BrandingConfigModalV59(self.cog))

    @discord.ui.button(label="Appliquer les réglages enregistrés", style=discord.ButtonStyle.success)
    async def apply(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Cette action est réservée à la Direction.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        changed = await self.cog.apply_panel_brand(interaction.guild)
        await interaction.followup.send(f"Branding appliqué à **{changed} panneau(x)**.", ephemeral=True)


class StaffPowerViewV59(discord.ui.View):
    def __init__(self, cog: "BrandRoleStudioV59Cog") -> None:
        super().__init__(timeout=None)
        self.add_item(StaffPowerSelectV59(cog))


class BrandRoleStudioV59Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.store = BrandRoleStore(str(Path(bot.settings.db_path).with_name("brand_role_v59.json")))

    async def cog_load(self) -> None:
        self.bot.add_view(StaffPowerViewV59(self))
        self.bot.add_view(SelfRoleViewV59(self))
        self._patch_setup_pipeline()

    def _patch_setup_pipeline(self) -> None:
        if getattr(SetupExperienceV55Cog, "_aidebot_v59_brand_role", False):
            return
        original_publish = SetupExperienceV55Cog._publish_panels

        async def publish(setup_self, guild, channels, roles):
            actions = await original_publish(setup_self, guild, channels, roles)
            cog = setup_self.bot.get_cog("BrandRoleStudioV59Cog")
            if cog is not None:
                actions.append(("Branding & Role Studio", await cog.reconcile(guild, channels)))
                brand = await cog.store.get_brand(guild.id)
                if brand:
                    changed = await cog.apply_panel_brand(guild)
                    actions.append(("Branding panneaux", f"{changed} mis à jour"))
            return actions

        SetupExperienceV55Cog._publish_panels = publish
        SetupExperienceV55Cog._aidebot_v59_brand_role = True

    async def _ensure_self_roles(self, guild: discord.Guild) -> dict[str, discord.Role]:
        found: dict[str, discord.Role] = {}
        me = guild.me
        for name, color in SELF_ROLE_SPECS:
            role = discord.utils.get(guild.roles, name=name)
            if role is None:
                if me is None or not me.guild_permissions.manage_roles:
                    continue
                try:
                    role = await guild.create_role(
                        name=name,
                        colour=discord.Colour(color),
                        permissions=discord.Permissions.none(),
                        reason="Aide Bot Role Studio — rôle d’intérêt sans permission",
                    )
                except (discord.Forbidden, discord.HTTPException):
                    continue
            found[name] = role
        return found

    async def repair_roles(self, guild: discord.Guild) -> dict[str, int]:
        result = {"created": 0, "updated": 0, "skipped": 0}
        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            return {"created": 0, "updated": 0, "skipped": len(ROLE_SPECS)}
        for name, color, spec in ROLE_SPECS:
            role = discord.utils.get(guild.roles, name=name)
            permissions = role_permissions(spec)
            if role is None:
                try:
                    await guild.create_role(
                        name=name,
                        colour=discord.Colour(color),
                        permissions=permissions,
                        reason="Aide Bot Role Studio — rôle canonique manquant",
                    )
                    result["created"] += 1
                except (discord.Forbidden, discord.HTTPException):
                    result["skipped"] += 1
                continue
            if role.managed or role >= me.top_role:
                result["skipped"] += 1
                continue
            if int(role.permissions.value) == int(permissions.value) and int(role.colour.value) == int(color):
                continue
            try:
                await role.edit(
                    permissions=permissions,
                    colour=discord.Colour(color),
                    reason="Aide Bot Role Studio — réparation contrôlée",
                )
                result["updated"] += 1
            except (discord.Forbidden, discord.HTTPException):
                result["skipped"] += 1
        await self._ensure_self_roles(guild)
        return result

    async def reconcile_self_roles(self, guild: discord.Guild) -> str:
        await self._ensure_self_roles(guild)
        channel = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL)
        if channel is None:
            return "absent"
        return await _upsert_panel(self.bot, channel, embed=self_role_embed_v59(), view=SelfRoleViewV59(self))

    async def reconcile(self, guild: discord.Guild, channels: dict[str, discord.TextChannel] | None = None) -> str:
        mapping = channels or {channel.name: channel for channel in guild.text_channels}
        staff = mapping.get(STAFF_CHANNEL)
        if staff is not None and staff.topic != STAFF_TOPIC:
            try:
                await staff.edit(topic=STAFF_TOPIC, reason="Aide Bot — Branding & Role Studio")
            except (discord.Forbidden, discord.HTTPException):
                pass
        action = "absent"
        if staff is not None:
            action = await _upsert_panel(self.bot, staff, embed=staff_power_embed_v59(), view=StaffPowerViewV59(self))
        await self.reconcile_self_roles(guild)
        return action

    async def _download_brand_image(self, url: str) -> bytes:
        url = _safe_https_image_url(url, allow_empty=False)
        timeout = aiohttp.ClientTimeout(total=12)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, allow_redirects=False) as response:
                if response.status != 200:
                    raise RuntimeError(f"Téléchargement image refusé (HTTP {response.status}).")
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().casefold()
                if not content_type.startswith("image/"):
                    raise RuntimeError("L’URL ne renvoie pas une image.")
                length = response.headers.get("Content-Length")
                if length and int(length) > 8 * 1024 * 1024:
                    raise RuntimeError("Image trop lourde : maximum 8 Mo.")
                data = await response.read()
                if len(data) > 8 * 1024 * 1024:
                    raise RuntimeError("Image trop lourde : maximum 8 Mo.")
                if len(data) < 64:
                    raise RuntimeError("Image invalide ou vide.")
                return data

    async def apply_server_brand(self, guild: discord.Guild) -> str:
        brand = await self.store.get_brand(guild.id)
        if not brand:
            return "Aucune configuration Branding Studio enregistrée."
        me = guild.me
        if me is None or not me.guild_permissions.manage_guild:
            return "Aide Bot n’a pas la permission **Gérer le serveur**."
        kwargs: dict[str, Any] = {"reason": "Aide Bot Branding Studio — application confirmée"}
        changes: list[str] = []
        try:
            if brand.get("server_icon"):
                kwargs["icon"] = await self._download_brand_image(brand["server_icon"])
                changes.append("icône")
            if brand.get("server_banner"):
                if "BANNER" not in guild.features:
                    return "Ce serveur Discord ne prend pas en charge la bannière de serveur. L’icône et les panneaux n’ont pas été modifiés par cette action."
                kwargs["banner"] = await self._download_brand_image(brand["server_banner"])
                changes.append("bannière serveur")
            if len(kwargs) == 1:
                return "Aucune icône ou bannière serveur n’est configurée."
            await guild.edit(**kwargs)
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as exc:
            return f"Impossible de préparer l’image : {str(exc)[:250]}"
        except (discord.Forbidden, discord.HTTPException) as exc:
            return f"Discord a refusé la modification : {str(exc)[:250]}"
        return "Identité du serveur appliquée : **" + ", ".join(changes) + "**."

    async def apply_panel_brand(self, guild: discord.Guild) -> int:
        brand = await self.store.get_brand(guild.id)
        if not brand:
            return 0
        accent = _hex_color(brand.get("accent", "5865F2"))
        banner = brand.get("panel_banner") or BANNER_URL
        changed = 0
        if self.bot.user is None:
            return 0
        for channel in guild.text_channels:
            if channel.name not in BRAND_PANEL_CHANNELS:
                continue
            try:
                async for message in channel.history(limit=80):
                    if message.author.id != self.bot.user.id or not message.embeds or not message.components:
                        continue
                    embed = discord.Embed.from_dict(message.embeds[0].to_dict())
                    embed.color = discord.Colour(accent)
                    embed.set_image(url=banner)
                    try:
                        await message.edit(embed=embed)
                        changed += 1
                    except (discord.Forbidden, discord.HTTPException):
                        continue
            except (discord.Forbidden, discord.HTTPException):
                continue
        return changed

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            await self.reconcile(guild)
            if await self.store.get_brand(guild.id):
                await self.apply_panel_brand(guild)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BrandRoleStudioV59Cog(bot))
