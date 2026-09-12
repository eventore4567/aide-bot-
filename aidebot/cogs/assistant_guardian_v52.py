from __future__ import annotations

import asyncio
import os
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

import aiohttp
import discord
from discord.ext import commands

from aidebot.experience_content import BANNER_URL
from aidebot.guardian import (
    GuardianAudit,
    GuardianStore,
    audit_guild,
    diff_snapshots,
    restore_permission_baseline,
    snapshot_guild,
    snapshot_hash,
)
from aidebot.message_reconcile import find_bot_embed_by_title
from aidebot.permissions import decide

COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F
DANGER = 0xED4245
AI_CHANNEL = "🤖・assistant-aide"
LEGACY_VIDEO_CHANNEL = "🎥・videos-guides"
STAFF_CHANNEL = "📋・staff"
LOG_CHANNEL = "🧾・logs"
AI_TITLE = "Aide Bot — Assistant IA"
GUARDIAN_TITLE = "Aide Bot — Guardian"

_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d+/[^\s]+", re.I),
)

SYSTEM_PROMPT = """Tu es l'assistant spécialisé d'Aide Bot, un service d'aide Discord.
Ta mission est uniquement d'aider sur Discord, les serveurs Discord, rôles, permissions, modération, tickets, sécurité défensive, bots Discord, Python/discord.py, GitHub, bases de données et hébergement d'un bot.

Règles obligatoires :
- Réponds en français clair, directement utile et adapté au niveau de la personne.
- Ne demande jamais de token Discord, mot de passe, cookie, code 2FA, code de récupération, clé API ou secret.
- Si la personne colle un secret, dis-lui de le révoquer/régénérer et ne le répète jamais.
- Ne prétends jamais avoir modifié le serveur, exécuté une commande ou vu des messages que tu n'as pas vus.
- Le contexte serveur fourni contient uniquement de la configuration et un audit automatique, pas les conversations privées.
- Pour les permissions et la sécurité, préfère le moindre privilège et explique le risque avant une action sensible.
- Si une réponse dépend d'un écran, d'une version ou d'un détail que tu ne connais pas, dis exactement quoi vérifier au lieu d'inventer.
- Commence par la solution la plus probable. Donne ensuite 2 à 5 étapes maximum. Termine par une seule question de diagnostic seulement si elle est vraiment nécessaire.
- Pour un problème qui exige l'intervention humaine du staff, indique que le membre peut ouvrir un ticket Aide Bot.
"""


def _redact_secrets(text: str) -> tuple[str, bool]:
    redacted = text
    changed = False
    for pattern in _SECRET_PATTERNS:
        redacted, count = pattern.subn("[SECRET MASQUÉ]", redacted)
        changed = changed or count > 0
    return redacted, changed


def _extract_response_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    parts: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    return "\n".join(parts).strip()


def _audit_context(guild: discord.Guild) -> str:
    audit = audit_guild(guild)
    top = "; ".join(f"{risk.severity}: {risk.detail}" for risk in audit.risks[:5]) or "aucun risque majeur détecté"
    personas = ", ".join(
        f"{name}: {stats['visible']} visibles/{stats['manageable']} gérables"
        for name, stats in audit.personas.items()
    )
    return (
        f"Serveur: {guild.name} ({guild.id}). "
        f"Rôles: {len(guild.roles)}. Salons/catégories: {len(guild.channels)}. "
        f"Score Guardian: {audit.score}/100. Risques principaux: {top}. "
        f"Simulation profils: {personas}."
    )


class AIUsageLimiter:
    def __init__(self, *, cooldown_seconds: int = 15, daily_limit: int = 25) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.daily_limit = max(1, daily_limit)
        self._last: dict[tuple[int, int], float] = {}
        self._daily: dict[tuple[str, int, int], int] = {}
        self._lock = asyncio.Lock()

    async def allow(self, guild_id: int, user_id: int) -> tuple[bool, str | None]:
        now = time.monotonic()
        today = date.today().isoformat()
        key = (guild_id, user_id)
        day_key = (today, guild_id, user_id)
        async with self._lock:
            previous = self._last.get(key, 0.0)
            remaining = self.cooldown_seconds - (now - previous)
            if remaining > 0:
                return False, f"Réessaie dans **{remaining:.0f}s**."
            used = self._daily.get(day_key, 0)
            if used >= self.daily_limit:
                return False, "Tu as atteint la limite de questions IA pour aujourd’hui. Le Centre d’aide et les tickets restent disponibles."
            self._last[key] = now
            self._daily[day_key] = used + 1
        return True, None


class AideAIClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("AIDEBOT_AI_MODEL", "gpt-5.6-luna").strip() or "gpt-5.6-luna"

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def answer(self, *, question: str, guild: discord.Guild, member: discord.Member) -> tuple[str, bool]:
        question, secret_was_redacted = _redact_secrets(question)
        if not self.configured:
            raise RuntimeError("OPENAI_API_KEY absent")

        role_names = [role.name for role in member.roles if role != guild.default_role][-8:]
        user_prompt = (
            f"Contexte technique automatique:\n{_audit_context(guild)}\n"
            f"Rôles du demandeur: {', '.join(role_names) if role_names else 'aucun rôle spécifique'}.\n\n"
            f"Question du membre:\n{question}"
        )
        body = {
            "model": self.model,
            "instructions": SYSTEM_PROMPT,
            "input": user_prompt,
            "max_output_tokens": 900,
        }
        timeout = aiohttp.ClientTimeout(total=35)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post("https://api.openai.com/v1/responses", headers=headers, json=body) as response:
                payload = await response.json(content_type=None)
                if response.status == 429:
                    raise RuntimeError("L’assistant IA reçoit trop de demandes. Réessaie dans un moment.")
                if response.status >= 400:
                    message = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
                    raise RuntimeError(message or f"Erreur IA HTTP {response.status}")
        text = _extract_response_text(payload if isinstance(payload, dict) else {})
        if not text:
            raise RuntimeError("Réponse IA vide")
        return text[:3800], secret_was_redacted


def assistant_panel_embed(configured: bool) -> discord.Embed:
    e = discord.Embed(
        title=AI_TITLE,
        description=(
            "Pose une question avec tes propres mots. L’assistant est spécialisé dans l’aide Discord : "
            "permissions, serveurs, modération, tickets, bots, code, sécurité et hébergement."
        ),
        color=COLOR,
    )
    e.add_field(
        name="Il connaît aussi ton serveur",
        value=(
            "Pour les questions de permissions ou de configuration, Aide Bot lui fournit uniquement un **audit technique** du serveur "
            "(rôles, salons, permissions et risques). Il ne lui envoie pas l’historique de tes conversations."
        ),
        inline=False,
    )
    e.add_field(
        name="Sécurité",
        value="Ne partage jamais token, clé API, mot de passe, cookie, 2FA ou code de récupération.",
        inline=False,
    )
    if not configured:
        e.add_field(
            name="État",
            value="L’assistant attend encore la configuration de sa clé IA par l’administrateur. Les autres outils Aide Bot restent disponibles.",
            inline=False,
        )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Une question → une réponse ciblée → ticket humain seulement si nécessaire")
    return e


def audit_embed(audit: GuardianAudit) -> discord.Embed:
    color = SUCCESS if audit.score >= 85 else WARNING if audit.score >= 60 else DANGER
    e = discord.Embed(
        title=f"Guardian — audit {audit.score}/100",
        description="Analyse automatique des permissions, accès privés et configurations sensibles.",
        color=color,
    )
    if audit.risks:
        lines = [f"**{risk.severity.upper()}** — {risk.detail}" for risk in audit.risks[:8]]
        e.add_field(name="Risques prioritaires", value="\n".join(lines)[:1024], inline=False)
    else:
        e.add_field(name="Risques prioritaires", value="Aucun risque important détecté par les règles actuelles.", inline=False)
    simulations = [
        f"**{name}** : {stats['visible']} accès visibles • {stats['manageable']} salons/catégories gérables"
        for name, stats in audit.personas.items()
    ]
    e.add_field(name="Simulation d’accès", value="\n".join(simulations), inline=False)
    e.set_footer(text="Guardian vérifie la configuration ; il ne lit pas les messages privés des membres.")
    return e


def guardian_panel_embed() -> discord.Embed:
    e = discord.Embed(
        title=GUARDIAN_TITLE,
        description=(
            "Guardian surveille la configuration du serveur comme un **contrôle d’intégrité**. Il peut mémoriser un état sûr, "
            "repérer ce qui change et restaurer les permissions après confirmation."
        ),
        color=0x2B2D31,
    )
    e.add_field(
        name="Audit",
        value="Permissions sensibles, fuite des espaces privés, rôles administrateur, simulation Membre/Helper/Formateur/VIP.",
        inline=False,
    )
    e.add_field(
        name="Surveillance",
        value="Après l’enregistrement d’un état sûr, un changement de rôle/salon/permission est comparé au snapshot et signalé dans les logs.",
        inline=False,
    )
    e.add_field(
        name="Rollback protégé",
        value="La restauration concerne les **permissions de rôles et overwrites de salons**. Elle exige une confirmation explicite et ne supprime pas les salons ou rôles créés après le snapshot.",
        inline=False,
    )
    e.set_footer(text="Aide Bot Guardian • audit → état sûr → détection du drift → restauration contrôlée")
    return e


async def _upsert_panel(
    bot: commands.Bot,
    channel: discord.TextChannel,
    *,
    embed: discord.Embed,
    view: discord.ui.View,
) -> None:
    if bot.user is None:
        return
    checked, existing = await find_bot_embed_by_title(channel, bot_user_id=bot.user.id, title=embed.title or "", limit=100)
    if existing is not None:
        try:
            await existing.edit(embed=embed, view=view)
        except (discord.Forbidden, discord.HTTPException):
            pass
        return
    if not checked:
        return
    try:
        await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())
    except (discord.Forbidden, discord.HTTPException):
        pass


async def _cleanup_legacy_video_panel(bot: commands.Bot, channel: discord.TextChannel) -> None:
    if bot.user is None:
        return
    try:
        async for message in channel.history(limit=100):
            if message.author.id != bot.user.id:
                continue
            titles = [embed.title or "" for embed in message.embeds]
            if any("Bibliothèque vidéo" in title or "Vidéos —" in title for title in titles):
                try:
                    await message.delete()
                except (discord.Forbidden, discord.HTTPException):
                    pass
    except (discord.Forbidden, discord.HTTPException):
        pass


class AskAIModal(discord.ui.Modal, title="Poser une question"):
    question = discord.ui.TextInput(
        label="Ta question",
        placeholder="Ex: pourquoi mon rôle Modérateur voit le salon Direction ?",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=1500,
    )

    def __init__(self, cog: "AssistantGuardianV52Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        allowed, reason = await self.cog.ai_limiter.allow(interaction.guild.id, interaction.user.id)
        if not allowed:
            return await interaction.response.send_message(reason or "Réessaie plus tard.", ephemeral=True)
        if not self.cog.ai.configured:
            return await interaction.response.send_message(
                "L’assistant IA n’est pas encore activé sur Aide Bot. Il manque la configuration `OPENAI_API_KEY` côté hébergement.",
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            answer, redacted = await self.cog.ai.answer(
                question=str(self.question).strip(),
                guild=interaction.guild,
                member=interaction.user,
            )
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as exc:
            return await interaction.followup.send(
                f"L’assistant IA est temporairement indisponible : {str(exc)[:300]}",
                ephemeral=True,
            )
        e = discord.Embed(title="Réponse de l’assistant", description=answer, color=COLOR)
        if redacted:
            e.add_field(
                name="Secret détecté",
                value="Une valeur ressemblant à un secret a été masquée avant l’envoi. Si c’était un vrai token ou une clé, régénère-la maintenant.",
                inline=False,
            )
        e.set_footer(text="Réponse générée pour t’aider • vérifie les actions sensibles avant de les appliquer")
        await interaction.followup.send(embed=e, ephemeral=True)


class AssistantPanelView(discord.ui.View):
    def __init__(self, cog: "AssistantGuardianV52Cog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Poser une question", style=discord.ButtonStyle.primary, custom_id="aidebot:v52:ai:ask")
    async def ask(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(AskAIModal(self.cog))


class RestoreGuardianModal(discord.ui.Modal, title="Restaurer les permissions"):
    confirmation = discord.ui.TextInput(label="Écris RESTAURER", placeholder="RESTAURER", max_length=10)

    def __init__(self, cog: "AssistantGuardianV52Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not self.cog._allowed(interaction.user, "config.manage"):
            return await interaction.response.send_message("Cette restauration est réservée à la Direction.", ephemeral=True)
        if str(self.confirmation).strip().upper() != "RESTAURER":
            return await interaction.response.send_message("Confirmation incorrecte. Aucune permission n’a été modifiée.", ephemeral=True)
        baseline = await self.cog.store.baseline(interaction.guild.id)
        if not baseline or not isinstance(baseline.get("snapshot"), dict):
            return await interaction.response.send_message("Aucun état sûr n’est enregistré pour ce serveur.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        result = await restore_permission_baseline(interaction.guild, baseline["snapshot"])
        current = snapshot_guild(interaction.guild)
        await self.cog.store.save_baseline(interaction.guild, current)
        self.cog._last_reported_hash.pop(interaction.guild.id, None)
        await interaction.followup.send(
            f"Restauration terminée : **{result['roles']} rôles** et **{result['channels']} salons/catégories** traités. "
            f"Éléments ignorés ou impossibles à modifier : **{result['skipped']}**.",
            ephemeral=True,
        )


class GuardianPanelView(discord.ui.View):
    def __init__(self, cog: "AssistantGuardianV52Cog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    async def _require(self, interaction: discord.Interaction, capability: str) -> bool:
        if isinstance(interaction.user, discord.Member) and self.cog._allowed(interaction.user, capability):
            return True
        await interaction.response.send_message("Tu n’as pas la permission d’utiliser cette action Guardian.", ephemeral=True)
        return False

    @discord.ui.button(label="Lancer un audit", style=discord.ButtonStyle.primary, custom_id="aidebot:v52:guardian:audit")
    async def audit(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not await self._require(interaction, "audit.run"):
            return
        await interaction.response.send_message(embed=audit_embed(audit_guild(interaction.guild)), ephemeral=True)

    @discord.ui.button(label="Enregistrer l’état sûr", style=discord.ButtonStyle.success, custom_id="aidebot:v52:guardian:baseline")
    async def baseline(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not await self._require(interaction, "config.manage"):
            return
        snapshot = snapshot_guild(interaction.guild)
        digest = await self.cog.store.save_baseline(interaction.guild, snapshot)
        self.cog._last_reported_hash.pop(interaction.guild.id, None)
        await interaction.response.send_message(
            f"État sûr enregistré. Empreinte : `{digest[:12]}`. Les prochains changements seront comparés à cette base.",
            ephemeral=True,
        )

    @discord.ui.button(label="Voir les changements", style=discord.ButtonStyle.secondary, custom_id="aidebot:v52:guardian:diff")
    async def diff(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not await self._require(interaction, "audit.run"):
            return
        baseline = await self.cog.store.baseline(interaction.guild.id)
        if not baseline or not isinstance(baseline.get("snapshot"), dict):
            return await interaction.response.send_message("Aucun état sûr n’est enregistré.", ephemeral=True)
        changes = diff_snapshots(baseline["snapshot"], snapshot_guild(interaction.guild))
        if not changes:
            return await interaction.response.send_message("Aucun écart : la configuration correspond à l’état sûr.", ephemeral=True)
        e = discord.Embed(
            title=f"Guardian — {len(changes)} changement(s)",
            description="\n".join(f"• {item}" for item in changes[:20]),
            color=WARNING,
        )
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="Restaurer les permissions", style=discord.ButtonStyle.danger, custom_id="aidebot:v52:guardian:restore")
    async def restore(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._require(interaction, "config.manage"):
            return
        await interaction.response.send_modal(RestoreGuardianModal(self.cog))


class AssistantGuardianV52Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        guardian_path = os.getenv("AIDEBOT_GUARDIAN_PATH", "").strip()
        if not guardian_path:
            guardian_path = str(Path(bot.settings.db_path).with_name("guardian_baselines.json"))
        self.store = GuardianStore(guardian_path)
        self.ai = AideAIClient()
        daily_limit = int(os.getenv("AIDEBOT_AI_DAILY_LIMIT", "25") or 25)
        self.ai_limiter = AIUsageLimiter(daily_limit=daily_limit)
        self._reconciled_guilds: set[int] = set()
        self._drift_tasks: dict[int, asyncio.Task] = {}
        self._last_reported_hash: dict[int, str] = {}

    async def cog_load(self) -> None:
        self.bot.add_view(AssistantPanelView(self))
        self.bot.add_view(GuardianPanelView(self))

    def _allowed(self, member: discord.Member, capability: str) -> bool:
        return decide(member, capability).allowed

    async def _ensure_ai_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel = discord.utils.get(guild.text_channels, name=AI_CHANNEL)
        if channel is not None:
            return channel
        legacy = discord.utils.get(guild.text_channels, name=LEGACY_VIDEO_CHANNEL)
        if legacy is None:
            return None
        try:
            await legacy.edit(name=AI_CHANNEL, reason="Aide Bot V52 — assistant spécialisé")
            return legacy
        except (discord.Forbidden, discord.HTTPException):
            return None

    async def _reconcile_guild(self, guild: discord.Guild) -> None:
        ai_channel = await self._ensure_ai_channel(guild)
        if ai_channel is not None:
            await _cleanup_legacy_video_panel(self.bot, ai_channel)
            await _upsert_panel(
                self.bot,
                ai_channel,
                embed=assistant_panel_embed(self.ai.configured),
                view=AssistantPanelView(self),
            )

        staff = discord.utils.get(guild.text_channels, name=STAFF_CHANNEL)
        if staff is not None:
            await _upsert_panel(self.bot, staff, embed=guardian_panel_embed(), view=GuardianPanelView(self))

        baseline = await self.store.baseline(guild.id)
        if baseline is None:
            await self.store.save_baseline(guild, snapshot_guild(guild))

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            if guild.id in self._reconciled_guilds:
                continue
            self._reconciled_guilds.add(guild.id)
            await self._reconcile_guild(guild)

    def _schedule_drift_check(self, guild: discord.Guild) -> None:
        previous = self._drift_tasks.get(guild.id)
        if previous and not previous.done():
            previous.cancel()
        self._drift_tasks[guild.id] = asyncio.create_task(self._check_drift_after_delay(guild))

    async def _check_drift_after_delay(self, guild: discord.Guild) -> None:
        try:
            await asyncio.sleep(2.0)
            baseline = await self.store.baseline(guild.id)
            if not baseline or not isinstance(baseline.get("snapshot"), dict):
                return
            current = snapshot_guild(guild)
            current_hash = snapshot_hash(current)
            if current_hash == baseline.get("hash"):
                self._last_reported_hash.pop(guild.id, None)
                return
            if self._last_reported_hash.get(guild.id) == current_hash:
                return
            changes = diff_snapshots(baseline["snapshot"], current)
            if not changes:
                return
            self._last_reported_hash[guild.id] = current_hash
            log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL)
            if log_channel is None:
                return
            e = discord.Embed(
                title="Guardian — changement de configuration détecté",
                description="\n".join(f"• {item}" for item in changes[:15]),
                color=WARNING,
            )
            e.add_field(
                name="Action",
                value="Vérifie le changement dans `📋・staff`. Si l’état actuel est volontaire, enregistre un nouvel état sûr ; sinon utilise la restauration contrôlée.",
                inline=False,
            )
            e.set_footer(text="Guardian compare la configuration actuelle au dernier état sûr enregistré")
            await log_channel.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
        except asyncio.CancelledError:
            return
        except (discord.Forbidden, discord.HTTPException):
            return

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        self._schedule_drift_check(channel.guild)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        self._schedule_drift_check(channel.guild)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> None:
        self._schedule_drift_check(after.guild)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        self._schedule_drift_check(role.guild)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        self._schedule_drift_check(role.guild)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        self._schedule_drift_check(after.guild)

    async def cog_unload(self) -> None:
        for task in self._drift_tasks.values():
            if not task.done():
                task.cancel()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AssistantGuardianV52Cog(bot))
