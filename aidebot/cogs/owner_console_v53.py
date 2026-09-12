from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands

from aidebot.cogs.assistant_guardian_v52 import (
    AI_CHANNEL,
    STAFF_CHANNEL,
    AssistantPanelView,
    GuardianPanelView,
    assistant_panel_embed,
    audit_guild,
    guardian_panel_embed,
    snapshot_guild,
    snapshot_hash,
)
from aidebot.cogs.product_experience_v51 import (
    HelpCenterViewV51,
    PremiumHubViewV51,
    ShopViewV51,
    WelcomeViewV51,
    help_center_embed_v51,
    premium_hub_embed_v51,
    shop_embed_v51,
    welcome_embed_v51,
)
from aidebot.cogs.recruitment_panel import RecruitmentView, recruitment_embed
from aidebot.cogs.training import TrainingPanel
from aidebot.experience_content import BANNER_URL
from aidebot.owner_config import OwnerBackupStore
from aidebot.public_panels import TicketEntryView, ticket_embed

OWNER_TITLE = "Aide Bot — Console propriétaire"
OWNER_COLOR = 0x2B2D31
SUCCESS = 0x57F287
WARNING = 0xF1C40F
DANGER = 0xED4245

OWNER_ACTIONS = (
    ("diagnostic", "État du bot", "Santé, IA, Guardian, base de données et sauvegardes"),
    ("backup", "Sauvegarder la configuration", "Snapshot des rôles, salons et permissions"),
    ("export", "Exporter la dernière sauvegarde", "Télécharger le dernier snapshot JSON"),
    ("repair", "Réparer les panneaux", "Republier les interfaces sans toucher à la structure"),
    ("bundle", "Créer un rapport diagnostic", "Exporter un rapport technique sans messages ni secrets"),
    ("readiness", "Vérifier la préparation produit", "Contrôle avant vente ou mise en production"),
)


def owner_console_embed() -> discord.Embed:
    e = discord.Embed(
        title=OWNER_TITLE,
        description=(
            "Centre privé du propriétaire. Il regroupe la maintenance, les sauvegardes et les diagnostics sans ajouter de commandes publiques. "
            "Choisis une action dans le menu."
        ),
        color=OWNER_COLOR,
    )
    e.add_field(
        name="Maintenance",
        value="Diagnostic complet • réparation des panneaux • rapport technique partageable.",
        inline=True,
    )
    e.add_field(
        name="Sauvegardes",
        value="Snapshots de configuration conservés sur le stockage persistant, sans contenu de messages.",
        inline=True,
    )
    e.add_field(
        name="Sécurité",
        value="Les actions de cette console sont réservées au propriétaire Discord du serveur.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Console propriétaire")
    return e


class OwnerActionSelect(discord.ui.Select):
    def __init__(self, cog: "OwnerConsoleV53Cog") -> None:
        self.cog = cog
        super().__init__(
            placeholder="Choisis une action propriétaire",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=label, value=value, description=description)
                for value, label, description in OWNER_ACTIONS
            ],
            custom_id="aidebot:v53:owner:action",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await self.cog.require_owner(interaction):
            return
        assert interaction.guild is not None
        action = self.values[0]

        if action == "diagnostic":
            await interaction.response.defer(ephemeral=True, thinking=True)
            embed = await self.cog.diagnostic_embed(interaction.guild)
            return await interaction.followup.send(embed=embed, ephemeral=True)

        if action == "backup":
            await interaction.response.defer(ephemeral=True, thinking=True)
            path = await self.cog.save_backup(interaction.guild)
            return await interaction.followup.send(
                f"Sauvegarde créée : `{path.name}`. Les **5 dernières** sont conservées automatiquement.",
                ephemeral=True,
            )

        if action == "export":
            await interaction.response.defer(ephemeral=True, thinking=True)
            latest = await self.cog.backups.latest_bytes(interaction.guild.id)
            if latest is None:
                return await interaction.followup.send(
                    "Aucune sauvegarde n’existe encore. Lance d’abord **Sauvegarder la configuration**.", ephemeral=True
                )
            filename, data = latest
            return await interaction.followup.send(
                content="Dernière sauvegarde de configuration. Elle ne contient aucun message du serveur.",
                file=discord.File(io.BytesIO(data), filename=filename),
                ephemeral=True,
            )

        if action == "repair":
            await interaction.response.defer(ephemeral=True, thinking=True)
            repaired, missing, failed = await self.cog.repair_panels(interaction.guild)
            color = SUCCESS if not failed else WARNING
            e = discord.Embed(
                title="Réparation des panneaux terminée",
                description=(
                    f"Panneaux remis à jour : **{repaired}**\n"
                    f"Salons absents : **{missing}**\n"
                    f"Échecs : **{failed}**"
                ),
                color=color,
            )
            e.add_field(
                name="Ce que cette action ne fait pas",
                value="Elle ne crée, ne supprime et ne déplace aucun rôle ou salon. Pour la structure complète, `/setup` reste l’outil prévu.",
                inline=False,
            )
            return await interaction.followup.send(embed=e, ephemeral=True)

        if action == "bundle":
            await interaction.response.defer(ephemeral=True, thinking=True)
            filename, data = await self.cog.support_bundle(interaction.guild)
            return await interaction.followup.send(
                content="Rapport technique généré. Aucun historique de messages, token ou clé API n’est inclus.",
                file=discord.File(io.BytesIO(data), filename=filename),
                ephemeral=True,
            )

        if action == "readiness":
            await interaction.response.defer(ephemeral=True, thinking=True)
            embed = await self.cog.readiness_embed(interaction.guild)
            return await interaction.followup.send(embed=embed, ephemeral=True)


class OwnerConsoleView(discord.ui.View):
    def __init__(self, cog: "OwnerConsoleV53Cog") -> None:
        super().__init__(timeout=None)
        self.add_item(OwnerActionSelect(cog))


class OwnerConsoleV53Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        backup_dir = Path(bot.settings.db_path).with_name("owner_backups")
        self.backups = OwnerBackupStore(backup_dir, retention=5)
        self._reconciled_guilds: set[int] = set()

    async def cog_load(self) -> None:
        self.bot.add_view(OwnerConsoleView(self))

    async def require_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True
        if interaction.response.is_done():
            await interaction.followup.send("Cette console est réservée au propriétaire du serveur.", ephemeral=True)
        else:
            await interaction.response.send_message("Cette console est réservée au propriétaire du serveur.", ephemeral=True)
        return False

    def _guardian(self):
        return self.bot.get_cog("AssistantGuardianV52Cog")

    async def _upsert_owner_panel(self, guild: discord.Guild) -> None:
        staff = discord.utils.get(guild.text_channels, name=STAFF_CHANNEL)
        if staff is None:
            return
        setup_cog = self.bot.get_cog("SetupServerCog")
        if setup_cog is None:
            return
        try:
            await setup_cog._upsert_panel(staff, owner_console_embed(), OwnerConsoleView(self))
        except (discord.Forbidden, discord.HTTPException):
            return

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            if guild.id in self._reconciled_guilds:
                continue
            self._reconciled_guilds.add(guild.id)
            await self._upsert_owner_panel(guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if isinstance(channel, discord.TextChannel) and channel.name == STAFF_CHANNEL:
            await self._upsert_owner_panel(channel.guild)

    async def _health(self, guild: discord.Guild) -> tuple[list[str], int, int, dict[str, int]]:
        health = self.bot.get_cog("HealthCog")
        if health is None or not hasattr(health, "_collect"):
            return ["Module de santé indisponible."], 1, 0, {}
        return await health._collect(guild)

    async def diagnostic_embed(self, guild: discord.Guild) -> discord.Embed:
        lines, blockers, warnings, _integrity = await self._health(guild)
        guardian = self._guardian()
        audit = audit_guild(guild)
        baseline = await guardian.store.baseline(guild.id) if guardian is not None else None
        latest = await self.backups.latest(guild.id)
        ai_ok = bool(guardian and guardian.ai.configured)

        color = SUCCESS if blockers == 0 and audit.score >= 80 else WARNING if blockers <= 1 else DANGER
        e = discord.Embed(
            title="Aide Bot — État technique",
            description="Vue propriétaire de la santé réelle du bot et du serveur.",
            color=color,
        )
        e.add_field(
            name="Système",
            value=(
                f"Bloquants : **{blockers}**\n"
                f"Avertissements : **{warnings}**\n"
                f"Latence : **{round(self.bot.latency * 1000)} ms**\n"
                f"Modules chargés : **{len(self.bot.cogs)}**"
            ),
            inline=True,
        )
        e.add_field(
            name="Modules avancés",
            value=(
                f"Assistant IA : **{'prêt' if ai_ok else 'clé manquante'}**\n"
                f"Guardian : **{audit.score}/100**\n"
                f"État sûr : **{'enregistré' if baseline else 'absent'}**\n"
                f"Backup propriétaire : **{'présent' if latest else 'absent'}**"
            ),
            inline=True,
        )
        e.add_field(name="Contrôles", value="\n".join(lines[:8])[:1024], inline=False)
        e.set_footer(text="Cette vue ne contient aucune conversation membre.")
        return e

    async def save_backup(self, guild: discord.Guild) -> Path:
        snapshot = snapshot_guild(guild)
        audit = audit_guild(guild)
        return await self.backups.save(
            guild.id,
            guild.name,
            snapshot,
            digest=snapshot_hash(snapshot),
            audit_score=audit.score,
        )

    async def support_bundle(self, guild: discord.Guild) -> tuple[str, bytes]:
        lines, blockers, warnings, integrity = await self._health(guild)
        guardian = self._guardian()
        audit = audit_guild(guild)
        baseline = await guardian.store.baseline(guild.id) if guardian is not None else None
        latest = await self.backups.latest(guild.id)
        snapshot = snapshot_guild(guild)
        payload: dict[str, Any] = {
            "schema": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "privacy": {
                "contains_messages": False,
                "contains_tokens_or_api_keys": False,
            },
            "guild": {
                "id": guild.id,
                "name": guild.name,
                "roles": len(guild.roles),
                "channels": len(guild.channels),
                "members": guild.member_count,
            },
            "bot": {
                "user_id": self.bot.user.id if self.bot.user else None,
                "latency_ms": round(self.bot.latency * 1000),
                "loaded_cogs": sorted(self.bot.cogs.keys()),
                "public_slash_commands": ["setup", "buy"],
            },
            "health": {
                "blockers": blockers,
                "warnings": warnings,
                "checks": lines,
                "integrity": integrity,
            },
            "assistant_ai": {
                "configured": bool(guardian and guardian.ai.configured),
                "model": guardian.ai.model if guardian is not None else None,
            },
            "guardian": {
                "score": audit.score,
                "risks": [
                    {"severity": risk.severity, "title": risk.title, "detail": risk.detail}
                    for risk in audit.risks
                ],
                "baseline_saved": baseline is not None,
                "snapshot_hash": snapshot_hash(snapshot),
            },
            "owner_backup": {
                "latest": latest.name if latest else None,
            },
        }
        data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"aidebot-diagnostic-{guild.id}-{stamp}.json", data

    async def readiness_embed(self, guild: discord.Guild) -> discord.Embed:
        lines, blockers, warnings, _integrity = await self._health(guild)
        guardian = self._guardian()
        audit = audit_guild(guild)
        baseline = await guardian.store.baseline(guild.id) if guardian is not None else None
        latest = await self.backups.latest(guild.id)
        ai_ok = bool(guardian and guardian.ai.configured)

        checks = [
            (blockers == 0, "Santé système sans blocage"),
            (audit.score >= 80, f"Guardian au moins 80/100 — actuel : {audit.score}/100"),
            (baseline is not None, "État sûr Guardian enregistré"),
            (latest is not None, "Sauvegarde propriétaire disponible"),
            (ai_ok, "Assistant IA réellement configuré"),
            (discord.utils.get(guild.text_channels, name=AI_CHANNEL) is not None, "Salon Assistant IA présent"),
            (discord.utils.get(guild.text_channels, name=STAFF_CHANNEL) is not None, "Espace staff présent"),
        ]
        passed = sum(1 for ok, _ in checks if ok)
        ready = passed == len(checks)
        e = discord.Embed(
            title="Préparation produit — " + ("COMPLÈTE" if ready else "À TERMINER"),
            description=(
                "Ce contrôle mesure si Aide Bot est proprement exploitable/transférable. "
                "Il ne fixe pas à lui seul un prix de vente."
            ),
            color=SUCCESS if ready else WARNING,
        )
        e.add_field(
            name=f"Contrôles {passed}/{len(checks)}",
            value="\n".join(f"{'✅' if ok else '⚠️'} {label}" for ok, label in checks),
            inline=False,
        )
        if blockers:
            e.add_field(name="Blocages système", value="\n".join(lines[:5])[:1024], inline=False)
        e.set_footer(text=f"Avertissements santé : {warnings} • Aucun message membre n’est analysé")
        return e

    async def repair_panels(self, guild: discord.Guild) -> tuple[int, int, int]:
        setup_cog = self.bot.get_cog("SetupServerCog")
        if setup_cog is None:
            return 0, 0, 1

        repaired = 0
        missing = 0
        failed = 0

        async def apply(channel_name: str, embed: discord.Embed, view: discord.ui.View) -> None:
            nonlocal repaired, missing, failed
            channel = discord.utils.get(guild.text_channels, name=channel_name)
            if channel is None:
                missing += 1
                return
            try:
                result = await setup_cog._upsert_panel(channel, embed, view)
                if result == "failed":
                    failed += 1
                else:
                    repaired += 1
            except (discord.Forbidden, discord.HTTPException):
                failed += 1

        await apply("👋・bienvenue", welcome_embed_v51(), WelcomeViewV51(self.bot))
        await apply("🎓・centre-aide", help_center_embed_v51(), HelpCenterViewV51(self.bot))

        training = self.bot.get_cog("TrainingCog")
        if training is not None:
            await apply("🎓・formations", setup_cog._training_embed(), TrainingPanel(training))
        else:
            failed += 1

        await apply(
            "🛒・shop",
            shop_embed_v51(self.bot.settings.vip_price_robux),
            ShopViewV51(self.bot),
        )
        await apply("🎫・ouvrir-ticket", ticket_embed(), TicketEntryView(self.bot))
        await apply("🧑‍🏫・recrutement", recruitment_embed(), RecruitmentView(self.bot))
        await apply("💎・espace-premium", premium_hub_embed_v51(), PremiumHubViewV51(self.bot))

        guardian = self._guardian()
        if guardian is not None:
            await apply(AI_CHANNEL, assistant_panel_embed(guardian.ai.configured), AssistantPanelView(guardian))
            await apply(STAFF_CHANNEL, guardian_panel_embed(), GuardianPanelView(guardian))
        else:
            failed += 1

        await apply(STAFF_CHANNEL, owner_console_embed(), OwnerConsoleView(self))
        return repaired, missing, failed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OwnerConsoleV53Cog(bot))
