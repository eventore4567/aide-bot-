from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.blueprint import CATEGORY_SPECS, ROLE_SPECS
from aidebot.cogs.assistant_guardian_v52 import GuardianPanelView, _upsert_panel, guardian_panel_embed
from aidebot.cogs.branding_role_studio_v59 import (
    BrandingHomeViewV59,
    RoleStudioViewV59,
    branding_embed_v59,
    role_studio_report,
)
from aidebot.cogs.power_suite_v58 import (
    BLUEPRINTS,
    DANGER,
    BlueprintHomeViewV58,
    IncidentViewV58,
    PermissionLabModalV58,
    PowerSuiteV58Cog,
)
from aidebot.cogs.setup_experience_v55 import SetupExperienceV55Cog
from aidebot.experience_content import BANNER_URL
from aidebot.permissions import decide

COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F
COMMUNITY = 0x1ABC9C

ENTRAIDE_CHANNEL = "🤝・entraide"
SOLUTIONS_CHANNEL = "📌・solutions"
STAFF_CHANNEL = "📋・staff"
COMMUNITY_TITLE = "Aide Bot — Entraide communautaire"
SOLUTIONS_TITLE = "Aide Bot — Solutions validées"
STAFF_TITLE = "Aide Bot — Outils avancés"

THEMES: dict[str, tuple[str, str]] = {
    "clean": ("Clean", "5865F2"),
    "minimal": ("Minimal", "2B2D31"),
    "luxury": ("Luxury", "D4AF37"),
    "gaming": ("Gaming", "57F287"),
    "cyber": ("Cyber", "00D4FF"),
    "creator": ("Creator", "EB459E"),
}

SERVER_PROFILES: dict[str, tuple[str, str]] = {
    "auto": ("Automatique", "Aide Bot analyse l’existant et reste compact."),
    "community": ("Communauté", "Priorité à l’entraide, aux solutions et à l’onboarding."),
    "gaming": ("Gaming", "Navigation courte, rôles d’intérêt et support communautaire."),
    "creator": ("Créateur", "Accueil, communauté, ressources et accompagnement."),
    "support": ("Support", "Centre d’aide, tickets, diagnostic et suivi."),
    "education": ("Éducation", "Formations, mentors, progression et solutions validées."),
    "dev": ("Développement", "Bots, code, hébergement, Git et diagnostics techniques."),
}

SENSITIVE_EVERYONE = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "ban_members",
    "kick_members",
    "mention_everyone",
)


class ProductStateStore:
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
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    async def _mutate(self, guild_id: int, callback) -> Any:
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            guilds = payload.setdefault("guilds", {})
            state = guilds.setdefault(str(guild_id), {})
            result = callback(state)
            await asyncio.to_thread(self._write_sync, payload)
            return result

    async def preferences(self, guild_id: int) -> dict[str, str]:
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            state = payload.get("guilds", {}).get(str(guild_id), {})
            prefs = state.get("preferences", {}) if isinstance(state, dict) else {}
            return dict(prefs) if isinstance(prefs, dict) else {}

    async def save_preferences(self, guild_id: int, *, profile: str, theme: str) -> None:
        def change(state: dict[str, Any]) -> None:
            state["preferences"] = {"profile": profile, "theme": theme, "updated_at": datetime.now(timezone.utc).isoformat()}
        await self._mutate(guild_id, change)

    async def active_questions_for(self, guild_id: int, user_id: int) -> list[dict[str, Any]]:
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            questions = payload.get("guilds", {}).get(str(guild_id), {}).get("questions", {})
            if not isinstance(questions, dict):
                return []
            return [dict(item) for item in questions.values() if isinstance(item, dict) and item.get("author_id") == user_id and item.get("status") == "open"]

    async def add_question(self, guild_id: int, *, thread_id: int, author_id: int, title: str, context: str) -> None:
        def change(state: dict[str, Any]) -> None:
            questions = state.setdefault("questions", {})
            questions[str(thread_id)] = {
                "thread_id": thread_id,
                "author_id": author_id,
                "title": title,
                "context": context,
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        await self._mutate(guild_id, change)

    async def get_question(self, guild_id: int, thread_id: int) -> dict[str, Any] | None:
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            item = payload.get("guilds", {}).get(str(guild_id), {}).get("questions", {}).get(str(thread_id))
            return dict(item) if isinstance(item, dict) else None

    async def resolve_question(self, guild_id: int, thread_id: int, *, resolver_id: int, solution: str) -> dict[str, Any] | None:
        result: dict[str, Any] | None = None
        def change(state: dict[str, Any]) -> None:
            nonlocal result
            questions = state.setdefault("questions", {})
            item = questions.get(str(thread_id))
            if not isinstance(item, dict):
                return
            item["status"] = "resolved"
            item["resolver_id"] = resolver_id
            item["solution"] = solution
            item["resolved_at"] = datetime.now(timezone.utc).isoformat()
            solutions = state.setdefault("solutions", [])
            solutions.append(dict(item))
            state["solutions"] = solutions[-250:]
            result = dict(item)
        await self._mutate(guild_id, change)
        return result

    async def search_solutions(self, guild_id: int, query: str) -> list[dict[str, Any]]:
        words = {word for word in re.findall(r"[a-z0-9à-ÿ]+", query.casefold()) if len(word) >= 3}
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            items = payload.get("guilds", {}).get(str(guild_id), {}).get("solutions", [])
            if not isinstance(items, list):
                return []
            scored: list[tuple[int, dict[str, Any]]] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                haystack = f"{item.get('title', '')} {item.get('context', '')} {item.get('solution', '')}".casefold()
                score = sum(1 for word in words if word in haystack)
                if score or not words:
                    scored.append((score, dict(item)))
            scored.sort(key=lambda row: (row[0], row[1].get("resolved_at", "")), reverse=True)
            return [item for _score, item in scored[:5]]

    async def community_stats(self, guild_id: int) -> dict[str, int]:
        async with self._lock:
            payload = await asyncio.to_thread(self._read_sync)
            state = payload.get("guilds", {}).get(str(guild_id), {})
            questions = state.get("questions", {}) if isinstance(state, dict) else {}
            solutions = state.get("solutions", []) if isinstance(state, dict) else []
            open_count = sum(1 for item in questions.values() if isinstance(item, dict) and item.get("status") == "open") if isinstance(questions, dict) else 0
            return {"open": open_count, "resolved": len(solutions) if isinstance(solutions, list) else 0}


@dataclass(frozen=True)
class Audit360:
    score: int
    grade: str
    subscores: dict[str, int]
    findings: tuple[str, ...]


def _grade(score: int) -> str:
    return "S" if score >= 92 else "A" if score >= 82 else "B" if score >= 70 else "C" if score >= 55 else "D"


def audit360(guild: discord.Guild) -> Audit360:
    scores = {
        "Sécurité": 100,
        "Permissions": 100,
        "Organisation": 100,
        "Onboarding": 100,
        "Support": 100,
        "Staff": 100,
        "Bot": 100,
    }
    findings: list[str] = []

    everyone = guild.default_role.permissions
    dangerous_everyone = [name for name in SENSITIVE_EVERYONE if getattr(everyone, name, False)]
    if dangerous_everyone:
        scores["Sécurité"] -= min(55, len(dangerous_everyone) * 12)
        findings.append("CRITIQUE — @everyone possède des permissions sensibles : " + ", ".join(dangerous_everyone))

    admin_roles = [role for role in guild.roles if role != guild.default_role and role.permissions.administrator]
    if len(admin_roles) > 2:
        scores["Sécurité"] -= min(30, (len(admin_roles) - 2) * 8)
        findings.append(f"IMPORTANT — {len(admin_roles)} rôles ont Administrateur.")

    me = guild.me
    if me is None:
        scores["Bot"] = 0
        findings.append("CRITIQUE — impossible d’identifier Aide Bot dans le serveur.")
    else:
        needed = ("manage_roles", "manage_channels", "view_channel", "send_messages", "embed_links", "read_message_history")
        missing = [name for name in needed if not getattr(me.guild_permissions, name, False)]
        scores["Bot"] -= min(80, len(missing) * 15)
        if missing:
            findings.append("CRITIQUE — permissions bot manquantes : " + ", ".join(missing))
        blocked = [role for role in guild.roles if role != guild.default_role and not role.managed and role >= me.top_role]
        scores["Permissions"] -= min(35, len(blocked) * 4)
        if blocked:
            findings.append(f"IMPORTANT — {len(blocked)} rôle(s) sont au-dessus d’Aide Bot.")

    names: dict[str, int] = {}
    for channel in guild.channels:
        names[channel.name.casefold()] = names.get(channel.name.casefold(), 0) + 1
    duplicates = sum(1 for count in names.values() if count > 1)
    empty_categories = sum(1 for category in guild.categories if not category.channels)
    uncategorized = sum(1 for channel in guild.text_channels if channel.category is None)
    scores["Organisation"] -= min(20, duplicates * 4)
    scores["Organisation"] -= min(15, empty_categories * 3)
    scores["Organisation"] -= min(15, max(0, uncategorized - 2) * 2)
    if len(guild.channels) > 55:
        scores["Organisation"] -= 12
        findings.append("CONFORT — le serveur contient beaucoup de salons ; vérifie que chacun a une mission claire.")

    required_onboarding = {"👋・bienvenue", "📜・règlement", "🎓・centre-aide"}
    present = {channel.name for channel in guild.text_channels}
    missing_onboarding = sorted(required_onboarding - present)
    scores["Onboarding"] -= len(missing_onboarding) * 22
    if missing_onboarding:
        findings.append("IMPORTANT — onboarding incomplet : " + ", ".join(missing_onboarding))

    support_expected = {"🎓・centre-aide", "🎓・formations", ENTRAIDE_CHANNEL, SOLUTIONS_CHANNEL}
    missing_support = sorted(support_expected - present)
    scores["Support"] -= len(missing_support) * 15
    if missing_support:
        findings.append("IMPORTANT — parcours aide incomplet : " + ", ".join(missing_support))

    staff_expected = {"📋・staff", "🧾・logs", "🧠・suivi-formations"}
    missing_staff = sorted(staff_expected - present)
    scores["Staff"] -= len(missing_staff) * 20

    role_report = role_studio_report(guild)
    scores["Permissions"] -= min(25, len(role_report["dangerous"]) * 3)
    scores["Permissions"] -= min(15, len(role_report["duplicates"]) * 4)

    normalized = {name: max(0, min(100, value)) for name, value in scores.items()}
    total = round(sum(normalized.values()) / len(normalized))
    return Audit360(total, _grade(total), normalized, tuple(findings[:12]))


def audit360_embed(guild: discord.Guild) -> discord.Embed:
    audit = audit360(guild)
    color = SUCCESS if audit.score >= 82 else WARNING if audit.score >= 60 else DANGER
    embed = discord.Embed(
        title=f"Audit 360 — Grade {audit.grade} • {audit.score}/100",
        description="Vue produit du serveur : sécurité, permissions, organisation, onboarding, support, staff et capacité du bot.",
        color=color,
    )
    for name, value in audit.subscores.items():
        embed.add_field(name=name, value=f"**{value}/100**", inline=True)
    embed.add_field(
        name="Priorités",
        value="\n".join(f"• {item}" for item in audit.findings)[:1024] if audit.findings else "Aucun problème important détecté.",
        inline=False,
    )
    embed.set_footer(text="Audit 360 • analyse de configuration, jamais du contenu privé")
    return embed


def role360_embed(guild: discord.Guild) -> discord.Embed:
    report = role_studio_report(guild)
    empty = [role for role in guild.roles if role != guild.default_role and not role.members and not role.managed]
    permission_groups: dict[int, list[str]] = {}
    for role in guild.roles:
        if role == guild.default_role or role.managed:
            continue
        permission_groups.setdefault(role.permissions.value, []).append(role.name)
    same_permissions = [names for names in permission_groups.values() if len(names) > 1]
    embed = discord.Embed(
        title="Role Studio — Vue 360",
        description="Hiérarchie, rôles Aide Bot, permissions sensibles, doublons et nettoyage suggéré. Rien n’est supprimé automatiquement.",
        color=SUCCESS if not report["missing"] and not report["dangerous"] else WARNING,
    )
    embed.add_field(name="Total", value=str(report["total"]), inline=True)
    embed.add_field(name="Canoniques manquants", value=str(len(report["missing"])), inline=True)
    embed.add_field(name="Au-dessus du bot", value=str(len(report["blocked"])), inline=True)
    embed.add_field(name="Sans membre", value=str(len(empty)), inline=True)
    embed.add_field(name="Noms doublons", value=str(len(report["duplicates"])), inline=True)
    embed.add_field(name="Permissions identiques", value=str(len(same_permissions)), inline=True)
    if report["dangerous"]:
        embed.add_field(name="À revoir", value="\n".join(f"• {item}" for item in report["dangerous"][:8])[:1024], inline=False)
    if same_permissions:
        embed.add_field(name="Rôles potentiellement redondants", value="\n".join(" • ".join(group[:4]) for group in same_permissions[:5])[:1024], inline=False)
    embed.set_footer(text="Role Studio • audit visible • réparation non destructive")
    return embed


def community_home_embed() -> discord.Embed:
    embed = discord.Embed(
        title=COMMUNITY_TITLE,
        description=(
            "Un seul point d’entrée pour l’entraide entre membres. Chaque question devient un thread propre, "
            "puis la réponse finale peut être transformée en solution réutilisable."
        ),
        color=COMMUNITY,
    )
    embed.add_field(name="Poser une question", value="Formulaire court → thread public → réponses de la communauté et des mentors.", inline=True)
    embed.add_field(name="Chercher une solution", value="Recherche dans les problèmes déjà résolus sans ouvrir un nouveau ticket.", inline=True)
    embed.add_field(name="Escalade propre", value="Si la communauté ne suffit pas, le Centre d’aide et les tickets restent disponibles.", inline=True)
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Aide Bot • entraide structurée, pas un salon général supplémentaire")
    return embed


def solutions_embed() -> discord.Embed:
    embed = discord.Embed(
        title=SOLUTIONS_TITLE,
        description="Archive lisible des problèmes réellement résolus par la communauté. Utilise la recherche depuis le panneau Entraide.",
        color=COMMUNITY,
    )
    embed.add_field(name="Principe", value="Une solution apparaît ici seulement après résolution explicite d’une question.", inline=False)
    embed.set_image(url=BANNER_URL)
    return embed


class AskCommunityModal(discord.ui.Modal, title="Poser une question à la communauté"):
    title_input = discord.ui.TextInput(label="Problème", placeholder="Ex: mon bot ne peut pas attribuer un rôle", min_length=8, max_length=90)
    context = discord.ui.TextInput(label="Contexte et ce que tu as déjà essayé", style=discord.TextStyle.paragraph, min_length=20, max_length=900)

    def __init__(self, cog: "ProductSuiteV60Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        active = await self.cog.store.active_questions_for(interaction.guild.id, interaction.user.id)
        if len(active) >= 3:
            return await interaction.response.send_message("Tu as déjà **3 questions ouvertes**. Résous ou ferme-en une avant d’en créer une autre.", ephemeral=True)
        channel = discord.utils.get(interaction.guild.text_channels, name=ENTRAIDE_CHANNEL)
        if channel is None:
            return await interaction.response.send_message("L’espace d’entraide n’est pas prêt. Un administrateur doit relancer `/setup`.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        title = str(self.title_input).strip()
        context = str(self.context).strip()
        starter = discord.Embed(title=title, description=context, color=COMMUNITY)
        starter.add_field(name="Auteur", value=interaction.user.mention, inline=True)
        starter.add_field(name="Statut", value="Ouvert", inline=True)
        starter.set_footer(text="Réponds dans le thread • aucun token, mot de passe ou secret")
        try:
            message = await channel.send(embed=starter, allowed_mentions=discord.AllowedMentions.none())
            thread_name = re.sub(r"\s+", " ", title)[:85]
            thread = await message.create_thread(name=thread_name, auto_archive_duration=1440)
            await self.cog.store.add_question(interaction.guild.id, thread_id=thread.id, author_id=interaction.user.id, title=title, context=context)
            await thread.send(
                "Expliquez les étapes de diagnostic et évitez de demander des secrets. Quand une réponse fonctionne, utilisez **Marquer résolu**.",
                view=QuestionThreadView(self.cog),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            return await interaction.followup.send("Impossible de créer le thread. Vérifie les permissions de threads d’Aide Bot.", ephemeral=True)
        await interaction.followup.send(f"Question créée : {thread.mention}", ephemeral=True)


class SearchSolutionModal(discord.ui.Modal, title="Chercher dans les solutions"):
    query = discord.ui.TextInput(label="Mots-clés", placeholder="permissions rôle invisible", min_length=3, max_length=120)

    def __init__(self, cog: "ProductSuiteV60Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        results = await self.cog.store.search_solutions(interaction.guild.id, str(self.query))
        if not results:
            return await interaction.response.send_message("Aucune solution validée ne correspond encore à cette recherche.", ephemeral=True)
        embed = discord.Embed(title="Solutions trouvées", color=COMMUNITY)
        for item in results:
            embed.add_field(
                name=str(item.get("title", "Solution"))[:256],
                value=str(item.get("solution", ""))[:900] or "Solution sans résumé.",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ResolveQuestionModal(discord.ui.Modal, title="Marquer cette question résolue"):
    solution = discord.ui.TextInput(label="Solution qui a fonctionné", style=discord.TextStyle.paragraph, min_length=15, max_length=900)

    def __init__(self, cog: "ProductSuiteV60Cog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.channel, discord.Thread) or not isinstance(interaction.user, discord.Member):
            return
        item = await self.cog.store.get_question(interaction.guild.id, interaction.channel.id)
        if not item:
            return await interaction.response.send_message("Cette question n’est pas enregistrée comme demande communautaire.", ephemeral=True)
        is_author = item.get("author_id") == interaction.user.id
        is_staff = interaction.user.guild_permissions.manage_messages or decide(interaction.user, "help.claim").allowed
        if not (is_author or is_staff):
            return await interaction.response.send_message("Seul l’auteur ou un membre du staff d’aide peut valider la solution.", ephemeral=True)
        if item.get("status") == "resolved":
            return await interaction.response.send_message("Cette question est déjà résolue.", ephemeral=True)

        result = await self.cog.store.resolve_question(
            interaction.guild.id,
            interaction.channel.id,
            resolver_id=interaction.user.id,
            solution=str(self.solution).strip(),
        )
        if not result:
            return await interaction.response.send_message("Impossible d’enregistrer la solution.", ephemeral=True)
        await interaction.response.send_message("Solution enregistrée. Ce thread va être archivé.")
        solutions = discord.utils.get(interaction.guild.text_channels, name=SOLUTIONS_CHANNEL)
        if solutions is not None:
            embed = discord.Embed(title=str(result.get("title", "Solution")), description=str(result.get("solution", "")), color=SUCCESS)
            embed.add_field(name="Contexte", value=str(result.get("context", ""))[:900], inline=False)
            embed.set_footer(text="Solution communautaire validée")
            try:
                await solutions.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            except (discord.Forbidden, discord.HTTPException):
                pass
        try:
            await interaction.channel.edit(archived=True, reason="Aide Bot — question résolue")
        except (discord.Forbidden, discord.HTTPException):
            pass


class QuestionThreadView(discord.ui.View):
    def __init__(self, cog: "ProductSuiteV60Cog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Marquer résolu", style=discord.ButtonStyle.success, custom_id="aidebot:v60:community:resolve")
    async def resolve(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(ResolveQuestionModal(self.cog))

    @discord.ui.button(label="Centre d’aide", style=discord.ButtonStyle.secondary, custom_id="aidebot:v60:community:help")
    async def help_center(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.help_system_v54 import HelpHomeView, help_home_embed
        await interaction.response.send_message(embed=help_home_embed(), view=HelpHomeView(self.cog.bot), ephemeral=True)


class CommunityHomeView(discord.ui.View):
    def __init__(self, cog: "ProductSuiteV60Cog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Poser une question", style=discord.ButtonStyle.primary, custom_id="aidebot:v60:community:ask")
    async def ask(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(AskCommunityModal(self.cog))

    @discord.ui.button(label="Chercher une solution", style=discord.ButtonStyle.secondary, custom_id="aidebot:v60:community:search")
    async def search(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(SearchSolutionModal(self.cog))

    @discord.ui.button(label="Mes questions", style=discord.ButtonStyle.secondary, custom_id="aidebot:v60:community:mine")
    async def mine(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild:
            return
        active = await self.cog.store.active_questions_for(interaction.guild.id, interaction.user.id)
        if not active:
            return await interaction.response.send_message("Tu n’as aucune question communautaire ouverte.", ephemeral=True)
        lines = []
        for item in active[:5]:
            thread = interaction.guild.get_thread(int(item.get("thread_id", 0)))
            lines.append(f"• {thread.mention if thread else item.get('title', 'Question')}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


class ThemeSelectV60(discord.ui.Select):
    def __init__(self, cog: "ProductSuiteV60Cog", *, setup_mode: bool = False) -> None:
        self.cog = cog
        self.setup_mode = setup_mode
        super().__init__(
            placeholder="Choisis un thème visuel",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=label, value=key, description=f"Accent #{accent}") for key, (label, accent) in THEMES.items()],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if self.setup_mode:
            view = self.view
            if isinstance(view, SetupWizardViewV60):
                view.theme = self.values[0]
                return await interaction.response.edit_message(embed=view.preview_embed(interaction.guild), view=view)
        if not decide(interaction.user, "config.manage").allowed:
            return await interaction.response.send_message("Le thème est réservé à la Direction.", ephemeral=True)
        await self.cog.apply_theme(interaction.guild, self.values[0])
        label, accent = THEMES[self.values[0]]
        await interaction.response.send_message(f"Thème **{label}** enregistré et appliqué aux panneaux compatibles (#{accent}).", ephemeral=True)


class BrandingThemesViewV60(discord.ui.View):
    def __init__(self, cog: "ProductSuiteV60Cog") -> None:
        super().__init__(timeout=600)
        self.cog = cog
        self.add_item(ThemeSelectV60(cog))

    @discord.ui.button(label="Réglages avancés", style=discord.ButtonStyle.primary, row=1)
    async def advanced(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        brand_cog = interaction.client.get_cog("BrandRoleStudioV59Cog")
        if brand_cog is None or not interaction.guild:
            return await interaction.response.send_message("Branding Studio est temporairement indisponible.", ephemeral=True)
        brand = await brand_cog.store.get_brand(interaction.guild.id)
        await interaction.response.send_message(embed=branding_embed_v59(interaction.guild, brand), view=BrandingHomeViewV59(brand_cog), ephemeral=True)


class StaffSelectV60(discord.ui.Select):
    def __init__(self, cog: "ProductSuiteV60Cog") -> None:
        self.cog = cog
        super().__init__(
            placeholder="Choisis un outil",
            min_values=1,
            max_values=1,
            custom_id="aidebot:v60:staff:tool",
            options=[
                discord.SelectOption(label="Audit 360", value="audit", description="Score S-A-B-C-D sur 7 domaines"),
                discord.SelectOption(label="Permission Lab", value="permissions", description="Tester les permissions effectives"),
                discord.SelectOption(label="Guardian", value="guardian", description="État sûr, diff et restauration"),
                discord.SelectOption(label="Mode incident", value="incident", description="Protection d’urgence réversible"),
                discord.SelectOption(label="Studio structure", value="blueprint", description="Prévisualiser puis construire une structure"),
                discord.SelectOption(label="Branding Studio", value="branding", description="Thèmes, bannières, couleurs et identité"),
                discord.SelectOption(label="Role Studio", value="roles", description="Hiérarchie, risques, réparation et self-roles"),
                discord.SelectOption(label="Communauté", value="community", description="Questions ouvertes et solutions validées"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not decide(interaction.user, "audit.run").allowed:
            return await interaction.response.send_message("Ces outils sont réservés au staff autorisé.", ephemeral=True)
        choice = self.values[0]
        if choice == "audit":
            return await interaction.response.send_message(embed=audit360_embed(interaction.guild), ephemeral=True)
        if choice == "permissions":
            return await interaction.response.send_modal(PermissionLabModalV58())
        if choice == "guardian":
            guardian = interaction.client.get_cog("AssistantGuardianV52Cog")
            if guardian is None:
                return await interaction.response.send_message("Guardian est temporairement indisponible.", ephemeral=True)
            return await interaction.response.send_message(embed=guardian_panel_embed(), view=GuardianPanelView(guardian), ephemeral=True)
        if choice == "incident":
            power = interaction.client.get_cog("PowerSuiteV58Cog")
            if not isinstance(power, PowerSuiteV58Cog):
                return await interaction.response.send_message("Mode incident temporairement indisponible.", ephemeral=True)
            embed = discord.Embed(title="Mode incident", description="Protection réversible de `@everyone`. Aucun salon, rôle ou membre n’est supprimé.", color=DANGER)
            return await interaction.response.send_message(embed=embed, view=IncidentViewV58(power), ephemeral=True)
        if choice == "blueprint":
            power = interaction.client.get_cog("PowerSuiteV58Cog")
            if not isinstance(power, PowerSuiteV58Cog):
                return await interaction.response.send_message("Studio structure temporairement indisponible.", ephemeral=True)
            embed = discord.Embed(title="Studio structure", description=f"**{len(BLUEPRINTS)} modèles** disponibles. Prévisualisation obligatoire avant création.", color=COLOR)
            return await interaction.response.send_message(embed=embed, view=BlueprintHomeViewV58(power), ephemeral=True)
        if choice == "branding":
            brand_cog = interaction.client.get_cog("BrandRoleStudioV59Cog")
            if brand_cog is None:
                return await interaction.response.send_message("Branding Studio est temporairement indisponible.", ephemeral=True)
            brand = await brand_cog.store.get_brand(interaction.guild.id)
            return await interaction.response.send_message(embed=branding_embed_v59(interaction.guild, brand), view=BrandingThemesViewV60(self.cog), ephemeral=True)
        if choice == "roles":
            brand_cog = interaction.client.get_cog("BrandRoleStudioV59Cog")
            if brand_cog is None:
                return await interaction.response.send_message("Role Studio est temporairement indisponible.", ephemeral=True)
            return await interaction.response.send_message(embed=role360_embed(interaction.guild), view=RoleStudioViewV59(brand_cog), ephemeral=True)
        if choice == "community":
            stats = await self.cog.store.community_stats(interaction.guild.id)
            embed = discord.Embed(title="Communauté d’entraide", color=COMMUNITY)
            embed.add_field(name="Questions ouvertes", value=str(stats["open"]), inline=True)
            embed.add_field(name="Solutions validées", value=str(stats["resolved"]), inline=True)
            embed.add_field(name="Principe", value="Les questions restent dans des threads et les solutions validées sont archivées dans `📌・solutions`.", inline=False)
            return await interaction.response.send_message(embed=embed, ephemeral=True)


class StaffViewV60(discord.ui.View):
    def __init__(self, cog: "ProductSuiteV60Cog") -> None:
        super().__init__(timeout=None)
        self.add_item(StaffSelectV60(cog))


def staff_embed_v60() -> discord.Embed:
    embed = discord.Embed(
        title=STAFF_TITLE,
        description="Un seul panneau staff. Chaque outil a une mission différente et les actions sensibles restent confirmées.",
        color=COLOR,
    )
    embed.add_field(name="Audit & sécurité", value="Audit 360 • Permission Lab • Guardian • Mode incident", inline=False)
    embed.add_field(name="Construction", value="Studio structure • Branding Studio • Role Studio", inline=False)
    embed.add_field(name="Support", value="Suivi de la communauté d’entraide et des solutions validées", inline=False)
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Aide Bot • administration sans dashboard externe")
    return embed


class ModeSelectV60(discord.ui.Select):
    def __init__(self, view: "SetupWizardViewV60") -> None:
        self.wizard = view
        super().__init__(
            placeholder="1. Choisis le mode",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Installer / réparer", value="install", description="Réutilise l’existant et complète ce qui manque"),
                discord.SelectOption(label="Vérifier seulement", value="verify", description="Audit sans modifier le serveur"),
                discord.SelectOption(label="Réparer les panneaux", value="panels", description="Republie/répare les panneaux sans refaire la structure"),
                discord.SelectOption(label="Audit 360 seulement", value="audit", description="Score détaillé sans modification"),
            ],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.wizard.mode = self.values[0]
        await interaction.response.edit_message(embed=self.wizard.preview_embed(interaction.guild), view=self.wizard)


class ProfileSelectV60(discord.ui.Select):
    def __init__(self, view: "SetupWizardViewV60") -> None:
        self.wizard = view
        super().__init__(
            placeholder="2. Choisis le profil serveur",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=label, value=key, description=description[:100]) for key, (label, description) in SERVER_PROFILES.items()],
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.wizard.profile = self.values[0]
        await interaction.response.edit_message(embed=self.wizard.preview_embed(interaction.guild), view=self.wizard)


class SetupWizardViewV60(discord.ui.View):
    def __init__(self, cog: "ProductSuiteV60Cog", user_id: int) -> None:
        super().__init__(timeout=900)
        self.cog = cog
        self.user_id = int(user_id)
        self.mode = "install"
        self.profile = "auto"
        self.theme = "clean"
        self.add_item(ModeSelectV60(self))
        self.add_item(ProfileSelectV60(self))
        theme = ThemeSelectV60(cog, setup_mode=True)
        theme.row = 2
        self.add_item(theme)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.user_id:
            return True
        await interaction.response.send_message("Seule la personne qui a lancé `/setup` peut utiliser cet installateur.", ephemeral=True)
        return False

    def preview_embed(self, guild: discord.Guild | None) -> discord.Embed:
        mode_labels = {"install": "Installer / réparer", "verify": "Vérifier seulement", "panels": "Réparer les panneaux", "audit": "Audit 360 seulement"}
        profile_label, profile_description = SERVER_PROFILES[self.profile]
        theme_label, accent = THEMES[self.theme]
        embed = discord.Embed(
            title="Aide Bot — Installateur intelligent",
            description="Configure ce que tu veux faire puis vérifie l’aperçu. Aucune action sensible n’est lancée avant **Appliquer**.",
            color=int(accent, 16),
        )
        embed.add_field(name="Mode", value=mode_labels[self.mode], inline=True)
        embed.add_field(name="Profil", value=profile_label, inline=True)
        embed.add_field(name="Thème", value=f"{theme_label} • #{accent}", inline=True)
        embed.add_field(name="Profil choisi", value=profile_description, inline=False)
        if guild is not None:
            audit = audit360(guild)
            embed.add_field(name="État actuel", value=f"Grade **{audit.grade}** • **{audit.score}/100**", inline=True)
            embed.add_field(name="Structure Aide Bot", value=f"**{len(ROLE_SPECS)} rôles** • **{sum(len(ch) for _, ch in CATEGORY_SPECS)} salons permanents**", inline=True)
        embed.add_field(name="Sécurité", value="Snapshot avant installation • réutilisation de l’existant • aucun contenu membre supprimé • actions sensibles confirmées", inline=False)
        embed.set_footer(text="Tu peux changer les 3 menus avant d’appliquer")
        return embed

    @discord.ui.button(label="Appliquer", style=discord.ButtonStyle.success, row=3)
    async def apply(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild:
            return
        await self.cog.store.save_preferences(interaction.guild.id, profile=self.profile, theme=self.theme)
        await self.cog.apply_theme(interaction.guild, self.theme, apply_now=False)
        base = interaction.client.get_cog("SetupExperienceV55Cog")
        if not isinstance(base, SetupExperienceV55Cog):
            return await interaction.response.send_message("Le moteur principal `/setup` est indisponible.", ephemeral=True)
        if self.mode == "audit":
            return await interaction.response.edit_message(embed=audit360_embed(interaction.guild), view=None)
        if self.mode == "verify":
            return await base.verify_only(interaction)
        if self.mode == "panels":
            await interaction.response.defer(ephemeral=True, thinking=True)
            channels = {channel.name: channel for channel in interaction.guild.text_channels}
            roles = {role.name: role for role in interaction.guild.roles}
            actions = await base._publish_panels(interaction.guild, channels, roles)
            await self.cog.reconcile_guild(interaction.guild)
            brand_cog = interaction.client.get_cog("BrandRoleStudioV59Cog")
            changed = await brand_cog.apply_panel_brand(interaction.guild) if brand_cog is not None else 0
            failed = sum(1 for _name, state in actions if state in {"failed", "skipped", "absent"})
            embed = discord.Embed(title="Panneaux réparés", description=f"Panneaux traités : **{len(actions)}** • incidents : **{failed}** • branding appliqué : **{changed}**", color=SUCCESS if failed == 0 else WARNING)
            return await interaction.edit_original_response(embed=embed, view=None)
        await base.run_setup(interaction)

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.danger, row=3)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=discord.Embed(title="Setup annulé", description="Aucune modification n’a été appliquée par cet installateur.", color=WARNING), view=None)


class ProductSuiteV60Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        state_path = str(Path(bot.settings.db_path).with_name("product_suite_v60.json"))
        self.store = ProductStateStore(state_path)
        self._ready: set[int] = set()

    async def cog_load(self) -> None:
        self.bot.add_view(CommunityHomeView(self))
        self.bot.add_view(QuestionThreadView(self))
        self.bot.add_view(StaffViewV60(self))
        self._patch_setup_pipeline()

    def _patch_setup_pipeline(self) -> None:
        if getattr(SetupExperienceV55Cog, "_aidebot_v60_product_suite", False):
            return
        original_publish = SetupExperienceV55Cog._publish_panels

        async def publish(setup_self, guild, channels, roles):
            actions = await original_publish(setup_self, guild, channels, roles)
            cog = setup_self.bot.get_cog("ProductSuiteV60Cog")
            if isinstance(cog, ProductSuiteV60Cog):
                await cog.reconcile_guild(guild)
                actions.append(("Communauté", "updated"))
                actions.append(("Audit staff", "updated"))
            return actions

        SetupExperienceV55Cog._publish_panels = publish
        SetupExperienceV55Cog._aidebot_v60_product_suite = True

    async def apply_theme(self, guild: discord.Guild, key: str, *, apply_now: bool = True) -> None:
        if key not in THEMES:
            key = "clean"
        _label, accent = THEMES[key]
        brand_cog = self.bot.get_cog("BrandRoleStudioV59Cog")
        if brand_cog is None:
            return
        brand = await brand_cog.store.get_brand(guild.id)
        brand["accent"] = accent
        await brand_cog.store.save_brand(guild.id, brand)
        if apply_now:
            await brand_cog.apply_panel_brand(guild)

    async def _configure_community_permissions(self, guild: discord.Guild, channel: discord.TextChannel) -> None:
        try:
            if channel.name == ENTRAIDE_CHANNEL:
                await channel.set_permissions(guild.default_role, view_channel=True, send_messages=False, read_message_history=True, send_messages_in_threads=True, create_public_threads=False, reason="Aide Bot — entraide structurée")
            elif channel.name == SOLUTIONS_CHANNEL:
                await channel.set_permissions(guild.default_role, view_channel=True, send_messages=False, read_message_history=True, reason="Aide Bot — solutions en lecture seule")
            for role_name in ("👑・Direction", "📘・Responsable Formation", "🎓・Formateur", "🤝・Helper", "🧭・Mentor"):
                role = discord.utils.get(guild.roles, name=role_name)
                if role is not None:
                    await channel.set_permissions(role, view_channel=True, send_messages=True, read_message_history=True, send_messages_in_threads=True, manage_threads=role_name in {"👑・Direction", "📘・Responsable Formation", "🤝・Helper"}, reason="Aide Bot — équipe entraide")
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def reconcile_guild(self, guild: discord.Guild) -> None:
        setup = self.bot.get_cog("SetupServerCog")
        if setup is None:
            return
        entraide = discord.utils.get(guild.text_channels, name=ENTRAIDE_CHANNEL)
        solutions = discord.utils.get(guild.text_channels, name=SOLUTIONS_CHANNEL)
        staff = discord.utils.get(guild.text_channels, name=STAFF_CHANNEL)
        for channel in (entraide, solutions):
            if channel is not None:
                await self._configure_community_permissions(guild, channel)
        if entraide is not None:
            await setup._upsert_panel(entraide, community_home_embed(), CommunityHomeView(self))
        if solutions is not None:
            await setup._upsert_panel(solutions, solutions_embed())
        if staff is not None:
            await _upsert_panel(self.bot, staff, embed=staff_embed_v60(), view=StaffViewV60(self))
        prefs = await self.store.preferences(guild.id)
        if prefs.get("theme") in THEMES:
            await self.apply_theme(guild, prefs["theme"], apply_now=True)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            if guild.id in self._ready:
                continue
            self._ready.add(guild.id)
            await self.reconcile_guild(guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if isinstance(channel, discord.TextChannel) and channel.name in {ENTRAIDE_CHANNEL, SOLUTIONS_CHANNEL, STAFF_CHANNEL}:
            await self.reconcile_guild(channel.guild)

    @app_commands.command(name="setup", description="Configurer, réparer ou auditer Aide Bot avec aperçu")
    @app_commands.guild_only()
    async def setup_v60(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if interaction.guild.owner_id != interaction.user.id and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Le setup est réservé au propriétaire ou à un administrateur Discord.", ephemeral=True)
        view = SetupWizardViewV60(self, interaction.user.id)
        await interaction.response.send_message(embed=view.preview_embed(interaction.guild), view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.tree.remove_command("setup")
    await bot.add_cog(ProductSuiteV60Cog(bot))
