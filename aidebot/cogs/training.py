from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.catalog import FORMATIONS
from aidebot.experience_content import BANNER_URL
from aidebot.payments import PAYMENT_LABELS
from aidebot.permissions import can, decide
from aidebot.premium_access import has_premium, missing_premium_message
from aidebot.request_integrity import cancel_request_atomic, create_request_with_entitlement_atomic
from aidebot.ticketing import format_guidance


def embed(title: str, description: str, color: int = 0x5865F2) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


TRAINING_FORMS: dict[str, dict] = {
    "discord": {
        "title": "Débuter sur Discord",
        "fields": (
            ("level", "Ton niveau sur Discord", "Jamais utilisé / débutant / je connais les bases", discord.TextStyle.short, True, 100),
            ("goal", "Ce que tu veux savoir faire", "Ex: comprendre les rôles, salons, messages et réglages importants", discord.TextStyle.paragraph, True, 550),
            ("device", "Ton appareil principal", "PC / Mac / téléphone / tablette", discord.TextStyle.short, True, 100),
            ("blocker", "Ce qui te bloque aujourd’hui", "Explique ce que tu ne comprends pas encore", discord.TextStyle.paragraph, False, 450),
            ("availability", "Tes disponibilités", "Ex: mercredi 18h-20h", discord.TextStyle.short, True, 150),
        ),
    },
    "serveur": {
        "title": "Créer son serveur",
        "fields": (
            ("level", "État actuel du serveur", "Pas créé / vide / déjà commencé", discord.TextStyle.short, True, 100),
            ("goal", "Projet et objectif du serveur", "Communauté, gaming, boutique, support... et résultat attendu", discord.TextStyle.paragraph, True, 600),
            ("audience", "Public et taille visée", "Ex: amis, 100 membres, communauté publique...", discord.TextStyle.short, True, 150),
            ("blocker", "Ce que tu veux améliorer en priorité", "Structure, rôles, permissions, onboarding, tickets, sécurité...", discord.TextStyle.paragraph, True, 450),
            ("availability", "Tes disponibilités", "Ex: samedi 14h-18h", discord.TextStyle.short, True, 150),
        ),
    },
    "permissions": {
        "title": "Permissions & sécurité",
        "fields": (
            ("level", "Ton niveau / rôle actuel", "Débutant / modérateur / administrateur...", discord.TextStyle.short, True, 120),
            ("goal", "Le problème exact", "Qui doit voir/faire quoi ? Qu’est-ce qui ne fonctionne pas ?", discord.TextStyle.paragraph, True, 650),
            ("roles", "Rôles ou salons concernés", "Ex: @Membre, @Modo, catégorie Staff...", discord.TextStyle.short, True, 180),
            ("blocker", "Ce que tu as déjà essayé", "Permissions cochées, overrides, ordre des rôles, tests effectués...", discord.TextStyle.paragraph, False, 450),
            ("availability", "Tes disponibilités", "Ex: ce soir 19h-21h", discord.TextStyle.short, True, 150),
        ),
    },
    "bot": {
        "title": "Créer son bot Discord",
        "fields": (
            ("level", "Ton niveau en code", "Aucun / bases Python / intermédiaire", discord.TextStyle.short, True, 120),
            ("goal", "Le bot que tu veux créer", "Décris les fonctions principales et le résultat final attendu", discord.TextStyle.paragraph, True, 650),
            ("stack", "Outils déjà utilisés", "Python, discord.py, GitHub, Railway... ou aucun", discord.TextStyle.short, True, 180),
            ("blocker", "Erreur ou blocage actuel", "Message d’erreur, étape où tu bloques, ce que tu as déjà testé", discord.TextStyle.paragraph, False, 450),
            ("availability", "Tes disponibilités", "Ex: week-end 15h-20h", discord.TextStyle.short, True, 150),
        ),
    },
    "vip": {
        "title": "Accompagnement Premium",
        "fields": (
            ("level", "Ton niveau actuel", "Débutant / intermédiaire / avancé", discord.TextStyle.short, True, 120),
            ("goal", "Ton projet et ton résultat final", "Décris précisément ce que tu veux obtenir avec l’accompagnement", discord.TextStyle.paragraph, True, 650),
            ("scope", "Ce que tu veux travailler", "Serveur, bot, sécurité, permissions, audit, organisation...", discord.TextStyle.short, True, 180),
            ("blocker", "Tes blocages actuels", "Ce qui t’empêche d’avancer et ce qui a déjà été essayé", discord.TextStyle.paragraph, False, 450),
            ("availability", "Tes disponibilités", "Jours + horaires possibles", discord.TextStyle.short, True, 150),
        ),
    },
    "serveur-pro": {
        "title": "Serveur professionnel",
        "fields": (
            ("level", "État actuel du serveur", "Nouveau / existant / déjà public", discord.TextStyle.short, True, 120),
            ("goal", "Objectif professionnel", "Public, service proposé, image souhaitée et résultat final", discord.TextStyle.paragraph, True, 650),
            ("scope", "Éléments à refaire", "Architecture, rôles, onboarding, tickets, logs, staff...", discord.TextStyle.short, True, 180),
            ("blocker", "Problèmes actuels", "Permissions, organisation, sécurité, expérience membre...", discord.TextStyle.paragraph, False, 450),
            ("availability", "Tes disponibilités", "Jours + horaires possibles", discord.TextStyle.short, True, 150),
        ),
    },
    "bot-avance": {
        "title": "Bot avancé",
        "fields": (
            ("level", "Stack et niveau actuel", "Python/discord.py, DB, Git, hébergement...", discord.TextStyle.short, True, 160),
            ("goal", "Architecture / fonctionnalités visées", "Décris le bot final et les fonctions importantes", discord.TextStyle.paragraph, True, 650),
            ("scope", "Parties à travailler", "DB, permissions, logs, tests, déploiement, architecture...", discord.TextStyle.short, True, 180),
            ("blocker", "Erreurs ou dette technique", "Ce qui casse, ralentit ou rend le bot difficile à maintenir", discord.TextStyle.paragraph, False, 450),
            ("availability", "Tes disponibilités", "Jours + horaires possibles", discord.TextStyle.short, True, 150),
        ),
    },
    "securite-avancee": {
        "title": "Sécurité avancée",
        "fields": (
            ("level", "Contexte du serveur", "Taille, public, niveau de risque", discord.TextStyle.short, True, 160),
            ("goal", "Objectif de l’audit", "Ce que tu veux protéger ou vérifier précisément", discord.TextStyle.paragraph, True, 650),
            ("scope", "Zones sensibles", "Rôles, bots, permissions, webhooks, anti-raid...", discord.TextStyle.short, True, 180),
            ("blocker", "Incidents ou inquiétudes", "Décris les problèmes déjà vus sans envoyer de secrets", discord.TextStyle.paragraph, False, 450),
            ("availability", "Tes disponibilités", "Jours + horaires possibles", discord.TextStyle.short, True, 150),
        ),
    },
}


def _human_status(status: str) -> str:
    labels = {
        "open": "Ouvert — en attente de prise en charge",
        "payment_pending": "En attente de validation du paiement",
        "payment_refused": "Paiement refusé",
        "payment_refunded": "Remboursé",
        "completed": "Terminé",
        "closed": "Archivé",
    }
    return labels.get(status, status.replace("_", " ").capitalize())


class ReviewModal(discord.ui.Modal, title="Laisser un avis"):
    rating = discord.ui.TextInput(label="Note sur 5", placeholder="5", max_length=1)
    comment = discord.ui.TextInput(label="Commentaire", style=discord.TextStyle.paragraph, max_length=800)

    def __init__(self, cog: "TrainingCog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not interaction.channel:
            return
        req = await self.cog.bot.db.request_by_channel(interaction.channel.id)
        if not req or req["user_id"] != interaction.user.id or req["status"] not in {"completed", "closed"} or not req["trainer_id"]:
            return await interaction.response.send_message("Cet avis n’est pas disponible ici.", ephemeral=True)
        try:
            rating = int(str(self.rating))
        except ValueError:
            rating = 0
        if rating < 1 or rating > 5:
            return await interaction.response.send_message("La note doit être comprise entre 1 et 5.", ephemeral=True)
        created = await self.cog.bot.db.add_review(
            interaction.guild.id,
            req["id"],
            interaction.user.id,
            req["trainer_id"],
            rating,
            str(self.comment),
        )
        if not created:
            return await interaction.response.send_message("Tu as déjà laissé un avis pour cette demande.", ephemeral=True)
        channel = discord.utils.get(interaction.guild.text_channels, name="⭐・avis")
        if channel:
            await channel.send(embed=embed("Nouvel avis", f"**{rating}/5** pour <@{req['trainer_id']}>\n{self.comment}", 0xF1C40F))
        await self.cog.log_action(interaction.guild, "Avis", f"Demande #{req['id']} • {interaction.user.mention} a noté <@{req['trainer_id']}> : {rating}/5")
        await interaction.response.send_message("Merci, ton avis a été enregistré.", ephemeral=True)


class ReviewView(discord.ui.View):
    def __init__(self, cog: "TrainingCog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Laisser un avis", style=discord.ButtonStyle.secondary, custom_id="aidebot:review")
    async def review(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(ReviewModal(self.cog))


class TicketActionsView(discord.ui.View):
    def __init__(self, cog: "TrainingCog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    async def _request(self, interaction: discord.Interaction):
        if not interaction.channel:
            return None
        return await self.cog.bot.db.request_by_channel(interaction.channel.id)

    @discord.ui.button(label="Prendre", style=discord.ButtonStyle.primary, custom_id="aidebot:ticket:claim")
    async def claim(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        req = await self._request(interaction)
        if not req:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        if req["payment_status"] == "pending":
            return await interaction.response.send_message("Le paiement doit d’abord être validé dans ce ticket.", ephemeral=True)
        capability = "help.claim" if req["training_key"] == "community_help" else "training.claim"
        decision = decide(interaction.user, capability)
        if not decision.allowed:
            roles = ", ".join(decision.allowed_roles) or "aucun"
            return await interaction.response.send_message(
                f"Accès refusé. Permission `{capability}`. Rôles autorisés : {roles}.",
                ephemeral=True,
            )
        if not await self.cog.bot.db.claim_request(req["id"], interaction.user.id):
            fresh = await self.cog.bot.db.request_by_id(req["id"])
            if fresh and fresh["trainer_id"]:
                return await interaction.response.send_message(f"Déjà prise par <@{fresh['trainer_id']}>.", ephemeral=True)
            return await interaction.response.send_message("Cette demande n’est plus disponible.", ephemeral=True)
        await self.cog.log_action(interaction.guild, "Demande prise", f"#{req['id']} prise par {interaction.user.mention}")
        await interaction.response.send_message(f"Prise en charge par {interaction.user.mention}. Le client sait maintenant qui suit son ticket.")

    @discord.ui.button(label="Étape suivante", style=discord.ButtonStyle.secondary, custom_id="aidebot:ticket:progress")
    async def progress(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        req = await self._request(interaction)
        if not req:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        if interaction.user.id != req["trainer_id"] and not can(interaction.user, "training.manage"):
            return await interaction.response.send_message("Seul le formateur assigné ou un responsable peut avancer la progression.", ephemeral=True)
        advanced = await self.cog.bot.db.advance_request(req["id"])
        if advanced is None:
            return await interaction.response.send_message("Impossible d’avancer : la demande est terminée, fermée ou sans formateur.", ephemeral=True)
        new_progress, total_steps = advanced
        data = FORMATIONS.get(req["training_key"])
        next_label = "Terminé" if new_progress >= total_steps else (data["steps"][new_progress] if data and new_progress < len(data["steps"]) else "Étape suivante")
        guidance = format_guidance(req["training_key"], new_progress)
        await self.cog.log_action(interaction.guild, "Progression", f"#{req['id']} • {new_progress}/{total_steps} par {interaction.user.mention}")
        message = f"Progression : **{new_progress}/{total_steps}** • prochaine étape : **{next_label}**"
        if guidance:
            message += f"\n\n{guidance}"
        await interaction.response.send_message(message)

    @discord.ui.button(label="Terminer", style=discord.ButtonStyle.success, custom_id="aidebot:ticket:complete")
    async def complete(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        req = await self._request(interaction)
        if not req:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        if interaction.user.id != req["trainer_id"] and not can(interaction.user, "training.manage"):
            return await interaction.response.send_message("Tu ne peux pas terminer cette demande.", ephemeral=True)
        if not req["trainer_id"]:
            return await interaction.response.send_message("Aucun Helper/Formateur n’est assigné.", ephemeral=True)
        completed = await self.cog.bot.db.complete_request_once(req["id"])
        if completed is None:
            return await interaction.response.send_message("Cette demande a déjà été terminée ou n’est plus dans un état valide.", ephemeral=True)
        await self.cog.bot.db.complete_for_trainer(interaction.guild.id, completed["trainer_id"], completed["training_key"] == "community_help")
        student = interaction.guild.get_member(completed["user_id"])
        if student and completed["training_key"] != "community_help":
            certificate = discord.utils.get(interaction.guild.roles, name="✅・Apprenant certifié")
            if certificate:
                try:
                    await student.add_roles(certificate, reason="Formation Aide Bot terminée")
                except discord.Forbidden:
                    pass
        await self.cog.log_action(interaction.guild, "Demande terminée", f"#{req['id']} terminée par {interaction.user.mention}")
        await interaction.response.send_message("Demande terminée. Le membre peut maintenant laisser son avis.", view=ReviewView(self.cog))

    @discord.ui.button(label="Archiver", style=discord.ButtonStyle.danger, custom_id="aidebot:ticket:archive")
    async def archive(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            return
        req = await self._request(interaction)
        if not req:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        if interaction.user.id != req["user_id"] and not can(interaction.user, "training.manage"):
            return await interaction.response.send_message("Seul le client ou un responsable peut archiver ce ticket.", ephemeral=True)
        if not await self.cog.bot.db.close_request_once(req["id"]):
            return await interaction.response.send_message("La demande doit être terminée avant d’être archivée.", ephemeral=True)
        client = interaction.guild.get_member(req["user_id"])
        if client:
            try:
                await interaction.channel.set_permissions(client, view_channel=True, send_messages=False, read_message_history=True)
            except discord.Forbidden:
                pass
        try:
            await interaction.channel.edit(name=f"archive-{req['id']}")
        except discord.HTTPException:
            pass
        await self.cog.log_action(interaction.guild, "Ticket archivé", f"#{req['id']} archivé par {interaction.user.mention}")
        await interaction.response.send_message("Ticket archivé en lecture seule.", ephemeral=True)


class TrainingRequestModal(discord.ui.Modal):
    def __init__(self, cog: "TrainingCog", training_key: str) -> None:
        data = TRAINING_FORMS[training_key]
        super().__init__(title=data["title"][:45])
        self.cog = cog
        self.training_key = training_key
        self.inputs: dict[str, tuple[str, discord.ui.TextInput]] = {}
        for key, label, placeholder, style, required, max_length in data["fields"]:
            item = discord.ui.TextInput(
                label=label[:45],
                placeholder=placeholder[:100],
                style=style,
                required=required,
                max_length=max_length,
            )
            self.inputs[key] = (label, item)
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        data = FORMATIONS[self.training_key]
        if data["vip"] and not has_premium(interaction.user):
            return await interaction.response.send_message(missing_premium_message(), ephemeral=True)

        existing = await self.cog.bot.db.active_request_for_training(interaction.guild.id, interaction.user.id, self.training_key)
        if existing:
            channel = interaction.guild.get_channel(existing["channel_id"]) if existing["channel_id"] else None
            destination = channel.mention if isinstance(channel, discord.TextChannel) else f"demande #{existing['id']}"
            return await interaction.response.send_message(
                f"Tu as déjà une demande active pour cette formation : {destination}. Termine ou archive-la avant d’en ouvrir une autre.",
                ephemeral=True,
            )

        values = {key: str(item).strip() for key, (_label, item) in self.inputs.items()}
        detail_lines = []
        for key, (label, _item) in self.inputs.items():
            if key in {"level", "availability"}:
                continue
            value = values.get(key, "")
            if value:
                detail_lines.append(f"{label} : {value}")
        objective = "\n\n".join(detail_lines)[:2400] or "Objectif à préciser avec le Formateur."
        requires_invite = not data["vip"] and not can(interaction.user, "training.claim")
        await self.cog.create_request_channel(
            interaction,
            self.training_key,
            level=values.get("level", "Non précisé"),
            objective=objective,
            availability=values.get("availability", "Non précisé"),
            budget="Abonnement Premium actif" if data["vip"] else "Formation classique",
            status="open",
            payment_status="not_required",
            requires_invite=requires_invite,
        )


class PremiumPurchaseModal(discord.ui.Modal, title="Acheter Aide Bot Premium"):
    level = discord.ui.TextInput(
        label="Ton niveau actuel",
        placeholder="Débutant / intermédiaire / avancé",
        max_length=100,
    )
    project = discord.ui.TextInput(
        label="Ton projet",
        placeholder="Serveur, bot, sécurité, permissions...",
        style=discord.TextStyle.paragraph,
        max_length=600,
    )
    result = discord.ui.TextInput(
        label="Résultat attendu",
        placeholder="Qu’est-ce que tu veux avoir terminé à la fin ?",
        style=discord.TextStyle.paragraph,
        max_length=600,
    )
    availability = discord.ui.TextInput(
        label="Tes disponibilités",
        placeholder="Ex: mercredi 18h-20h",
        max_length=150,
    )
    payment_note = discord.ui.TextInput(
        label="Note paiement (optionnel)",
        placeholder="Pseudo/référence publique uniquement — jamais de mot de passe",
        required=False,
        max_length=180,
    )

    def __init__(self, cog: "TrainingCog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if has_premium(interaction.user):
            return await interaction.response.send_message(
                "Ton abonnement Premium est déjà actif. Utilise le bouton **Premium** dans le centre ou choisis une formation Premium.",
                ephemeral=True,
            )
        existing = await self.cog.bot.db.active_request_for_training(interaction.guild.id, interaction.user.id, "vip")
        if existing:
            channel = interaction.guild.get_channel(existing["channel_id"]) if existing["channel_id"] else None
            destination = channel.mention if isinstance(channel, discord.TextChannel) else f"demande #{existing['id']}"
            return await interaction.response.send_message(
                f"Tu as déjà un achat/abonnement Premium en cours : {destination}.",
                ephemeral=True,
            )
        objective = (
            f"Projet : {str(self.project).strip()}\n\n"
            f"Résultat attendu : {str(self.result).strip()}"
        )
        note = str(self.payment_note).strip()
        if note:
            objective += f"\n\nNote de paiement : {note}"
        await self.cog.create_request_channel(
            interaction,
            "vip",
            level=str(self.level),
            objective=objective,
            availability=str(self.availability),
            budget="Achat Premium depuis 🛒・shop",
            status="payment_pending",
            payment_status="pending",
            requires_invite=False,
        )


class TrainingSelect(discord.ui.Select):
    def __init__(self, cog: "TrainingCog") -> None:
        options = []
        for key, data in FORMATIONS.items():
            access = "Premium requis" if data["vip"] else data.get("difficulty", "Classique")
            description = f"{access} • {data.get('duration', 'Durée variable')} • {data['description']}"
            options.append(discord.SelectOption(label=data["title"][:100], value=key, description=description[:100]))
        super().__init__(
            placeholder="Choisis précisément la formation que tu veux",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:training:select",
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction) -> None:
        key = self.values[0]
        if not isinstance(interaction.user, discord.Member):
            return
        if FORMATIONS[key]["vip"] and not has_premium(interaction.user):
            return await interaction.response.send_message(missing_premium_message(), ephemeral=True)
        await interaction.response.send_modal(TrainingRequestModal(self.cog, key))


class TrainingPanel(discord.ui.View):
    def __init__(self, cog: "TrainingCog") -> None:
        super().__init__(timeout=None)
        self.add_item(TrainingSelect(cog))


class TrainingCog(commands.Cog, name="TrainingCog"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(TrainingPanel(self))
        self.bot.add_view(TicketActionsView(self))
        self.bot.add_view(ReviewView(self))

    async def log_action(self, guild: discord.Guild, title: str, description: str) -> None:
        channel = discord.utils.get(guild.text_channels, name="🧾・logs")
        if channel:
            try:
                await channel.send(embed=embed(title, description, 0x2B2D31))
            except discord.HTTPException:
                pass

    async def _rollback_creation(
        self,
        guild: discord.Guild,
        request_id: int,
        invite_used: bool,
        channel: discord.TextChannel | None = None,
    ) -> bool:
        result = await cancel_request_atomic(self.bot.db, request_id, refund_invite=invite_used)
        if channel is not None:
            try:
                await channel.delete(reason="Rollback création ticket Aide Bot")
            except discord.HTTPException:
                pass
        return result.refunded_invite

    async def create_request_channel(self, interaction: discord.Interaction, training_key: str, **fields) -> None:
        guild = interaction.guild
        assert guild is not None and isinstance(interaction.user, discord.Member)
        requires_invite = bool(fields.pop("requires_invite", False))
        fields.pop("invite_used", None)

        services = discord.utils.get(guild.categories, name="━━ SERVICES ━━")
        if not services:
            return await interaction.response.send_message("Le serveur n’est pas encore configuré. Lance `/setup`.", ephemeral=True)

        creation = await create_request_with_entitlement_atomic(
            self.bot.db,
            requires_invite=requires_invite,
            guild_id=guild.id,
            user_id=interaction.user.id,
            training_key=training_key,
            total_steps=len(FORMATIONS[training_key]["steps"]) if training_key in FORMATIONS else 1,
            level=str(fields.get("level", "")),
            objective=str(fields.get("objective", "")),
            availability=str(fields.get("availability", "")),
            budget=str(fields.get("budget", "")),
            status=str(fields.get("status", "open")),
            payment_status=str(fields.get("payment_status", "not_required")),
        )
        if creation.reason == "insufficient_credit":
            return await interaction.response.send_message(
                "La formation classique demande **1 invitation valide**. Ton solde est insuffisant.",
                ephemeral=True,
            )
        if creation.request_id is None:
            existing = creation.existing
            channel = guild.get_channel(existing["channel_id"]) if existing and existing["channel_id"] else None
            destination = channel.mention if isinstance(channel, discord.TextChannel) else f"demande #{existing['id']}" if existing else "une demande existante"
            return await interaction.response.send_message(
                f"Une demande identique est déjà active : {destination}. Aucun crédit n’a été perdu.",
                ephemeral=True,
            )

        request_id = creation.request_id
        invite_used = creation.invite_used
        staff_roles = [r for r in guild.roles if r.name in {"👑・Direction", "📘・Responsable Formation", "🎓・Formateur"}]
        if training_key == "community_help":
            helper = discord.utils.get(guild.roles, name="🤝・Helper")
            if helper:
                staff_roles.append(helper)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        for role in staff_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            channel = await guild.create_text_channel(
                f"ticket-{request_id}-{interaction.user.name}"[:95],
                category=services,
                overwrites=overwrites,
                reason="Nouvelle demande Aide Bot",
            )
        except (discord.Forbidden, discord.HTTPException):
            refunded = await self._rollback_creation(guild, request_id, invite_used)
            return await interaction.response.send_message(
                "Impossible de créer le ticket. La demande a été annulée proprement" + (" et ton invitation a été recréditée." if refunded else "."),
                ephemeral=True,
            )

        try:
            await self.bot.db.set_request_channel(request_id, channel.id)
        except Exception:
            await self._rollback_creation(guild, request_id, invite_used, channel)
            raise

        title = FORMATIONS.get(training_key, {"title": "Aide communautaire"})["title"]
        payment_status = str(fields.get("payment_status", "not_required"))
        status = str(fields.get("status", "open"))
        if payment_status == "pending":
            display_title = "Activation Premium"
        elif training_key == "community_help":
            display_title = "Aide gratuite"
        else:
            display_title = title

        ticket = discord.Embed(
            title=f"Ticket #{request_id} — {display_title}",
            description=(
                f"{interaction.user.mention}, ta demande est enregistrée. **Tout ce qu’il faut comprendre est regroupé dans ce message.** "
                "Le staff utilise les boutons ci-dessous pour la prendre en charge et suivre son avancement."
            ),
            color=0x9B59B6 if payment_status == "pending" else 0x5865F2,
        )
        objective = str(fields.get("objective", "-")).strip() or "Non précisé"
        ticket.add_field(name="Ta demande", value=objective[:1024], inline=False)
        ticket.add_field(
            name="Informations",
            value=(
                f"**Niveau :** {str(fields.get('level', '-'))[:180]}\n"
                f"**Disponibilités :** {str(fields.get('availability', '-'))[:180]}\n"
                f"**Formule :** {str(fields.get('budget', '-'))[:180]}"
            ),
            inline=True,
        )
        payment_label = "Inclus / non requis" if payment_status == "not_required" else PAYMENT_LABELS.get(payment_status, payment_status)
        ticket.add_field(
            name="État",
            value=f"**Ticket :** {_human_status(status)}\n**Paiement :** {payment_label}",
            inline=True,
        )
        guidance = format_guidance(training_key, 0)
        if guidance:
            ticket.add_field(name="Première étape", value=guidance[:1024], inline=False)
        if payment_status == "pending":
            next_text = (
                "1. La Direction vérifie le paiement avec les boutons **Paiement validé / refusé**.\n"
                "2. Si le paiement est validé, le rôle **💎・VIP** est ajouté automatiquement.\n"
                "3. Le ticket passe en état **Ouvert** et un Formateur peut cliquer sur **Prendre**.\n"
                "4. Aucun mot de passe, token ou code secret ne doit être envoyé."
            )
        else:
            next_text = (
                "1. Un membre autorisé clique sur **Prendre**.\n"
                "2. Il répond directement dans ce salon et avance les étapes avec **Étape suivante**.\n"
                "3. Quand l’objectif est atteint, il clique sur **Terminer** puis le ticket peut être archivé."
            )
        ticket.add_field(name="Ce qui se passe maintenant", value=next_text, inline=False)
        ticket.set_image(url=BANNER_URL)
        ticket.set_footer(text="Aide Bot • Un ticket = un responsable • Ne partage jamais de secret")

        try:
            await channel.send(embed=ticket, view=TicketActionsView(self), allowed_mentions=discord.AllowedMentions.none())
        except (discord.Forbidden, discord.HTTPException):
            refunded = await self._rollback_creation(guild, request_id, invite_used, channel)
            return await interaction.response.send_message(
                "Le ticket n’a pas pu être initialisé correctement. La création a été annulée" + (" et ton invitation a été recréditée." if refunded else "."),
                ephemeral=True,
            )

        await self.log_action(guild, "Nouvelle demande", f"#{request_id} • {title} • {interaction.user.mention}")
        await interaction.response.send_message(
            f"Ta demande est prête : {channel.mention}. Toutes les informations et les prochaines étapes sont dans le premier message.",
            ephemeral=True,
        )

    async def post_panel(self, channel: discord.TextChannel) -> None:
        text = (
            "Choisis une formation ci-dessous. **Chaque choix ouvre maintenant un formulaire adapté au sujet sélectionné** : "
            "les questions ne sont plus identiques pour Discord, serveur, permissions ou bot.\n\n"
            "Les formations classiques peuvent demander **1 invitation valide**. Les parcours Premium sont accessibles uniquement "
            "aux membres possédant le rôle **💎・VIP** ; l’abonnement s’achète dans `🛒・shop` ou avec `/buy`."
        )
        await channel.send(embed=embed("Aide Bot — Formations", text), view=TrainingPanel(self))

    formation = app_commands.Group(name="formation", description="Formations Aide Bot")

    @formation.command(name="catalogue", description="Voir les formations disponibles")
    async def catalogue(self, interaction: discord.Interaction) -> None:
        lines = []
        for data in FORMATIONS.values():
            suffix = " • Premium requis" if data["vip"] else " • 1 invitation valide"
            lines.append(f"**{data['title']}**{suffix}\n{data['description']}")
        await interaction.response.send_message(embed=embed("Catalogue", "\n\n".join(lines)), ephemeral=True)

    @formation.command(name="panneau", description="Publier le panneau des formations")
    async def panneau(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not can(interaction.user, "config.manage"):
            return await interaction.response.send_message("Accès refusé.", ephemeral=True)
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("Utilise cette commande dans un salon texte.", ephemeral=True)
        await self.post_panel(interaction.channel)
        await interaction.response.send_message("Panneau publié.", ephemeral=True)

    @formation.command(name="planifier", description="Planifier le rendez-vous du ticket actuel")
    @app_commands.describe(quand="Ex: samedi 18h")
    async def planifier(self, interaction: discord.Interaction, quand: str) -> None:
        if not interaction.channel or not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        req = await self.bot.db.request_by_channel(interaction.channel.id)
        if not req:
            return await interaction.response.send_message("Cette commande doit être utilisée dans un ticket.", ephemeral=True)
        if interaction.user.id != req["trainer_id"] and not can(interaction.user, "training.manage"):
            return await interaction.response.send_message("Seul le formateur assigné ou un responsable peut planifier.", ephemeral=True)
        await self.bot.db.update_request(req["id"], scheduled_for=quand)
        await self.log_action(interaction.guild, "Rendez-vous", f"#{req['id']} planifié : {quand} par {interaction.user.mention}")
        await interaction.response.send_message(f"Rendez-vous enregistré : **{quand}**.")

    @app_commands.command(name="tickets_auditer", description="Détecter les demandes actives dont le salon a disparu")
    @app_commands.describe(corriger="Annuler les demandes orphelines détectées")
    async def tickets_auditer(self, interaction: discord.Interaction, corriger: bool = False) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "training.manage"):
            return await interaction.response.send_message("Accès refusé : `training.manage` requis.", ephemeral=True)

        rows = await self.bot.db.active_requests_for_guild(interaction.guild.id)
        orphans: list[tuple[object, str]] = []
        for row in rows:
            if not row["channel_id"]:
                orphans.append((row, "aucun salon enregistré"))
                continue
            if interaction.guild.get_channel(row["channel_id"]) is None:
                orphans.append((row, "salon introuvable"))

        if not orphans:
            return await interaction.response.send_message(
                f"Audit terminé : **{len(rows)}** demande(s) active(s), aucun ticket orphelin.",
                ephemeral=True,
            )

        corrected = 0
        refunded = 0
        if corriger:
            for row, _reason in orphans:
                safe_refund = not row["channel_id"] and bool(row["invite_used"]) and not row["trainer_id"] and int(row["progress"]) == 0
                result = await cancel_request_atomic(self.bot.db, row["id"], refund_invite=safe_refund)
                if result.changed:
                    corrected += 1
                    if result.refunded_invite:
                        refunded += 1
            await self.log_action(
                interaction.guild,
                "Audit tickets",
                f"{corrected} demande(s) orpheline(s) annulée(s), {refunded} crédit(s) recrédité(s) par {interaction.user.mention}",
            )

        lines = [f"• **#{row['id']}** <@{row['user_id']}> — {reason}" for row, reason in orphans[:15]]
        suffix = "" if len(orphans) <= 15 else f"\n… et {len(orphans) - 15} autre(s)."
        action = f"\n\n**Corrigées :** {corrected} • **Crédits recrédités :** {refunded}" if corriger else "\n\nRelance avec `corriger:True` pour annuler les demandes orphelines."
        await interaction.response.send_message(
            embed=embed("Audit intégrité des tickets", f"**Orphelins détectés : {len(orphans)}**\n" + "\n".join(lines) + suffix + action, 0xF1C40F),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TrainingCog(bot))
