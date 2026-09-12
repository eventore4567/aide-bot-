from __future__ import annotations

import asyncio
from dataclasses import dataclass

import discord
from discord.ext import commands

import aidebot.public_panels as public_panels
from aidebot.catalog import FORMATIONS
from aidebot.cogs.experience_v43 import member_space_embed
from aidebot.cogs.premium_service_v47 import (
    DIRECT_PREMIUM_VIDEOS,
    PREMIUM_CATEGORY,
    PREMIUM_HUB_CHANNEL,
    PREMIUM_SERVICE_FORMS,
    PREMIUM_VIDEO_CHANNEL,
    SERVER_BUILD_KEY,
    SERVER_TEMPLATES,
    DirectPremiumVideoView,
    OAuthInviteView,
    PremiumServiceModal,
    PremiumServiceSelect,
    ServerBuildRequestModal,
    ServerTemplateChoiceView,
    _client_target_member,
    _oauth_url,
    _parse_build_data,
    _request_unlocked,
    build_client_server,
    premium_v47_video_embed,
)
from aidebot.cogs.setup_server import SetupServerCog
from aidebot.cogs.ticket_experience import PremiumPaymentView
from aidebot.experience_content import BANNER_URL
from aidebot.permissions import can
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed

PREMIUM_COLOR = 0xEB459E
SUCCESS = 0x57F287
WARNING = 0xF1C40F
DANGER = 0xED4245
SHOP_CHANNEL = "🛒・shop"
SHOP_TITLE = "Aide Bot — Boutique Premium"
CONFIRM_WORD = "CONSTRUIRE"


ADDITIONAL_SERVER_TEMPLATES = {
    "academy": {
        "label": "Formation / académie",
        "description": "Cours, ressources, exercices, entraide, progression et espace formateurs.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ FORMATION ━━", (("text", "📚・cours"), ("text", "🧪・exercices"), ("text", "❓・questions"), ("voice", "🎓・Salle de cours"))),
            ("━━ COMMUNAUTÉ ━━", (("text", "💬・général"), ("text", "🏆・progression"), ("text", "⭐・avis"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "💡・suggestions"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"), ("voice", "🔒・Formateurs"))),
        ),
    },
    "esport": {
        "label": "Esport / clan",
        "description": "Équipe, annonces, recrutement, scrims, résultats, vocaux et staff.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ ÉQUIPE ━━", (("text", "🎮・général"), ("text", "📅・planning"), ("text", "🏆・résultats"), ("text", "📝・recrutement"))),
            ("━━ COMPÉTITION ━━", (("text", "⚔️・scrims"), ("text", "🎬・clips"), ("voice", "🔊・Team 1"), ("voice", "🔊・Team 2"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "💡・suggestions"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"), ("voice", "🔒・Coaching"))),
        ),
    },
    "project": {
        "label": "Projet / développement",
        "description": "Roadmap, changelog, bugs, idées, documentation, support et équipe projet.",
        "categories": (
            ("━━ INFORMATIONS ━━", (("text", "👋・bienvenue"), ("text", "📜・règlement"), ("text", "📢・annonces"))),
            ("━━ PROJET ━━", (("text", "🗺️・roadmap"), ("text", "📝・changelog"), ("text", "🐛・bugs"), ("text", "💡・idées"))),
            ("━━ RESSOURCES ━━", (("text", "📚・documentation"), ("text", "🧪・tests"), ("text", "🤖・bot-status"))),
            ("━━ SUPPORT ━━", (("text", "🎫・support"), ("text", "⭐・avis"))),
            ("━━ STAFF ━━", (("text", "📋・staff"), ("text", "🧾・logs"), ("voice", "🔒・Dev room"))),
        ),
    },
}


ADDITIONAL_PREMIUM_SERVICES = {
    "onboarding": {
        "label": "Refaire mon onboarding",
        "description": "Accueil, règles, rôles, premiers salons et parcours nouveau membre.",
        "questions": (
            ("Type de serveur", "Communauté, gaming, boutique, créateur...", 220),
            ("Parcours actuel", "Ce que voit et fait un nouveau membre aujourd’hui", 600),
            ("Problèmes constatés", "Perte, confusion, trop de salons, rôles mal compris...", 500),
            ("Résultat attendu", "Ce qu’un nouveau membre doit comprendre en moins d’une minute", 500),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "staff-system": {
        "label": "Structurer mon staff",
        "description": "Hiérarchie, permissions, responsabilités, sanctions, tickets et procédures.",
        "questions": (
            ("Staff actuel", "Rôles staff + nombre de personnes", 250),
            ("Problèmes actuels", "Inactivité, permissions, sanctions, tickets, organisation...", 600),
            ("Rôles à conserver", "Fondateur, admin, modo, helper, formateur...", 350),
            ("Résultat attendu", "Comment le staff doit fonctionner après la refonte", 500),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
    "launch-review": {
        "label": "Préparer mon lancement",
        "description": "Audit final avant ouverture publique : UX, permissions, sécurité et support.",
        "questions": (
            ("Projet", "Type de serveur + objectif", 300),
            ("État actuel", "Ce qui est déjà prêt et ce qui manque", 600),
            ("Date / période visée", "Quand tu veux ouvrir au public", 180),
            ("Points à vérifier", "Onboarding, permissions, tickets, bots, sécurité...", 500),
            ("Disponibilités", "Jours + horaires possibles", 150),
        ),
    },
}

SERVER_TEMPLATES.update(ADDITIONAL_SERVER_TEMPLATES)
PREMIUM_SERVICE_FORMS.update(ADDITIONAL_PREMIUM_SERVICES)


SERVICE_DELIVERABLES = {
    "audit-server": ("Score et risques principaux", "Priorités classées", "Plan d’amélioration + contrôle final"),
    "improve-server": ("Structure cible", "Refonte rôles/salons/onboarding", "Vérification avec vue membre"),
    "fix-bot": ("Diagnostic reproductible", "Corrections prioritaires", "Tests + vérification production"),
    "security": ("Cartographie des risques", "Corrections de permissions", "Plan d’urgence et contrôle final"),
    "railway": ("Diagnostic logs/déploiement", "Persistance et configuration", "Vérification après redémarrage"),
    "tickets": ("Workflow de tickets", "Permissions et prise en charge", "Test ouverture → résolution → fermeture"),
    "personal-plan": ("Objectif mesurable", "Plan étape par étape", "Exercices + validation finale"),
    "onboarding": ("Parcours nouveau membre", "Réduction des points de friction", "Test du parcours en conditions réelles"),
    "staff-system": ("Hiérarchie claire", "Matrice responsabilités/permissions", "Procédures simples et vérifiables"),
    "launch-review": ("Checklist pré-lancement", "Risques bloquants", "Go / corrections avant ouverture"),
}


for service_key, service in PREMIUM_SERVICE_FORMS.items():
    training_key = f"premium_service_{service_key.replace('-', '_')}"
    FORMATIONS.setdefault(
        training_key,
        {
            "title": f"Premium — {service['label']}",
            "description": service["description"],
            "steps": ["Diagnostic", "Plan", "Mise en œuvre", "Vérification", "Rapport final"],
            "vip": True,
            "kind": "premium-service",
            "difficulty": "Sur mesure",
            "duration": "Selon projet",
        },
    )

FORMATIONS.setdefault(
    SERVER_BUILD_KEY,
    {
        "title": "Premium — création de serveur",
        "description": "Création guidée et automatisée d’un serveur Discord à partir d’un modèle professionnel.",
        "steps": ["Validation", "OAuth2", "Pré-vérification", "Construction", "Audit final"],
        "vip": True,
        "kind": "premium-service",
        "difficulty": "Automatisé + accompagné",
        "duration": "Selon modèle",
    },
)


@dataclass(frozen=True)
class ServerAudit:
    score: int
    risks: tuple[str, ...]
    admin_roles: int
    dangerous_roles: int
    roles_to_create: int = 0
    roles_reused: int = 0
    categories_to_create: int = 0
    categories_reused: int = 0
    channels_to_create: int = 0
    channels_reused: int = 0
    bot_ready: bool = False


def _score_security(
    *,
    everyone_administrator: bool,
    everyone_manage_guild: bool,
    everyone_manage_roles: bool,
    everyone_manage_channels: bool,
    everyone_manage_webhooks: bool,
    everyone_mention_everyone: bool,
    admin_role_count: int,
    dangerous_role_count: int,
    verification_value: int,
    content_filter_value: int,
) -> tuple[int, tuple[str, ...]]:
    score = 100
    risks: list[str] = []
    if everyone_administrator:
        score -= 55
        risks.append("@everyone possède Administrateur — risque critique.")
    if everyone_manage_guild:
        score -= 25
        risks.append("@everyone peut gérer le serveur.")
    if everyone_manage_roles:
        score -= 20
        risks.append("@everyone peut gérer les rôles.")
    if everyone_manage_channels:
        score -= 15
        risks.append("@everyone peut gérer les salons.")
    if everyone_manage_webhooks:
        score -= 10
        risks.append("@everyone peut gérer les webhooks.")
    if everyone_mention_everyone:
        score -= 5
        risks.append("@everyone peut mentionner @everyone/@here.")
    if admin_role_count > 4:
        score -= min(20, (admin_role_count - 4) * 4)
        risks.append(f"Beaucoup de rôles ont Administrateur ({admin_role_count}).")
    if dangerous_role_count > 8:
        score -= min(15, (dangerous_role_count - 8) * 2)
        risks.append(f"Beaucoup de rôles ont des permissions sensibles ({dangerous_role_count}).")
    if verification_value == 0:
        score -= 10
        risks.append("Niveau de vérification Discord désactivé.")
    if content_filter_value == 0:
        score -= 5
        risks.append("Filtre de contenu explicite désactivé.")
    return max(0, score), tuple(risks)


def _template_plan(guild: discord.Guild, template_key: str) -> tuple[int, int, int, int, int, int]:
    expected_roles = ("✅・Membre", "🛡️・Modérateur", "🎫・Support", "📢・Notifications")
    roles_reused = sum(1 for name in expected_roles if discord.utils.get(guild.roles, name=name) is not None)
    roles_to_create = len(expected_roles) - roles_reused

    categories_to_create = 0
    categories_reused = 0
    channels_to_create = 0
    channels_reused = 0
    for category_name, channels in SERVER_TEMPLATES[template_key]["categories"]:
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            categories_to_create += 1
            channels_to_create += len(channels)
            continue
        categories_reused += 1
        for kind, channel_name in channels:
            pool = category.voice_channels if kind == "voice" else category.text_channels
            if discord.utils.get(pool, name=channel_name) is None:
                channels_to_create += 1
            else:
                channels_reused += 1
    return (
        roles_to_create,
        roles_reused,
        categories_to_create,
        categories_reused,
        channels_to_create,
        channels_reused,
    )


def analyze_server(guild: discord.Guild, template_key: str | None = None) -> ServerAudit:
    everyone = guild.default_role.permissions
    admin_roles = [role for role in guild.roles if not role.is_default() and role.permissions.administrator]
    dangerous_roles = [
        role
        for role in guild.roles
        if not role.is_default()
        and (
            role.permissions.administrator
            or role.permissions.manage_guild
            or role.permissions.manage_roles
            or role.permissions.manage_channels
            or role.permissions.manage_webhooks
        )
    ]
    score, risks = _score_security(
        everyone_administrator=everyone.administrator,
        everyone_manage_guild=everyone.manage_guild,
        everyone_manage_roles=everyone.manage_roles,
        everyone_manage_channels=everyone.manage_channels,
        everyone_manage_webhooks=everyone.manage_webhooks,
        everyone_mention_everyone=everyone.mention_everyone,
        admin_role_count=len(admin_roles),
        dangerous_role_count=len(dangerous_roles),
        verification_value=int(getattr(guild.verification_level, "value", 0)),
        content_filter_value=int(getattr(guild.explicit_content_filter, "value", 0)),
    )

    plan = (0, 0, 0, 0, 0, 0)
    if template_key in SERVER_TEMPLATES:
        plan = _template_plan(guild, template_key)

    me = guild.me
    bot_ready = bool(
        me
        and me.guild_permissions.manage_channels
        and me.guild_permissions.manage_roles
        and me.guild_permissions.send_messages
        and me.guild_permissions.embed_links
    )
    return ServerAudit(score, risks, len(admin_roles), len(dangerous_roles), *plan, bot_ready)


def _score_label(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Bon"
    if score >= 55:
        return "À améliorer"
    return "Risque élevé"


def audit_embed(guild: discord.Guild, audit: ServerAudit, template_key: str | None = None) -> discord.Embed:
    color = SUCCESS if audit.score >= 75 else WARNING if audit.score >= 55 else DANGER
    e = discord.Embed(
        title=f"Audit Premium — {guild.name}",
        description=f"**Score sécurité : {audit.score}/100 — {_score_label(audit.score)}**\nAnalyse automatique des permissions visibles par Aide Bot. Elle complète l’audit humain, elle ne le remplace pas.",
        color=color,
    )
    if audit.risks:
        e.add_field(name="Risques détectés", value="\n".join(f"• {risk}" for risk in audit.risks[:8])[:1024], inline=False)
    else:
        e.add_field(name="Risques détectés", value="Aucun risque critique détecté par les contrôles automatiques de base.", inline=False)
    e.add_field(name="Rôles Administrateur", value=str(audit.admin_roles), inline=True)
    e.add_field(name="Rôles sensibles", value=str(audit.dangerous_roles), inline=True)
    e.add_field(name="Aide Bot prêt", value="Oui" if audit.bot_ready else "Non — permissions à corriger", inline=True)
    if template_key in SERVER_TEMPLATES:
        e.add_field(
            name="Plan de construction",
            value=(
                f"**Rôles :** {audit.roles_to_create} à créer • {audit.roles_reused} réutilisés\n"
                f"**Catégories :** {audit.categories_to_create} à créer • {audit.categories_reused} réutilisées\n"
                f"**Salons :** {audit.channels_to_create} à créer • {audit.channels_reused} réutilisés"
            ),
            inline=False,
        )
    e.add_field(
        name="À vérifier aussi manuellement",
        value="Hiérarchie réelle du staff • bots/intégrations • webhooks • procédures de récupération • parcours membre • règles de modération.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V48 • audit automatique + accompagnement humain")
    return e


def premium_v48_hub_embed(price: int) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot Premium — Centre de services",
        description=(
            f"**{price} Robux = un pack de service, pas un badge.**\n\n"
            "Premium te donne un vrai parcours : diagnostic → plan → mise en œuvre → vérification → rapport final. "
            "Tu peux faire auditer ton serveur, le faire construire automatiquement, corriger ton bot, préparer un lancement, refaire ton onboarding ou structurer ton staff."
        ),
        color=PREMIUM_COLOR,
    )
    e.add_field(name="Serveur", value="**8 modèles** + pré-vérification + confirmation avant construction + audit final.", inline=True)
    e.add_field(name="Accompagnement", value=f"**{len(PREMIUM_SERVICE_FORMS)} services** avec questionnaire spécifique et livrables clairs.", inline=True)
    e.add_field(name="Audit instantané", value="Score sécurité, permissions sensibles, risques et plan de création/réutilisation.", inline=True)
    e.add_field(name="Bot / production", value="Architecture, bugs, Railway, DB, logs, tests, GitHub et fiabilité.", inline=True)
    e.add_field(name="Organisation", value="Onboarding, staff, tickets, lancement public et expérience membre.", inline=True)
    e.add_field(name="Ressources", value=f"{len(DIRECT_PREMIUM_VIDEOS)} vidéos directes + bibliothèque Premium avancée.", inline=True)
    e.add_field(
        name="Création de serveur — sécurité",
        value="Aide Bot ne supprime pas ton contenu existant. Avant la construction, il affiche ce qu’il va créer/réutiliser et demande une confirmation explicite. Discord exige toujours ton autorisation OAuth2 pour ajouter le bot au serveur cible.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V48 • diagnostic → plan → action → vérification → rapport")
    return e


def premium_shop_embed(price: int) -> discord.Embed:
    e = discord.Embed(
        title=SHOP_TITLE,
        description=(
            f"**Pack Premium — {price} Robux**\n\n"
            "Tu achètes un **service complet** : audit, configuration de serveur, support prioritaire, bot/production, sécurité, tickets, onboarding, staff, lancement et plan personnalisé."
        ),
        color=PREMIUM_COLOR,
    )
    e.add_field(name="Serveur construit", value="8 modèles • preview avant création • OAuth2 • confirmation • construction idempotente • audit final.", inline=False)
    e.add_field(name="Audit & sécurité", value="Score automatique + analyse humaine des permissions, bots, staff et risques.", inline=True)
    e.add_field(name="Bot & production", value="Bugs, architecture, Railway, SQLite/PostgreSQL, logs, tests et GitHub.", inline=True)
    e.add_field(name="Organisation", value="Onboarding, système de tickets, structure staff et préparation du lancement.", inline=True)
    e.add_field(name="Suivi", value="Chaque demande Premium a un objectif précis, des étapes, une vérification et des livrables attendus.", inline=True)
    e.add_field(
        name="Parcours d’achat",
        value="**1.** Acheter Premium → **2.** ticket privé → **3.** validation Direction → **4.** rôle 💎・VIP → **5.** centre Premium et services débloqués.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V48 • Premium = résultat vérifiable, pas seulement du contenu")
    return e


def server_templates_v48_embed() -> discord.Embed:
    e = discord.Embed(
        title="Premium — créer mon serveur",
        description=(
            "Choisis un des **8 modèles**. Une demande privée est créée. Après paiement si nécessaire et autorisation OAuth2, tu peux d’abord **pré-vérifier** le serveur : "
            "Aide Bot affiche ce qui sera créé ou réutilisé et les risques de sécurité détectés. La construction demande ensuite une confirmation explicite."
        ),
        color=PREMIUM_COLOR,
    )
    for data in SERVER_TEMPLATES.values():
        channel_count = sum(len(channels) for _category, channels in data["categories"])
        e.add_field(name=data["label"], value=f"{data['description']}\n{len(data['categories'])} catégories • {channel_count} salons/vocaux", inline=True)
    e.add_field(name="Aucune suppression automatique", value="Les éléments existants sont réutilisés quand leur nom correspond. Aide Bot n’efface pas les salons/rôles du client.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V48 • modèle → ticket → OAuth2 → pré-vérification → confirmation → construction")
    return e


def mission_embed(req) -> discord.Embed | None:
    key = str(req["training_key"])
    prefix = "premium_service_"
    if not key.startswith(prefix):
        return None
    service_key = key[len(prefix):].replace("_", "-")
    service = PREMIUM_SERVICE_FORMS.get(service_key)
    if service is None:
        return None
    deliverables = SERVICE_DELIVERABLES.get(service_key, ("Diagnostic", "Plan d’action", "Vérification finale"))
    e = discord.Embed(
        title=f"Mission Premium — {service['label']}",
        description="Cette demande doit produire un résultat vérifiable. Le ticket sert au suivi, pas seulement à échanger des messages.",
        color=PREMIUM_COLOR,
    )
    e.add_field(name="Livrables attendus", value="\n".join(f"• {item}" for item in deliverables), inline=False)
    e.add_field(name="Méthode", value="**1. Diagnostic** → **2. Plan** → **3. Mise en œuvre** → **4. Vérification** → **5. Rapport final**", inline=False)
    e.add_field(name="Fin de mission", value="Avant de terminer, vérifie que l’objectif initial est atteint et résume clairement ce qui a été fait + ce qui reste à surveiller.", inline=False)
    e.set_footer(text=f"Aide Bot V48 • Ticket #{req['id']} • Premium avec livrables")
    return e


async def _require_vip(interaction: discord.Interaction) -> bool:
    if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
        return True
    shop = discord.utils.get(interaction.guild.text_channels, name=SHOP_CHANNEL) if interaction.guild else None
    await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
    return False


async def _request_for_ticket(bot: commands.Bot, interaction: discord.Interaction):
    if interaction.channel is None:
        return None
    return await bot.db.request_by_channel(interaction.channel.id)


async def _validated_build_context(bot: commands.Bot, interaction: discord.Interaction, req):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return None, None, "Contexte Discord invalide."
    if str(req["training_key"]) != SERVER_BUILD_KEY:
        return None, None, "Cette demande n’est pas une création de serveur."
    if interaction.user.id != int(req["user_id"]) and not can(interaction.user, "training.manage"):
        return None, None, "Seul le client ou un responsable peut utiliser cette action."
    client = interaction.guild.get_member(int(req["user_id"]))
    if not _request_unlocked(req, client):
        return None, None, "La création reste verrouillée jusqu’à la validation du paiement Premium."
    data = _parse_build_data(str(req["objective"]))
    if data is None:
        return None, None, "Les informations du serveur cible sont invalides."
    target = bot.get_guild(data.target_guild_id)
    if target is None:
        return data, None, "Aide Bot n’est pas encore présent sur le serveur cible. Utilise d’abord **Autoriser Aide Bot**."
    target_member = await _client_target_member(target, int(req["user_id"]))
    if target_member is None or not (
        target.owner_id == target_member.id
        or target_member.guild_permissions.administrator
        or target_member.guild_permissions.manage_guild
    ):
        return data, target, "Le client doit être propriétaire ou posséder Administrateur/Gérer le serveur sur le serveur cible."
    return data, target, None


class InstantAuditModal(discord.ui.Modal, title="Audit Premium instantané"):
    server_id = discord.ui.TextInput(label="ID du serveur", placeholder="Copier l’identifiant du serveur", max_length=22)

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await _require_vip(interaction) or not isinstance(interaction.user, discord.Member):
            return
        raw = str(self.server_id).strip()
        if not raw.isdigit() or not 15 <= len(raw) <= 22:
            return await interaction.response.send_message("ID de serveur invalide.", ephemeral=True)
        target_id = int(raw)
        target = self.bot.get_guild(target_id)
        if target is None:
            url = _oauth_url(self.bot, target_id)
            if url is None:
                return await interaction.response.send_message("Aide Bot n’est pas présent sur ce serveur et le lien OAuth2 est indisponible.", ephemeral=True)
            return await interaction.response.send_message(
                "Aide Bot doit d’abord être autorisé sur le serveur pour pouvoir l’auditer.",
                view=OAuthInviteView(url),
                ephemeral=True,
            )
        member = await _client_target_member(target, interaction.user.id)
        if member is None or not (
            target.owner_id == member.id or member.guild_permissions.administrator or member.guild_permissions.manage_guild
        ):
            return await interaction.response.send_message("Tu dois être propriétaire ou avoir Gérer le serveur sur le serveur audité.", ephemeral=True)
        await interaction.response.send_message(embed=audit_embed(target, analyze_server(target)), ephemeral=True)


class PremiumHubV48View(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(PremiumServiceSelect(bot))

    @discord.ui.button(label="Créer mon serveur", style=discord.ButtonStyle.success, custom_id="aidebot:v48:premium:server", row=1)
    async def server(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_message(embed=server_templates_v48_embed(), view=ServerTemplateChoiceView(self.bot), ephemeral=True)

    @discord.ui.button(label="Audit instantané", style=discord.ButtonStyle.primary, custom_id="aidebot:v48:premium:audit", row=1)
    async def audit(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_modal(InstantAuditModal(self.bot))

    @discord.ui.button(label="Vidéos VIP", style=discord.ButtonStyle.primary, custom_id="aidebot:v48:premium:videos", row=1)
    async def videos(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_message(embed=premium_v47_video_embed(), view=DirectPremiumVideoView(), ephemeral=True)

    @discord.ui.button(label="Mon espace", style=discord.ButtonStyle.secondary, custom_id="aidebot:v48:premium:space", row=2)
    async def space(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction) or not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=await member_space_embed(self.bot, interaction.user), ephemeral=True)

    @discord.ui.button(label="Statut VIP", style=discord.ButtonStyle.secondary, custom_id="aidebot:v48:premium:status", row=2)
    async def status(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction) or not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=premium_member_embed(interaction.user), ephemeral=True)


class ShopV48View(public_panels.ShopView):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.bot = bot

    @discord.ui.button(label="Commander un serveur", style=discord.ButtonStyle.primary, custom_id="aidebot:v48:shop:server", row=1)
    async def server(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=server_templates_v48_embed(), view=ServerTemplateChoiceView(self.bot), ephemeral=True)

    @discord.ui.button(label="Voir tout le pack", style=discord.ButtonStyle.secondary, custom_id="aidebot:v48:shop:pack", row=1)
    async def pack(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            return await interaction.response.send_message(embed=premium_v48_hub_embed(self.bot.settings.vip_price_robux), view=PremiumHubV48View(self.bot), ephemeral=True)
        await interaction.response.send_message(embed=premium_v48_hub_embed(self.bot.settings.vip_price_robux), ephemeral=True)

    @discord.ui.button(label="Audit Premium", style=discord.ButtonStyle.secondary, custom_id="aidebot:v48:shop:audit", row=2)
    async def audit(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await _require_vip(interaction):
            return
        await interaction.response.send_modal(InstantAuditModal(self.bot))


class ServerBuildConfirmModal(discord.ui.Modal, title="Confirmer la construction"):
    confirmation = discord.ui.TextInput(
        label=f"Écris {CONFIRM_WORD}",
        placeholder=CONFIRM_WORD,
        max_length=20,
    )

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
        data, target, error = await _validated_build_context(self.bot, interaction, req)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        assert data is not None and target is not None
        before = analyze_server(target, data.template_key)
        if not before.bot_ready:
            return await interaction.response.send_message(
                "Aide Bot est présent mais n’a pas toutes les permissions nécessaires : **Gérer les salons, Gérer les rôles, Envoyer des messages et Intégrer des liens**.",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            report = await build_client_server(self.bot, target, data)
        except (discord.Forbidden, discord.HTTPException) as exc:
            return await interaction.followup.send(
                f"Discord a bloqué la configuration (`{type(exc).__name__}`). Vérifie les permissions et la hiérarchie du rôle Aide Bot.",
                ephemeral=True,
            )

        after = analyze_server(target, data.template_key)
        result = discord.Embed(
            title="Configuration Premium terminée",
            description=f"Le modèle **{SERVER_TEMPLATES[data.template_key]['label']}** a été appliqué sur **{target.name}**. Aucun salon ou rôle utilisateur existant n’a été supprimé.",
            color=SUCCESS,
        )
        result.add_field(
            name="Créé maintenant",
            value=f"**Rôles :** {report['roles_created']}\n**Catégories :** {report['categories_created']}\n**Salons :** {report['channels_created']}\n**Panneaux :** {report['panels']}",
            inline=True,
        )
        result.add_field(
            name="Réutilisé",
            value=f"**Rôles :** {before.roles_reused}\n**Catégories :** {before.categories_reused}\n**Salons :** {before.channels_reused}",
            inline=True,
        )
        result.add_field(name="Audit après configuration", value=f"**{after.score}/100 — {_score_label(after.score)}**", inline=True)
        if after.risks:
            result.add_field(name="À corriger ensuite", value="\n".join(f"• {risk}" for risk in after.risks[:6])[:1024], inline=False)
        result.add_field(
            name="Test final conseillé",
            value="Teste avec un vrai compte membre : arrivée → règlement → salons visibles → permissions → ticket support → fermeture. Ensuite ajuste uniquement ce qui ne correspond pas à ton projet.",
            inline=False,
        )
        result.set_image(url=BANNER_URL)
        result.set_footer(text=f"Aide Bot V48 • Ticket #{req['id']} • rapport de construction")

        if isinstance(interaction.channel, discord.TextChannel):
            try:
                await interaction.channel.send(embed=result, allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                pass
        await interaction.followup.send("Configuration terminée. Le rapport complet a été publié dans le ticket.", ephemeral=True)

        training = self.bot.get_cog("TrainingCog")
        if training is not None and interaction.guild is not None:
            await training.log_action(
                interaction.guild,
                "Serveur Premium configuré V48",
                f"Ticket #{req['id']} • cible `{target.id}` • modèle **{SERVER_TEMPLATES[data.template_key]['label']}** • score {after.score}/100",
            )


class ServerBuildV48TicketView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Autoriser Aide Bot", style=discord.ButtonStyle.primary, custom_id="aidebot:v48:server:authorize", row=0)
    async def authorize(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await _request_for_ticket(self.bot, interaction)
        if req is None:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if interaction.user.id != int(req["user_id"]) and not can(interaction.user, "training.manage"):
            return await interaction.response.send_message("Seul le client ou un responsable peut autoriser le bot.", ephemeral=True)
        client = interaction.guild.get_member(int(req["user_id"]))
        if not _request_unlocked(req, client):
            return await interaction.response.send_message("Le paiement doit d’abord être validé.", ephemeral=True)
        data = _parse_build_data(str(req["objective"]))
        if data is None:
            return await interaction.response.send_message("Informations du serveur cible invalides.", ephemeral=True)
        url = _oauth_url(self.bot, data.target_guild_id)
        if url is None:
            return await interaction.response.send_message("Lien OAuth2 indisponible. Réessaie dans quelques secondes.", ephemeral=True)
        await interaction.response.send_message(
            "Autorise Aide Bot sur le serveur cible. Ensuite reviens ici et utilise **Pré-vérifier** avant de construire.",
            view=OAuthInviteView(url),
            ephemeral=True,
        )

    @discord.ui.button(label="Pré-vérifier", style=discord.ButtonStyle.secondary, custom_id="aidebot:v48:server:preflight", row=0)
    async def preflight(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await _request_for_ticket(self.bot, interaction)
        if req is None:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        data, target, error = await _validated_build_context(self.bot, interaction, req)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        assert data is not None and target is not None
        await interaction.response.send_message(embed=audit_embed(target, analyze_server(target, data.template_key), data.template_key), ephemeral=True)

    @discord.ui.button(label="Voir le plan", style=discord.ButtonStyle.secondary, custom_id="aidebot:v48:server:plan", row=0)
    async def plan(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await _request_for_ticket(self.bot, interaction)
        if req is None:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        data = _parse_build_data(str(req["objective"]))
        if data is None:
            return await interaction.response.send_message("Plan introuvable.", ephemeral=True)
        template = SERVER_TEMPLATES[data.template_key]
        lines = [f"**{category}**\n" + ", ".join(name for _kind, name in channels) for category, channels in template["categories"]]
        e = discord.Embed(title=f"Plan — {template['label']}", description="\n\n".join(lines)[:4000], color=PREMIUM_COLOR)
        e.add_field(name="Objectif", value=data.purpose[:1024], inline=False)
        e.add_field(name="Options demandées", value=data.extras[:1024], inline=False)
        e.set_footer(text="Aide Bot V48 • rien n’est créé depuis cet écran")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="Construire mon serveur", style=discord.ButtonStyle.success, custom_id="aidebot:v48:server:build", row=1)
    async def build(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        req = await _request_for_ticket(self.bot, interaction)
        if req is None:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        data, target, error = await _validated_build_context(self.bot, interaction, req)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        assert data is not None and target is not None
        audit = analyze_server(target, data.template_key)
        if not audit.bot_ready:
            return await interaction.response.send_message(
                "Pré-vérification bloquante : Aide Bot n’a pas toutes les permissions nécessaires. Réautorise-le puis réessaie.",
                ephemeral=True,
            )
        await interaction.response.send_modal(ServerBuildConfirmModal(self.bot, int(req["id"])))


def server_build_control_embed(req, ready: bool) -> discord.Embed:
    data = _parse_build_data(str(req["objective"]))
    template = SERVER_TEMPLATES[data.template_key]["label"] if data else "Inconnu"
    e = discord.Embed(
        title="Premium — création de serveur V48",
        description=(
            "Le service est débloqué. **Autorise le bot → pré-vérifie → regarde le plan → confirme la construction.**"
            if ready
            else "La commande est enregistrée. La construction reste verrouillée jusqu’à la validation du paiement Premium."
        ),
        color=SUCCESS if ready else WARNING,
    )
    if data:
        e.add_field(name="Serveur cible", value=f"`{data.target_guild_id}`", inline=True)
        e.add_field(name="Modèle", value=template, inline=True)
        e.add_field(name="Nom demandé", value=(data.requested_name or "Conserver le nom actuel")[:200], inline=True)
    e.add_field(
        name="Protection V48",
        value="Avant de modifier le serveur, Aide Bot calcule les éléments à créer/réutiliser, vérifie ses permissions et demande d’écrire **CONSTRUIRE**. Aucun contenu existant n’est supprimé automatiquement.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V48 • paiement → OAuth2 → pré-vérification → confirmation → rapport")
    return e


def _install_shop_patch() -> None:
    public_panels.ShopView = ShopV48View
    public_panels.shop_embed = premium_shop_embed
    public_panels.premium_embed = premium_v48_hub_embed
    try:
        import aidebot.cogs.storefront as storefront

        storefront.ShopView = ShopV48View
        storefront.shop_embed = premium_shop_embed
    except Exception:
        pass


def _install_setup_patch() -> None:
    if getattr(SetupServerCog, "_aidebot_v48_patched", False):
        return
    original = SetupServerCog._reconcile_channel_permissions

    async def reconcile(self: SetupServerCog, guild: discord.Guild, channel: discord.TextChannel, roles: dict[str, discord.Role]) -> None:
        await original(self, guild, channel, roles)
        if channel.name == SHOP_CHANNEL:
            await self._upsert_panel(channel, premium_shop_embed(self.bot.settings.vip_price_robux), ShopV48View(self.bot))
        if channel.category and channel.category.name == PREMIUM_CATEGORY:
            if channel.name == PREMIUM_HUB_CHANNEL:
                await self._upsert_panel(channel, premium_v48_hub_embed(self.bot.settings.vip_price_robux), PremiumHubV48View(self.bot))
            elif channel.name == PREMIUM_VIDEO_CHANNEL:
                await self._upsert_panel(channel, premium_v47_video_embed(), DirectPremiumVideoView())

    SetupServerCog._reconcile_channel_permissions = reconcile
    SetupServerCog._aidebot_v48_patched = True


def _install_payment_patch() -> None:
    if getattr(PremiumPaymentView, "_aidebot_v48_patched", False):
        return
    original = PremiumPaymentView._transition

    async def transition(self: PremiumPaymentView, interaction: discord.Interaction, target: str) -> None:
        req_before = await self.bot.db.request_by_channel(interaction.channel.id) if interaction.channel else None
        previous = str(req_before["payment_status"]) if req_before else ""
        await original(self, interaction, target)
        if target != "paid" or req_before is None or previous == "paid" or not isinstance(interaction.channel, discord.TextChannel):
            return
        refreshed = await self.bot.db.request_by_id(int(req_before["id"]))
        if refreshed is None or str(refreshed["payment_status"]) != "paid":
            return
        cog = self.bot.get_cog("PremiumServiceV48Cog")
        if cog is None:
            return
        if str(refreshed["training_key"]) == SERVER_BUILD_KEY:
            await cog.unlock_server_build_ticket(interaction.channel, refreshed)
        elif str(refreshed["training_key"]) == "vip":
            try:
                await interaction.channel.send(
                    embed=premium_v48_hub_embed(self.bot.settings.vip_price_robux),
                    view=PremiumHubV48View(self.bot),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass

    PremiumPaymentView._transition = transition
    PremiumPaymentView._aidebot_v48_patched = True


class PremiumServiceV48Cog(commands.Cog, name="PremiumServiceV48Cog"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        _install_shop_patch()
        _install_setup_patch()
        _install_payment_patch()
        self.bot.add_view(PremiumHubV48View(self.bot))
        self.bot.add_view(ShopV48View(self.bot))
        self.bot.add_view(ServerBuildV48TicketView(self.bot))
        self.bot.add_view(DirectPremiumVideoView())

    async def unlock_server_build_ticket(self, channel: discord.TextChannel, req) -> None:
        try:
            await channel.send(
                embed=server_build_control_embed(req, True),
                view=ServerBuildV48TicketView(self.bot),
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
            await asyncio.sleep(0.35)
            req = await self.bot.db.request_by_channel(channel.id)
            if req is not None:
                break
        if req is None:
            return
        key = str(req["training_key"])
        if key == SERVER_BUILD_KEY:
            client = channel.guild.get_member(int(req["user_id"]))
            ready = _request_unlocked(req, client)
            try:
                await channel.send(
                    embed=server_build_control_embed(req, ready),
                    view=ServerBuildV48TicketView(self.bot),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            return
        card = mission_embed(req)
        if card is not None:
            try:
                await channel.send(embed=card, allowed_mentions=discord.AllowedMentions.none())
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PremiumServiceV48Cog(bot))
