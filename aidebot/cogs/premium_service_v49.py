from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone

import discord
from discord.ext import commands

import aidebot.public_panels as public_panels
import aidebot.cogs.premium_service_v48 as v48
from aidebot.catalog import FORMATIONS
from aidebot.cogs.experience_v43 import member_space_embed
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed

PREMIUM_COLOR = 0xEB459E
SUCCESS = 0x57F287
WARNING = 0xF1C40F
DANGER = 0xED4245
ELITE_PRICE_ROBUX = 10_000
SHOP_CHANNEL = "🛒・shop"
CONFIRM_WORD = "CONSTRUIRE"

# Compatibilité : les anciennes vues V48 restent enregistrées afin que les
# panneaux déjà publiés continuent de répondre jusqu'au prochain /setup.
_V48_HUB_VIEW = v48.PremiumHubV48View
_V48_SHOP_VIEW = v48.ShopV48View
_V48_SERVER_VIEW = v48.ServerBuildV48TicketView
_BASE_SHOP_VIEW = public_panels.ShopView


V49_SERVER_TEMPLATES = {
    "marketplace": {
        "label": "Marketplace / échange",
        "description": "Catalogue, annonces, réputation, règles anti-arnaque, support et staff.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ MARKETPLACE ━━", (("text", "🛒・catalogue"), ("text", "📦・offres"), ("text", "🔎・recherches"), ("text", "⭐・réputation"))),
            ("━━ SÉCURITÉ ━━", (("text", "🛡️・sécurité"), ("text", "⚠️・signalements"), ("text", "📚・guide-échange"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "💡・suggestions"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"), ("voice", "🔒・Staff"))),
        ),
    },
    "event": {
        "label": "Événement / tournoi",
        "description": "Inscriptions, planning, équipes, résultats, annonces, vocaux et support.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ ÉVÉNEMENT ━━", (("text", "📝・inscriptions"), ("text", "📅・planning"), ("text", "🏆・résultats"), ("text", "📌・informations"))),
            ("━━ PARTICIPANTS ━━", (("text", "💬・général"), ("text", "🎬・clips"), ("voice", "🔊・Lobby 1"), ("voice", "🔊・Lobby 2"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "❓・faq"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"), ("voice", "🔒・Organisation"))),
        ),
    },
    "roleplay": {
        "label": "Roleplay / univers",
        "description": "Lore, règles RP, personnages, scènes, communauté, vocaux et modération.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ UNIVERS RP ━━", (("text", "📖・lore"), ("text", "🪪・personnages"), ("text", "🎭・scènes-rp"), ("text", "📌・règles-rp"))),
            ("━━ COMMUNAUTÉ ━━", (("text", "💬・général"), ("text", "📸・médias"), ("voice", "🔊・RP 1"), ("voice", "🔊・RP 2"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "⚠️・signalements"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"), ("voice", "🔒・Staff RP"))),
        ),
    },
    "agency": {
        "label": "Agence / business",
        "description": "Services, portfolio, commandes, clients, support et organisation interne.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ SERVICES ━━", (("text", "💼・services"), ("text", "🖼️・portfolio"), ("text", "📦・commandes"), ("text", "⭐・avis"))),
            ("━━ CLIENTS ━━", (("text", "❓・faq"), ("text", "📚・process"), ("text", "📌・statut-service"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "💡・suggestions"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"), ("voice", "🔒・Réunion"))),
        ),
    },
}


V49_PREMIUM_SERVICES = {
    "project-360": {
        "label": "Transformation 360°",
        "description": "Audit complet puis refonte coordonnée serveur, UX, sécurité, support et organisation.",
        "questions": (
            ("Projet", "Type de serveur, taille, public et objectif", 320),
            ("État actuel", "Ce qui fonctionne et ce qui ne fonctionne pas", 650),
            ("Priorités", "Les 3 résultats les plus importants à obtenir", 500),
            ("Contraintes", "Ce qu'il faut absolument conserver / éviter", 500),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "migration": {
        "label": "Migrer / restructurer mon serveur",
        "description": "Plan de migration d'un serveur existant sans suppression automatique du contenu actuel.",
        "questions": (
            ("Serveur actuel", "Taille, ancienneté, public", 250),
            ("Structure actuelle", "Catégories, rôles et systèmes importants", 600),
            ("Ce qui doit changer", "Organisation, permissions, tickets, onboarding...", 600),
            ("Éléments à préserver", "Salons/rôles/process à ne surtout pas perdre", 450),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "branding-ux": {
        "label": "Branding & UX Discord",
        "description": "Parcours membre, cohérence visuelle, noms de salons, information et lisibilité.",
        "questions": (
            ("Identité", "Nom, thème, public et ambiance recherchée", 300),
            ("Problèmes UX", "Ce qui paraît confus, vide, chargé ou incohérent", 600),
            ("Références", "Styles/serveurs que tu apprécies, sans copier", 450),
            ("Résultat attendu", "Ce qu'un nouveau membre doit ressentir/comprendre", 500),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "automation": {
        "label": "Automatisations Discord",
        "description": "Workflows pour onboarding, rôles, tickets, logs, notifications et opérations répétitives.",
        "questions": (
            ("Tâches répétitives", "Ce que ton staff fait encore à la main", 550),
            ("Bots actuels", "Bots et fonctions déjà en place", 350),
            ("Automatisations visées", "Onboarding, tickets, logs, rôles, notifications...", 600),
            ("Contraintes", "Permissions, outils, sécurité ou limites importantes", 450),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "data-backup": {
        "label": "Données, sauvegarde & fiabilité",
        "description": "Persistance, SQLite/PostgreSQL, sauvegardes, restauration, logs et reprise après incident.",
        "questions": (
            ("Stack", "Bot, hébergement, base de données et stockage", 320),
            ("Données critiques", "Ce qui ne doit pas être perdu", 550),
            ("Problèmes connus", "Perte de données, locks, redémarrages, migrations...", 600),
            ("Objectif fiabilité", "Sauvegarde, reprise, monitoring, migration...", 500),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
}

v48.SERVER_TEMPLATES.update(V49_SERVER_TEMPLATES)
v48.PREMIUM_SERVICE_FORMS.update(V49_PREMIUM_SERVICES)
v48.SERVICE_DELIVERABLES.update(
    {
        "project-360": ("Audit 360°", "Plan priorisé", "Refonte coordonnée", "Tests d'acceptation", "Dossier final"),
        "migration": ("Inventaire avant changement", "Plan de migration", "Ordre d'exécution", "Contrôle après migration"),
        "branding-ux": ("Diagnostic UX", "Architecture de navigation", "Règles de nommage", "Parcours nouveau membre testé"),
        "automation": ("Carte des tâches manuelles", "Workflows proposés", "Permissions nécessaires", "Tests des automatisations"),
        "data-backup": ("Cartographie des données", "Stratégie de sauvegarde", "Plan de restauration", "Test de reprise"),
    }
)


@dataclass(frozen=True)
class Readiness360:
    total: int
    security: int
    structure: int
    onboarding: int
    support: int
    operations: int
    recommendations: tuple[str, ...]


def _channel_names(guild: discord.Guild) -> set[str]:
    return {channel.name.casefold() for channel in guild.channels}


def _role_names(guild: discord.Guild) -> set[str]:
    return {role.name.casefold() for role in guild.roles}


def _has_any(names: set[str], *needles: str) -> bool:
    return any(any(needle in name for needle in needles) for name in names)


def analyze_360(guild: discord.Guild) -> Readiness360:
    security = v48.analyze_server(guild).score
    channels = _channel_names(guild)
    roles = _role_names(guild)
    category_count = len(guild.categories)
    text_count = len(guild.text_channels)

    structure = 0
    structure += 20 if category_count >= 4 else min(20, category_count * 5)
    structure += 20 if text_count >= 10 else min(20, text_count * 2)
    structure += 20 if _has_any(channels, "règlement", "reglement", "rules") else 0
    structure += 15 if _has_any(channels, "annonce", "news") else 0
    structure += 15 if _has_any(channels, "général", "general", "discussion") else 0
    structure += 10 if _has_any(channels, "staff") else 0

    onboarding = 0
    onboarding += 25 if _has_any(channels, "bienvenue", "welcome") else 0
    onboarding += 25 if _has_any(channels, "règlement", "reglement", "rules") else 0
    onboarding += 20 if _has_any(channels, "annonce", "news") else 0
    onboarding += 15 if _has_any(roles, "membre", "member") else 0
    onboarding += 15 if _has_any(roles, "notification") else 0

    support = 0
    support += 35 if _has_any(channels, "support", "ticket") else 0
    support += 20 if _has_any(channels, "faq", "guide", "aide") else 0
    support += 10 if _has_any(channels, "avis", "review") else 0
    support += 15 if _has_any(channels, "logs", "journal") else 0
    support += 20 if _has_any(roles, "support", "helper") else 0

    operations = 0
    operations += 25 if _has_any(channels, "staff") else 0
    operations += 20 if _has_any(channels, "logs", "journal") else 0
    operations += 20 if _has_any(roles, "modérateur", "moderator", "modo") else 0
    operations += 15 if _has_any(roles, "support", "helper") else 0
    admin_roles = sum(1 for role in guild.roles if not role.is_default() and role.permissions.administrator)
    operations += 20 if admin_roles <= 4 else 5

    structure = min(100, structure)
    onboarding = min(100, onboarding)
    support = min(100, support)
    operations = min(100, operations)
    total = round(security * 0.35 + structure * 0.20 + onboarding * 0.15 + support * 0.15 + operations * 0.15)

    recommendations: list[str] = []
    if security < 75:
        recommendations.append("Réduire les permissions sensibles et corriger les risques de sécurité en priorité.")
    if structure < 70:
        recommendations.append("Simplifier la structure et rendre les salons essentiels immédiatement identifiables.")
    if onboarding < 70:
        recommendations.append("Créer un parcours d'arrivée clair : bienvenue → règles → rôles → premiers salons.")
    if support < 70:
        recommendations.append("Mettre en place un support visible avec ticket, FAQ/guide et suivi des demandes.")
    if operations < 70:
        recommendations.append("Clarifier le staff, les logs et les rôles opérationnels avant de grandir.")
    if not recommendations:
        recommendations.append("Base solide : concentrer la prochaine amélioration sur l'expérience membre et les tests réels.")
    return Readiness360(total, security, structure, onboarding, support, operations, tuple(recommendations))


def _score_label(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Solide"
    if score >= 55:
        return "À améliorer"
    return "Prioritaire"


def audit_360_embed(guild: discord.Guild, report: Readiness360) -> discord.Embed:
    color = SUCCESS if report.total >= 75 else WARNING if report.total >= 55 else DANGER
    e = discord.Embed(
        title=f"Audit 360° — {guild.name}",
        description=(
            f"**Score global : {report.total}/100 — {_score_label(report.total)}**\n"
            "Le score combine sécurité, structure, onboarding, support et opérations. Il sert à prioriser les améliorations, pas à remplacer un audit humain."
        ),
        color=color,
    )
    e.add_field(name="Sécurité", value=f"**{report.security}/100**", inline=True)
    e.add_field(name="Structure", value=f"**{report.structure}/100**", inline=True)
    e.add_field(name="Onboarding", value=f"**{report.onboarding}/100**", inline=True)
    e.add_field(name="Support", value=f"**{report.support}/100**", inline=True)
    e.add_field(name="Opérations", value=f"**{report.operations}/100**", inline=True)
    e.add_field(name="Priorités", value="\n".join(f"• {item}" for item in report.recommendations)[:1024], inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V49 • Audit 360° • décisions basées sur des vérifications réelles")
    return e


def _snapshot_dict(guild: discord.Guild) -> dict:
    def overwrites(channel: discord.abc.GuildChannel) -> list[dict]:
        values = []
        for target, overwrite in getattr(channel, "overwrites", {}).items():
            allow, deny = overwrite.pair()
            values.append(
                {
                    "target_id": target.id,
                    "target_name": getattr(target, "name", str(target.id)),
                    "target_type": type(target).__name__,
                    "allow": allow.value,
                    "deny": deny.value,
                }
            )
        return values

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guild": {"id": guild.id, "name": guild.name, "owner_id": guild.owner_id},
        "roles": [
            {
                "id": role.id,
                "name": role.name,
                "position": role.position,
                "permissions": role.permissions.value,
                "managed": role.managed,
            }
            for role in guild.roles
        ],
        "categories": [
            {"id": category.id, "name": category.name, "position": category.position, "overwrites": overwrites(category)}
            for category in guild.categories
        ],
        "channels": [
            {
                "id": channel.id,
                "name": channel.name,
                "type": str(channel.type),
                "position": channel.position,
                "category_id": getattr(channel, "category_id", None),
                "overwrites": overwrites(channel),
            }
            for channel in guild.channels
            if not isinstance(channel, discord.CategoryChannel)
        ],
    }


def snapshot_file(guild: discord.Guild, *, suffix: str = "before") -> discord.File:
    payload = json.dumps(_snapshot_dict(guild), ensure_ascii=False, indent=2).encode("utf-8")
    return discord.File(io.BytesIO(payload), filename=f"aidebot-{suffix}-{guild.id}.json")


def readiness_json_file(guild: discord.Guild, report: Readiness360) -> discord.File:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guild_id": guild.id,
        "guild_name": guild.name,
        "score_global": report.total,
        "security": report.security,
        "structure": report.structure,
        "onboarding": report.onboarding,
        "support": report.support,
        "operations": report.operations,
        "recommendations": list(report.recommendations),
    }
    return discord.File(
        io.BytesIO(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")),
        filename=f"audit-360-{guild.id}.json",
    )


def premium_v49_hub_embed(price: int) -> discord.Embed:
    price = max(price, ELITE_PRICE_ROBUX)
    e = discord.Embed(
        title="Aide Bot — Premium Elite",
        description=(
            f"**Premium Elite — {price:,} Robux**\n".replace(",", " ")
            + "À ce niveau, tu n'achètes pas un badge. Tu débloques un **centre de services complet** : audit 360°, transformation serveur, automatisation, "
            "sécurité, bot/production, données, accompagnement et dossier de livraison."
        ),
        color=PREMIUM_COLOR,
    )
    e.add_field(name="Transformation 360°", value="Diagnostic global → priorités → mise en œuvre → tests → dossier final.", inline=True)
    e.add_field(name="12 modèles de serveur", value="Communauté, Gaming, Shop, Créateur, Support, Académie, Esport, Projet, Marketplace, Événement, RP et Agence.", inline=True)
    e.add_field(name="Audit 360°", value="Scores Sécurité / Structure / Onboarding / Support / Opérations + recommandations prioritaires.", inline=True)
    e.add_field(name="Protection avant modification", value="Pré-vérification, simulation du plan, snapshot JSON et confirmation explicite avant construction.", inline=True)
    e.add_field(name="15+ services spécialisés", value="Migration, branding/UX, automatisations, données/sauvegarde, staff, Railway, tickets, sécurité et plus.", inline=True)
    e.add_field(name="Livraison vérifiable", value="Rapport avant/après, éléments créés/réutilisés, audit final et checklist d'acceptation.", inline=True)
    e.add_field(
        name="Ce qui reste manuel",
        value="Le paiement est validé par la Direction et Discord exige toujours l'autorisation OAuth2 du propriétaire/admin avant que le bot rejoigne un serveur.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V49 • Premium Elite = service + automatisation + audit + livrables")
    return e


def premium_shop_embed(price: int) -> discord.Embed:
    price = max(price, ELITE_PRICE_ROBUX)
    e = discord.Embed(
        title="Aide Bot — Boutique Premium Elite",
        description=(
            f"**Pack Premium Elite — {price:,} Robux**\n\n".replace(",", " ")
            + "Le prix correspond à un **pack de réalisation et d'accompagnement**, pas à l'accès à quelques vidéos. Le client peut commander une construction serveur, "
            "demander une transformation 360°, faire auditer son projet ou utiliser les services techniques spécialisés."
        ),
        color=PREMIUM_COLOR,
    )
    e.add_field(name="Serveur sur mesure", value="12 modèles, pré-vérification, snapshot avant changement, construction automatisée et rapport après livraison.", inline=False)
    e.add_field(name="Projet 360°", value="Audit, roadmap priorisée, UX, sécurité, support, staff et vérification finale dans un même dossier.", inline=True)
    e.add_field(name="Bot & production", value="Architecture, Railway, DB, sauvegardes, logs, tests, CI/CD et fiabilité.", inline=True)
    e.add_field(name="Sécurité & opérations", value="Permissions, anti-abus, staff, tickets, onboarding, automatisations et préparation au lancement.", inline=True)
    e.add_field(name="Ressources Elite", value="Vidéos VIP, bibliothèque avancée et parcours d'apprentissage organisés par objectif.", inline=True)
    e.add_field(
        name="Parcours d'achat",
        value="**1.** Achat → **2.** ticket privé → **3.** validation Direction → **4.** rôle 💎・VIP → **5.** centre Elite débloqué → **6.** mission suivie jusqu'au résultat vérifié.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V49 • 10 000 Robux = réalisation, audit, livrables et suivi")
    return e


def academy_elite_embed() -> discord.Embed:
    e = discord.Embed(
        title="Premium Elite — Academy",
        description="Les vidéos deviennent des **parcours**, pas une liste de liens. Choisis un objectif puis applique les ressources à ton propre projet.",
        color=PREMIUM_COLOR,
    )
    e.add_field(name="Architecture Bot", value="discord.py avancé → vues persistantes → erreurs → DB → tests → déploiement.", inline=True)
    e.add_field(name="Production", value="Railway → volumes → PostgreSQL → logs → CI/CD → reprise après incident.", inline=True)
    e.add_field(name="Serveur Pro", value="Architecture → permissions → onboarding → tickets → staff → audit final.", inline=True)
    e.add_field(name="Sécurité", value="Rôles sensibles → webhooks → anti-abus → logs → plan d'urgence → contrôle.", inline=True)
    e.add_field(name="Support & UX", value="Diagnostic → formulaires → claim → progression → fermeture → expérience membre.", inline=True)
    e.add_field(name="Fiabilité", value="Tests → concurrence → sauvegardes → migrations → monitoring → validation production.", inline=True)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V49 • Apprendre → appliquer → vérifier")
    return e


def server_templates_v49_embed() -> discord.Embed:
    e = discord.Embed(
        title="Premium Elite — serveur sur mesure",
        description=(
            f"**{len(v48.SERVER_TEMPLATES)} modèles** sont disponibles. Le modèle sert de base : ton objectif et tes options restent enregistrés dans le ticket.\n\n"
            "Avant la construction, Aide Bot peut auditer le serveur, montrer ce qui sera créé/réutilisé et exporter un snapshot JSON. **Rien n'est supprimé automatiquement.**"
        ),
        color=PREMIUM_COLOR,
    )
    for data in v48.SERVER_TEMPLATES.values():
        e.add_field(name=data["label"], value=data["description"], inline=True)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V49 • modèle → ticket → paiement → OAuth2 → audit → snapshot → confirmation → livraison")
    return e


def _internal_training_meta(title: str, description: str) -> dict:
    return {
        "title": title,
        "description": description,
        "steps": ["Diagnostic", "Plan", "Mise en œuvre", "Vérification", "Dossier final"],
        "vip": True,
        "kind": "vip",
        "difficulty": "Sur mesure",
        "duration": "Selon projet",
    }


async def _create_internal_request(training, interaction: discord.Interaction, key: str, meta: dict, **fields) -> None:
    previous = FORMATIONS.get(key)
    FORMATIONS[key] = meta
    try:
        await training.create_request_channel(interaction, key, **fields)
    finally:
        if previous is None:
            FORMATIONS.pop(key, None)
        else:
            FORMATIONS[key] = previous


async def _require_vip(interaction: discord.Interaction) -> bool:
    if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
        return True
    shop = discord.utils.get(interaction.guild.text_channels, name=SHOP_CHANNEL) if interaction.guild else None
    await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
    return False


class PremiumServiceModalV49(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, service_key: str) -> None:
        data = v48.PREMIUM_SERVICE_FORMS[service_key]
        super().__init__(title=data["label"][:45])
        self.bot = bot
        self.service_key = service_key
        self.inputs: list[discord.ui.TextInput] = []
        for index, (label, placeholder, max_length) in enumerate(data["questions"]):
            item = discord.ui.TextInput(
                label=label[:45],
                placeholder=placeholder[:100],
                style=discord.TextStyle.paragraph if index in {1, 2, 3} else discord.TextStyle.short,
                max_length=max_length,
            )
            self.inputs.append(item)
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name=SHOP_CHANNEL)
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de tickets indisponible.", ephemeral=True)
        data = v48.PREMIUM_SERVICE_FORMS[self.service_key]
        objective = "\n\n".join(
            f"{question[0]} : {str(item).strip()}" for question, item in zip(data["questions"], self.inputs)
        )[:3000]
        key = f"premium_service_{self.service_key.replace('-', '_')}"
        await _create_internal_request(
            training,
            interaction,
            key,
            _internal_training_meta(f"Premium Elite — {data['label']}", data["description"]),
            level="Service Premium Elite",
            objective=objective,
            availability=str(self.inputs[-1]).strip(),
            budget="Inclus dans Premium Elite",
            status="open",
            payment_status="not_required",
            requires_invite=False,
        )


class ServerBuildRequestModalV49(discord.ui.Modal):
    target_server = discord.ui.TextInput(label="ID du serveur à configurer", placeholder="Mode développeur → Copier l'identifiant du serveur", max_length=22)
    requested_name = discord.ui.TextInput(label="Nom souhaité du serveur", placeholder="Optionnel : conserver le nom actuel", required=False, max_length=100)
    purpose = discord.ui.TextInput(label="Objectif du serveur", placeholder="Public, activité, résultat attendu...", style=discord.TextStyle.paragraph, max_length=500)
    extras = discord.ui.TextInput(label="Options / demandes spéciales", placeholder="Rôles, salons, style, tickets, vocaux...", style=discord.TextStyle.paragraph, required=False, max_length=600)
    availability = discord.ui.TextInput(label="Tes disponibilités", placeholder="Ex: samedi 14h-20h", max_length=150)

    def __init__(self, bot: commands.Bot, template_key: str) -> None:
        super().__init__(title=f"Elite — {v48.SERVER_TEMPLATES[template_key]['label']}"[:45])
        self.bot = bot
        self.template_key = template_key

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        raw = str(self.target_server).strip()
        if not raw.isdigit() or not 15 <= len(raw) <= 22:
            return await interaction.response.send_message("ID serveur invalide. Active le mode développeur puis copie l'identifiant du serveur.", ephemeral=True)
        target_id = int(raw)
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de tickets indisponible.", ephemeral=True)
        existing = await self.bot.db.active_request_for_training(interaction.guild.id, interaction.user.id, v48.SERVER_BUILD_KEY)
        if existing:
            channel = interaction.guild.get_channel(existing["channel_id"]) if existing["channel_id"] else None
            destination = channel.mention if isinstance(channel, discord.TextChannel) else f"demande #{existing['id']}"
            return await interaction.response.send_message(f"Tu as déjà une construction de serveur active : {destination}.", ephemeral=True)

        vip = has_premium(interaction.user)
        objective = (
            f"Serveur cible ID : {target_id}\n"
            f"Modèle : {self.template_key}\n"
            f"Nom souhaité : {str(self.requested_name).strip() or 'Conserver le nom actuel'}\n"
            f"Objectif : {str(self.purpose).strip()}\n"
            f"Options : {str(self.extras).strip() or 'Aucune option spéciale'}"
        )
        await _create_internal_request(
            training,
            interaction,
            v48.SERVER_BUILD_KEY,
            {
                "title": "Premium Elite — création de serveur",
                "description": "Construction sécurisée d'un serveur avec audit, snapshot, confirmation et dossier final.",
                "steps": ["Validation", "OAuth2", "Audit 360°", "Snapshot", "Construction", "Vérification", "Dossier final"],
                "vip": True,
                "kind": "vip",
                "difficulty": "Automatisé + accompagné",
                "duration": "Selon modèle",
            },
            level=f"Modèle {v48.SERVER_TEMPLATES[self.template_key]['label']}",
            objective=objective,
            availability=str(self.availability).strip(),
            budget="Inclus dans Premium Elite" if vip else f"Premium Elite — {max(self.bot.settings.vip_price_robux, ELITE_PRICE_ROBUX)} Robux",
            status="open" if vip else "payment_pending",
            payment_status="not_required" if vip else "pending",
            requires_invite=False,
        )


class ServerTemplateSelectV49(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__(
            placeholder="Choisis le modèle de départ",
            min_values=1,
            max_values=1,
            custom_id="aidebot:v49:server:template",
            options=[
                discord.SelectOption(label=data["label"][:100], value=key, description=data["description"][:100])
                for key, data in v48.SERVER_TEMPLATES.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ServerBuildRequestModalV49(self.bot, self.values[0]))


class ServerTemplateChoiceViewV49(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=900)
        self.add_item(ServerTemplateSelectV49(bot))


class PremiumServiceSelectV49(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(label="Serveur sur mesure", value="build-server", description="12 modèles + audit + snapshot + construction"),
            *[
                discord.SelectOption(label=data["label"][:100], value=key, description=data["description"][:100])
                for key, data in v48.PREMIUM_SERVICE_FORMS.items()
            ],
        ]
        super().__init__(
            placeholder="Choisis ton service Premium Elite",
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id="aidebot:v49:premium:service",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await _require_vip(interaction):
            return
        key = self.values[0]
        if key == "build-server":
            return await interaction.response.send_message(embed=server_templates_v49_embed(), view=ServerTemplateChoiceViewV49(self.bot), ephemeral=True)
        await interaction.response.send_modal(PremiumServiceModalV49(self.bot, key))


class Audit360Modal(discord.ui.Modal, title="Audit 360° Premium Elite"):
    server_id = discord.ui.TextInput(label="ID du serveur", placeholder="Copier l'identifiant du serveur", max_length=22)

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await _require_vip(interaction) or not isinstance(interaction.user, discord.Member):
            return
        raw = str(self.server_id).strip()
        if not raw.isdigit() or not 15 <= len(raw) <= 22:
            return await interaction.response.send_message("ID serveur invalide.", ephemeral=True)
        target_id = int(raw)
        target = self.bot.get_guild(target_id)
        if target is None:
            url = v48._oauth_url(self.bot, target_id)
            if url is None:
                return await interaction.response.send_message("Aide Bot n'est pas encore présent sur ce serveur.", ephemeral=True)
            return await interaction.response.send_message("Autorise d'abord Aide Bot pour lancer l'audit 360°.", view=v48.OAuthInviteView(url), ephemeral=True)
        member = await v48._client_target_member(target, interaction.user.id)
        if member is None or not (target.owner_id == member.id or member.guild_permissions.administrator or member.guild_permissions.manage_guild):
            return await interaction.response.send_message("Tu dois être propriétaire ou avoir Gérer le serveur sur le serveur audité.", ephemeral=True)
        report = analyze_360(target)
        await interaction.response.send_message(embed=audit_360_embed(target, report), file=readiness_json_file(target, report), ephemeral=True)


class PremiumHubV49View(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(PremiumServiceSelectV49(bot))

    @discord.ui.button(label="Serveur sur mesure", style=discord.ButtonStyle.success, custom_id="aidebot:v49:premium:server", row=1)
    async def server(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_message(embed=server_templates_v49_embed(), view=ServerTemplateChoiceViewV49(self.bot), ephemeral=True)

    @discord.ui.button(label="Audit 360°", style=discord.ButtonStyle.primary, custom_id="aidebot:v49:premium:audit", row=1)
    async def audit(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_modal(Audit360Modal(self.bot))

    @discord.ui.button(label="Academy Elite", style=discord.ButtonStyle.primary, custom_id="aidebot:v49:premium:academy", row=1)
    async def academy(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_message(embed=academy_elite_embed(), view=v48.DirectPremiumVideoView(), ephemeral=True)

    @discord.ui.button(label="Projet 360°", style=discord.ButtonStyle.secondary, custom_id="aidebot:v49:premium:project", row=2)
    async def project(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_modal(PremiumServiceModalV49(self.bot, "project-360"))

    @discord.ui.button(label="Mon espace", style=discord.ButtonStyle.secondary, custom_id="aidebot:v49:premium:space", row=2)
    async def space(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction) or not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=await member_space_embed(self.bot, interaction.user), ephemeral=True)

    @discord.ui.button(label="Statut VIP", style=discord.ButtonStyle.secondary, custom_id="aidebot:v49:premium:status", row=2)
    async def status(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction) or not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=premium_member_embed(interaction.user), ephemeral=True)


class ShopV49View(_BASE_SHOP_VIEW):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.bot = bot

    @discord.ui.button(label="Commander un serveur", style=discord.ButtonStyle.primary, custom_id="aidebot:v49:shop:server", row=1)
    async def server(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=server_templates_v49_embed(), view=ServerTemplateChoiceViewV49(self.bot), ephemeral=True)

    @discord.ui.button(label="Voir le pack 10K", style=discord.ButtonStyle.secondary, custom_id="aidebot:v49:shop:pack", row=1)
    async def pack(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            return await interaction.response.send_message(embed=premium_v49_hub_embed(self.bot.settings.vip_price_robux), view=PremiumHubV49View(self.bot), ephemeral=True)
        await interaction.response.send_message(embed=premium_v49_hub_embed(self.bot.settings.vip_price_robux), ephemeral=True)

    @discord.ui.button(label="Audit 360°", style=discord.ButtonStyle.secondary, custom_id="aidebot:v49:shop:audit", row=1)
    async def audit(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_modal(Audit360Modal(self.bot))


async def _request_for_ticket(bot: commands.Bot, interaction: discord.Interaction):
    if interaction.channel is None:
        return None
    return await bot.db.request_by_channel(interaction.channel.id)


def mission_elite_embed(req) -> discord.Embed | None:
    key = str(req["training_key"])
    prefix = "premium_service_"
    if not key.startswith(prefix):
        return None
    service_key = key[len(prefix):].replace("_", "-")
    service = v48.PREMIUM_SERVICE_FORMS.get(service_key)
    if service is None:
        return None
    deliverables = v48.SERVICE_DELIVERABLES.get(service_key, ("Diagnostic", "Plan d'action", "Vérification finale"))
    e = discord.Embed(
        title=f"Dossier Premium Elite — {service['label']}",
        description="Ce ticket est une **mission avec livrables**. Le résultat doit être vérifiable avant clôture.",
        color=PREMIUM_COLOR,
    )
    e.add_field(name="Objectif enregistré", value=str(req["objective"])[:1024] or "Non précisé", inline=False)
    e.add_field(name="Livrables", value="\n".join(f"• {item}" for item in deliverables)[:1024], inline=False)
    e.add_field(name="Cycle de mission", value="**1. Diagnostic** → **2. Plan** → **3. Mise en œuvre** → **4. Vérification** → **5. Dossier final**", inline=False)
    e.add_field(name="Critères d'acceptation", value="Le résultat est testé, les changements sont résumés, les risques restants sont signalés et le client sait quoi vérifier ensuite.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text=f"Aide Bot V49 • Ticket #{req['id']} • mission Premium Elite")
    return e


def server_build_control_embed(req, ready: bool) -> discord.Embed:
    data = v48._parse_build_data(str(req["objective"]))
    template = v48.SERVER_TEMPLATES[data.template_key]["label"] if data else "Inconnu"
    e = discord.Embed(
        title="Premium Elite — livraison serveur",
        description=(
            "Service débloqué. **Autorise → Audit 360° → Snapshot → Plan → Confirme → Livraison.**"
            if ready
            else "Commande enregistrée. Les actions de construction restent verrouillées jusqu'à validation du paiement Premium Elite."
        ),
        color=SUCCESS if ready else WARNING,
    )
    if data:
        e.add_field(name="Serveur cible", value=f"`{data.target_guild_id}`", inline=True)
        e.add_field(name="Modèle", value=template, inline=True)
        e.add_field(name="Nom demandé", value=(data.requested_name or "Conserver le nom actuel")[:200], inline=True)
    e.add_field(name="Sécurité V49", value="Aide Bot ne supprime pas automatiquement les salons/rôles existants. Un snapshot JSON est exporté avant construction et la confirmation **CONSTRUIRE** est obligatoire.", inline=False)
    e.add_field(name="Livraison", value="Le ticket reçoit ensuite un rapport avant/après avec scores, éléments créés/réutilisés et checklist de validation.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V49 • paiement → OAuth2 → audit → snapshot → confirmation → rapport")
    return e


class ServerBuildConfirmModalV49(discord.ui.Modal, title="Confirmer la livraison serveur"):
    confirmation = discord.ui.TextInput(label=f"Écris {CONFIRM_WORD}", placeholder=CONFIRM_WORD, max_length=20)

    def __init__(self, bot: commands.Bot, request_id: int) -> None:
        super().__init__()
        self.bot = bot
        self.request_id = request_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if str(self.confirmation).strip().upper() != CONFIRM_WORD:
            return await interaction.response.send_message(f"Construction annulée : il fallait écrire **{CONFIRM_WORD}**.", ephemeral=True)
        req = await self.bot.db.request_by_id(self.request_id)
        if req is None:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        data, target, error = await v48._validated_build_context(self.bot, interaction, req)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        assert data is not None and target is not None
        preflight = v48.analyze_server(target, data.template_key)
        if not preflight.bot_ready:
            return await interaction.response.send_message("Aide Bot n'a pas toutes les permissions nécessaires. Lance d'abord la pré-vérification.", ephemeral=True)

        before360 = analyze_360(target)
        await interaction.response.defer(ephemeral=True, thinking=True)
        if isinstance(interaction.channel, discord.TextChannel):
            try:
                await interaction.channel.send(
                    embed=discord.Embed(
                        title="Snapshot avant construction",
                        description="Copie de la structure actuelle exportée **avant** les modifications automatiques. Ce fichier sert d'inventaire et de référence de restauration manuelle.",
                        color=WARNING,
                    ),
                    file=snapshot_file(target, suffix="before"),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass

        try:
            result = await v48.build_client_server(self.bot, target, data)
        except (discord.Forbidden, discord.HTTPException) as exc:
            return await interaction.followup.send(
                f"Discord a bloqué une étape (`{type(exc).__name__}`). Aucun nettoyage destructif n'est lancé automatiquement ; vérifie les permissions du bot.",
                ephemeral=True,
            )

        after360 = analyze_360(target)
        delivery = discord.Embed(
            title="Dossier de livraison — serveur Premium Elite",
            description=(
                f"Le modèle **{v48.SERVER_TEMPLATES[data.template_key]['label']}** a été appliqué sur **{target.name}**. "
                "Les éléments existants ont été conservés ; la construction ajoute ou réutilise la structure attendue."
            ),
            color=SUCCESS,
        )
        delivery.add_field(
            name="Créé",
            value=f"**Rôles :** {result['roles_created']}\n**Catégories :** {result['categories_created']}\n**Salons :** {result['channels_created']}\n**Panneaux :** {result['panels']}",
            inline=True,
        )
        delivery.add_field(
            name="Réutilisé",
            value=f"**Rôles :** {preflight.roles_reused}\n**Catégories :** {preflight.categories_reused}\n**Salons :** {preflight.channels_reused}",
            inline=True,
        )
        delivery.add_field(name="Score 360°", value=f"**Avant : {before360.total}/100**\n**Après : {after360.total}/100**", inline=True)
        delivery.add_field(name="Sécurité", value=f"**Avant : {before360.security}/100**\n**Après : {after360.security}/100**", inline=True)
        delivery.add_field(name="Onboarding", value=f"**Avant : {before360.onboarding}/100**\n**Après : {after360.onboarding}/100**", inline=True)
        delivery.add_field(name="Support", value=f"**Avant : {before360.support}/100**\n**Après : {after360.support}/100**", inline=True)
        delivery.add_field(name="À vérifier", value="\n".join(f"• {item}" for item in after360.recommendations)[:1024], inline=False)
        delivery.add_field(
            name="Checklist d'acceptation",
            value="Compte membre test → arrivée → règles → salons visibles → permissions → ticket support → fermeture → logs → test après redémarrage des bots.",
            inline=False,
        )
        delivery.set_image(url=BANNER_URL)
        delivery.set_footer(text=f"Aide Bot V49 • Ticket #{req['id']} • dossier de livraison")

        if isinstance(interaction.channel, discord.TextChannel):
            try:
                await interaction.channel.send(
                    embed=delivery,
                    file=readiness_json_file(target, after360),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass
        await interaction.followup.send("Construction terminée. Le snapshot avant changement et le dossier de livraison ont été publiés dans le ticket.", ephemeral=True)

        training = self.bot.get_cog("TrainingCog")
        if training is not None and interaction.guild is not None:
            await training.log_action(
                interaction.guild,
                "Serveur Premium Elite livré",
                f"Ticket #{req['id']} • cible `{target.id}` • modèle **{v48.SERVER_TEMPLATES[data.template_key]['label']}** • score 360 {before360.total}→{after360.total}",
            )


class ServerBuildV49TicketView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Autoriser Aide Bot", style=discord.ButtonStyle.primary, custom_id="aidebot:v49:server:authorize", row=0)
    async def authorize(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await _request_for_ticket(self.bot, interaction)
        if req is None or not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        if interaction.user.id != int(req["user_id"]) and not v48.can(interaction.user, "training.manage"):
            return await interaction.response.send_message("Seul le client ou un responsable peut autoriser le bot.", ephemeral=True)
        client = interaction.guild.get_member(int(req["user_id"]))
        if not v48._request_unlocked(req, client):
            return await interaction.response.send_message("Le paiement doit d'abord être validé.", ephemeral=True)
        data = v48._parse_build_data(str(req["objective"]))
        if data is None:
            return await interaction.response.send_message("Informations serveur invalides.", ephemeral=True)
        url = v48._oauth_url(self.bot, data.target_guild_id)
        if url is None:
            return await interaction.response.send_message("Lien OAuth2 indisponible.", ephemeral=True)
        await interaction.response.send_message("Autorise Aide Bot sur le serveur cible, puis reviens lancer **Audit 360°**.", view=v48.OAuthInviteView(url), ephemeral=True)

    @discord.ui.button(label="Audit 360°", style=discord.ButtonStyle.secondary, custom_id="aidebot:v49:server:audit", row=0)
    async def audit(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await _request_for_ticket(self.bot, interaction)
        if req is None:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        data, target, error = await v48._validated_build_context(self.bot, interaction, req)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        assert target is not None
        report = analyze_360(target)
        await interaction.response.send_message(embed=audit_360_embed(target, report), file=readiness_json_file(target, report), ephemeral=True)

    @discord.ui.button(label="Exporter snapshot", style=discord.ButtonStyle.secondary, custom_id="aidebot:v49:server:snapshot", row=0)
    async def snapshot(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await _request_for_ticket(self.bot, interaction)
        if req is None:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        _data, target, error = await v48._validated_build_context(self.bot, interaction, req)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        assert target is not None
        await interaction.response.send_message(
            "Snapshot JSON généré. Il contient l'inventaire des rôles, catégories, salons et overwrites actuels.",
            file=snapshot_file(target, suffix="manual"),
            ephemeral=True,
        )

    @discord.ui.button(label="Voir le plan", style=discord.ButtonStyle.secondary, custom_id="aidebot:v49:server:plan", row=1)
    async def plan(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await _request_for_ticket(self.bot, interaction)
        if req is None:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        data = v48._parse_build_data(str(req["objective"]))
        if data is None:
            return await interaction.response.send_message("Plan introuvable.", ephemeral=True)
        template = v48.SERVER_TEMPLATES[data.template_key]
        lines = [f"**{category}**\n" + ", ".join(name for _kind, name in channels) for category, channels in template["categories"]]
        e = discord.Embed(title=f"Plan de construction — {template['label']}", description="\n\n".join(lines)[:4000], color=PREMIUM_COLOR)
        e.add_field(name="Objectif", value=data.purpose[:1024], inline=False)
        e.add_field(name="Options", value=data.extras[:1024], inline=False)
        e.set_footer(text="Aide Bot V49 • aperçu uniquement • aucun changement depuis ce bouton")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="Construire mon serveur", style=discord.ButtonStyle.success, custom_id="aidebot:v49:server:build", row=1)
    async def build(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await _request_for_ticket(self.bot, interaction)
        if req is None:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        data, target, error = await v48._validated_build_context(self.bot, interaction, req)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        assert data is not None and target is not None
        preflight = v48.analyze_server(target, data.template_key)
        if not preflight.bot_ready:
            return await interaction.response.send_message("Pré-vérification bloquante : permissions du bot insuffisantes.", ephemeral=True)
        await interaction.response.send_modal(ServerBuildConfirmModalV49(self.bot, int(req["id"])))


def _patch_v48_symbols() -> None:
    # Les patchers V48 sont solides et déjà testés ; on leur donne simplement
    # les nouvelles vues V49 afin que /setup, /buy et la validation paiement
    # publient directement la nouvelle expérience.
    v48.ShopV48View = ShopV49View
    v48.PremiumHubV48View = PremiumHubV49View
    v48.premium_shop_embed = premium_shop_embed
    v48.premium_v48_hub_embed = premium_v49_hub_embed


class PremiumServiceV49Cog(commands.Cog, name="PremiumServiceV48Cog"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        _patch_v48_symbols()
        v48._install_shop_patch()
        v48._install_setup_patch()
        v48._install_payment_patch()

        self.bot.add_view(PremiumHubV49View(self.bot))
        self.bot.add_view(ShopV49View(self.bot))
        self.bot.add_view(ServerBuildV49TicketView(self.bot))
        self.bot.add_view(v48.DirectPremiumVideoView())

        # Compatibilité des anciens messages déjà publiés.
        self.bot.add_view(_V48_HUB_VIEW(self.bot))
        self.bot.add_view(_V48_SHOP_VIEW(self.bot))
        self.bot.add_view(_V48_SERVER_VIEW(self.bot))

    async def unlock_server_build_ticket(self, channel: discord.TextChannel, req) -> None:
        try:
            await channel.send(
                embed=server_build_control_embed(req, True),
                view=ServerBuildV49TicketView(self.bot),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("ticket-"):
            return
        req = None
        for _ in range(12):
            await __import__("asyncio").sleep(0.35)
            req = await self.bot.db.request_by_channel(channel.id)
            if req is not None:
                break
        if req is None:
            return
        key = str(req["training_key"])
        if key == v48.SERVER_BUILD_KEY:
            client = channel.guild.get_member(int(req["user_id"]))
            ready = v48._request_unlocked(req, client)
            try:
                await channel.send(
                    embed=server_build_control_embed(req, ready),
                    view=ServerBuildV49TicketView(self.bot),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            return
        card = mission_elite_embed(req)
        if card is not None:
            try:
                await channel.send(embed=card, allowed_mentions=discord.AllowedMentions.none())
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PremiumServiceV49Cog(bot))
