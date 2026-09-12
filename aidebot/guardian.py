from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import discord


SENSITIVE_PERMISSION_NAMES = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "mention_everyone",
)

SEVERITY_WEIGHT = {
    "critical": 35,
    "high": 18,
    "medium": 8,
    "low": 3,
}

PERSONAS = {
    "Membre": ("👤・Membre",),
    "Helper": ("👤・Membre", "🤝・Helper"),
    "Formateur": ("👤・Membre", "🎓・Formateur"),
    "VIP": ("👤・Membre", "💎・VIP"),
}

PRIVATE_CATEGORY_RULES = {
    "━━ STAFF ━━": ("Membre", "VIP"),
    "━━ PREMIUM ━━": ("Membre",),
}


def _enum_value(value: Any) -> int:
    raw = getattr(value, "value", value)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _overwrite_payload(channel: discord.abc.GuildChannel) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for target, overwrite in channel.overwrites.items():
        allow, deny = overwrite.pair()
        target_type = "role" if isinstance(target, discord.Role) else "member"
        payload[str(target.id)] = {
            "type": target_type,
            "name": getattr(target, "name", getattr(target, "display_name", str(target.id))),
            "allow": int(allow.value),
            "deny": int(deny.value),
        }
    return payload


def snapshot_guild(guild: discord.Guild) -> dict[str, Any]:
    roles = [
        {
            "id": int(role.id),
            "name": role.name,
            "position": int(role.position),
            "permissions": int(role.permissions.value),
            "managed": bool(role.managed),
        }
        for role in sorted(guild.roles, key=lambda item: item.id)
    ]
    channels = []
    for channel in sorted(guild.channels, key=lambda item: item.id):
        channels.append(
            {
                "id": int(channel.id),
                "name": channel.name,
                "type": str(channel.type),
                "category_id": int(channel.category_id) if getattr(channel, "category_id", None) else None,
                "position": int(channel.position),
                "overwrites": _overwrite_payload(channel),
            }
        )
    return {
        "guild": {
            "id": int(guild.id),
            "name": guild.name,
            "verification_level": _enum_value(guild.verification_level),
            "explicit_content_filter": _enum_value(guild.explicit_content_filter),
        },
        "roles": roles,
        "channels": channels,
    }


def snapshot_hash(snapshot: dict[str, Any]) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    before_roles = {int(item["id"]): item for item in before.get("roles", [])}
    after_roles = {int(item["id"]): item for item in after.get("roles", [])}
    for role_id in sorted(set(before_roles) | set(after_roles)):
        old = before_roles.get(role_id)
        new = after_roles.get(role_id)
        if old is None:
            changes.append(f"Rôle ajouté : {new['name']}")
            continue
        if new is None:
            changes.append(f"Rôle supprimé : {old['name']}")
            continue
        if old["name"] != new["name"]:
            changes.append(f"Rôle renommé : {old['name']} → {new['name']}")
        if int(old["permissions"]) != int(new["permissions"]):
            changes.append(f"Permissions du rôle modifiées : {new['name']}")

    before_channels = {int(item["id"]): item for item in before.get("channels", [])}
    after_channels = {int(item["id"]): item for item in after.get("channels", [])}
    for channel_id in sorted(set(before_channels) | set(after_channels)):
        old = before_channels.get(channel_id)
        new = after_channels.get(channel_id)
        if old is None:
            changes.append(f"Salon/catégorie ajouté : {new['name']}")
            continue
        if new is None:
            changes.append(f"Salon/catégorie supprimé : {old['name']}")
            continue
        if old["name"] != new["name"]:
            changes.append(f"Salon/catégorie renommé : {old['name']} → {new['name']}")
        if old.get("category_id") != new.get("category_id"):
            changes.append(f"Catégorie changée : {new['name']}")
        if old.get("overwrites", {}) != new.get("overwrites", {}):
            changes.append(f"Permissions du salon modifiées : {new['name']}")

    before_guild = before.get("guild", {})
    after_guild = after.get("guild", {})
    for key, label in (
        ("verification_level", "Niveau de vérification"),
        ("explicit_content_filter", "Filtre de contenu"),
    ):
        if before_guild.get(key) != after_guild.get(key):
            changes.append(f"{label} modifié")
    return changes


def _persona_roles(guild: discord.Guild, names: tuple[str, ...]) -> list[discord.Role]:
    roles: list[discord.Role] = []
    for name in names:
        role = discord.utils.get(guild.roles, name=name)
        if role is not None and role != guild.default_role:
            roles.append(role)
    return roles


def effective_permissions_for_roles(
    guild: discord.Guild,
    channel: discord.abc.GuildChannel,
    roles: list[discord.Role],
) -> discord.Permissions:
    value = int(guild.default_role.permissions.value)
    for role in roles:
        value |= int(role.permissions.value)

    administrator_bit = int(discord.Permissions(administrator=True).value)
    if value & administrator_bit:
        return discord.Permissions.all()

    everyone = channel.overwrites_for(guild.default_role)
    allow, deny = everyone.pair()
    value &= ~int(deny.value)
    value |= int(allow.value)

    role_allow = 0
    role_deny = 0
    for role in roles:
        overwrite = channel.overwrites_for(role)
        allow, deny = overwrite.pair()
        role_allow |= int(allow.value)
        role_deny |= int(deny.value)
    value &= ~role_deny
    value |= role_allow
    return discord.Permissions(value)


@dataclass(frozen=True)
class GuardianRisk:
    severity: str
    title: str
    detail: str


@dataclass(frozen=True)
class GuardianAudit:
    score: int
    risks: tuple[GuardianRisk, ...]
    personas: dict[str, dict[str, int]]


def audit_guild(guild: discord.Guild) -> GuardianAudit:
    risks: list[GuardianRisk] = []
    everyone = guild.default_role.permissions
    for name in SENSITIVE_PERMISSION_NAMES:
        if getattr(everyone, name, False):
            severity = "critical" if name == "administrator" else "high"
            risks.append(
                GuardianRisk(
                    severity,
                    "Permission sensible sur @everyone",
                    f"@everyone possède `{name}`. Tous les membres héritent de ce pouvoir.",
                )
            )

    admin_roles = [role for role in guild.roles if role != guild.default_role and role.permissions.administrator]
    if len(admin_roles) > 4:
        risks.append(
            GuardianRisk(
                "high",
                "Trop de rôles Administrateur",
                f"{len(admin_roles)} rôles ont Administrateur. Réduis ce nombre et utilise des permissions ciblées.",
            )
        )
    for role in admin_roles:
        if role.managed:
            risks.append(
                GuardianRisk(
                    "medium",
                    "Intégration avec Administrateur",
                    f"Le rôle géré `{role.name}` possède Administrateur. Vérifie que cette intégration en a réellement besoin.",
                )
            )

    duplicate_channels: dict[str, int] = {}
    for channel in guild.channels:
        duplicate_channels[channel.name] = duplicate_channels.get(channel.name, 0) + 1
    duplicates = sorted(name for name, count in duplicate_channels.items() if count > 1)
    if duplicates:
        risks.append(
            GuardianRisk(
                "low",
                "Noms de salons en double",
                "Plusieurs objets portent le même nom : " + ", ".join(duplicates[:6]),
            )
        )

    if _enum_value(guild.verification_level) == 0:
        risks.append(GuardianRisk("medium", "Vérification désactivée", "Le niveau de vérification du serveur est désactivé."))
    if _enum_value(guild.explicit_content_filter) == 0:
        risks.append(GuardianRisk("low", "Filtre de contenu désactivé", "Le filtre de contenu explicite est désactivé."))

    personas: dict[str, dict[str, int]] = {}
    for persona_name, role_names in PERSONAS.items():
        persona_roles = _persona_roles(guild, role_names)
        visible = 0
        manageable = 0
        for channel in guild.channels:
            permissions = effective_permissions_for_roles(guild, channel, persona_roles)
            if permissions.view_channel:
                visible += 1
            if permissions.manage_channels:
                manageable += 1
        personas[persona_name] = {"visible": visible, "manageable": manageable}

    for category_name, forbidden_personas in PRIVATE_CATEGORY_RULES.items():
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            continue
        for persona_name in forbidden_personas:
            role_names = PERSONAS[persona_name]
            permissions = effective_permissions_for_roles(guild, category, _persona_roles(guild, role_names))
            if permissions.view_channel:
                risks.append(
                    GuardianRisk(
                        "critical",
                        "Fuite d’accès privé",
                        f"Le profil **{persona_name}** peut voir la catégorie `{category_name}`.",
                    )
                )

    for channel in guild.text_channels:
        lowered = channel.name.casefold()
        if not any(token in lowered for token in ("staff", "logs", "admin", "direction")):
            continue
        member_roles = _persona_roles(guild, PERSONAS["Membre"])
        if effective_permissions_for_roles(guild, channel, member_roles).view_channel:
            risks.append(
                GuardianRisk(
                    "high",
                    "Salon sensible visible",
                    f"Un profil Membre peut voir `{channel.name}`. Vérifie les overwrites de la catégorie et du salon.",
                )
            )

    score = 100
    for risk in risks:
        score -= SEVERITY_WEIGHT.get(risk.severity, 0)
    return GuardianAudit(max(0, score), tuple(risks), personas)


class GuardianStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._lock = asyncio.Lock()

    def _read_sync(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"guilds": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"guilds": {}}
        if not isinstance(data, dict):
            return {"guilds": {}}
        data.setdefault("guilds", {})
        return data

    def _write_sync(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    async def baseline(self, guild_id: int) -> dict[str, Any] | None:
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            value = data.get("guilds", {}).get(str(guild_id))
            return value if isinstance(value, dict) else None

    async def save_baseline(self, guild: discord.Guild, snapshot: dict[str, Any]) -> str:
        digest = snapshot_hash(snapshot)
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            data.setdefault("guilds", {})[str(guild.id)] = {
                "hash": digest,
                "snapshot": snapshot,
            }
            await asyncio.to_thread(self._write_sync, data)
        return digest


async def restore_permission_baseline(guild: discord.Guild, snapshot: dict[str, Any]) -> dict[str, int]:
    result = {"roles": 0, "channels": 0, "skipped": 0}
    me = guild.me
    if me is None:
        return result

    baseline_roles = {int(item["id"]): item for item in snapshot.get("roles", [])}
    for role_id, data in baseline_roles.items():
        role = guild.get_role(role_id)
        if role is None or role == guild.default_role or role.managed or role >= me.top_role:
            result["skipped"] += 1
            continue
        if int(role.permissions.value) == int(data["permissions"]):
            continue
        try:
            await role.edit(
                permissions=discord.Permissions(int(data["permissions"])),
                reason="Aide Bot Guardian — restauration de l’état sûr",
            )
            result["roles"] += 1
        except (discord.Forbidden, discord.HTTPException):
            result["skipped"] += 1

    baseline_channels = {int(item["id"]): item for item in snapshot.get("channels", [])}
    for channel_id, data in baseline_channels.items():
        channel = guild.get_channel(channel_id)
        if channel is None:
            result["skipped"] += 1
            continue
        baseline_overwrites = data.get("overwrites", {})
        role_targets = {
            int(target_id): payload
            for target_id, payload in baseline_overwrites.items()
            if payload.get("type") == "role"
        }
        current_role_ids = {target.id for target in channel.overwrites if isinstance(target, discord.Role)}
        all_role_ids = current_role_ids | set(role_targets)
        changed = False
        for role_id in all_role_ids:
            role = guild.get_role(role_id)
            if role is None:
                continue
            payload = role_targets.get(role_id)
            try:
                if payload is None:
                    await channel.set_permissions(role, overwrite=None, reason="Aide Bot Guardian — rollback overwrite")
                else:
                    overwrite = discord.PermissionOverwrite.from_pair(
                        discord.Permissions(int(payload.get("allow", 0))),
                        discord.Permissions(int(payload.get("deny", 0))),
                    )
                    await channel.set_permissions(role, overwrite=overwrite, reason="Aide Bot Guardian — rollback overwrite")
                changed = True
            except (discord.Forbidden, discord.HTTPException):
                result["skipped"] += 1
        if changed:
            result["channels"] += 1
    return result
