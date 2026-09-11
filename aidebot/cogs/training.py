from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.catalog import FORMATIONS
from aidebot.permissions import can, decide


def embed(title: str, description: str, color: int = 0x5865F2) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


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
            return await interaction.response.send_message("Cette formation VIP est encore en attente de confirmation du paiement.", ephemeral=True)
        capability = "help.claim" if req["training_key"] == "community_help" else "training.claim"
        decision = decide(interaction.user, capability)
        if not decision.allowed:
            roles = ", ".join(decision.allowed_roles) or "aucun"
            return await interaction.response.send_message(
                f"Accès refusé. Permission `{capability}`. Rôles autorisés : {roles}.",
                ephemeral=True,
            )
        if req["trainer_id"] and req["trainer_id"] != interaction.user.id:
            return await interaction.response.send_message(f"Déjà prise par <@{req['trainer_id']}>.", ephemeral=True)
        await self.cog.bot.db.update_request(req["id"], trainer_id=interaction.user.id, status="assigned")
        await self.cog.log_action(interaction.guild, "Demande prise", f"#{req['id']} prise par {interaction.user.mention}")
        await interaction.response.send_message(f"Demande prise par {interaction.user.mention}.")

    @discord.ui.button(label="Étape suivante", style=discord.ButtonStyle.secondary, custom_id="aidebot:ticket:progress")
    async def progress(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return
        req = await self._request(interaction)
        if not req:
            return await interaction.response.send_message("Demande introuvable.", ephemeral=True)
        if interaction.user.id != req["trainer_id"] and not can(interaction.user, "training.manage"):
            return await interaction.response.send_message("Seul le formateur assigné ou un responsable peut avancer la progression.", ephemeral=True)
        if req["status"] in {"completed", "closed"}:
            return await interaction.response.send_message("Cette demande est déjà terminée.", ephemeral=True)
        new_progress = min(req["progress"] + 1, req["total_steps"])
        await self.cog.bot.db.update_request(req["id"], progress=new_progress, status="in_progress")
        data = FORMATIONS.get(req["training_key"])
        next_label = "Terminé" if new_progress >= req["total_steps"] else (data["steps"][new_progress] if data and new_progress < len(data["steps"]) else "Étape suivante")
        await self.cog.log_action(interaction.guild, "Progression", f"#{req['id']} • {new_progress}/{req['total_steps']} par {interaction.user.mention}")
        await interaction.response.send_message(f"Progression : **{new_progress}/{req['total_steps']}** • prochain : **{next_label}**")

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
        if req["status"] in {"completed", "closed"}:
            return await interaction.response.send_message("Cette demande est déjà terminée.", ephemeral=True)
        await self.cog.bot.db.update_request(req["id"], status="completed", progress=req["total_steps"])
        await self.cog.bot.db.complete_for_trainer(interaction.guild.id, req["trainer_id"], req["training_key"] == "community_help")
        student = interaction.guild.get_member(req["user_id"])
        if student and req["training_key"] != "community_help":
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
        if req["status"] != "completed":
            return await interaction.response.send_message("Termine d’abord la demande avant de l’archiver.", ephemeral=True)
        await self.cog.bot.db.update_request(req["id"], status="closed")
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
    level = discord.ui.TextInput(label="Ton niveau", placeholder="Débutant / intermédiaire / avancé", max_length=80)
    objective = discord.ui.TextInput(label="Ton objectif", style=discord.TextStyle.paragraph, max_length=700)
    availability = discord.ui.TextInput(label="Tes disponibilités", placeholder="Ex: mercredi 18h-20h", max_length=150)
    budget = discord.ui.TextInput(label="Budget / formule", placeholder="Classique / VIP / à discuter", required=False, max_length=100)

    def __init__(self, cog: "TrainingCog", training_key: str) -> None:
        super().__init__(title=FORMATIONS[training_key]["title"][:45])
        self.cog = cog
        self.training_key = training_key

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        data = FORMATIONS[self.training_key]
        invite_used = False
        if not data["vip"] and not can(interaction.user, "training.claim"):
            invite_used = await self.cog.bot.db.consume_invite_credit(interaction.guild.id, interaction.user.id)
            if not invite_used:
                return await interaction.response.send_message("La formation classique demande **1 invitation valide**. Ton solde est insuffisant.", ephemeral=True)
        status = "payment_pending" if data["vip"] else "open"
        payment = "pending" if data["vip"] else "not_required"
        await self.cog.create_request_channel(
            interaction,
            self.training_key,
            level=str(self.level),
            objective=str(self.objective),
            availability=str(self.availability),
            budget=str(self.budget),
            status=status,
            payment_status=payment,
            invite_used=invite_used,
        )


class TrainingSelect(discord.ui.Select):
    def __init__(self, cog: "TrainingCog") -> None:
        options = [discord.SelectOption(label=v["title"], value=k, description=v["description"][:95]) for k, v in FORMATIONS.items()]
        super().__init__(
            placeholder="Choisis ce que tu veux apprendre",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:training:select",
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TrainingRequestModal(self.cog, self.values[0]))


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

    async def create_request_channel(self, interaction: discord.Interaction, training_key: str, **fields) -> None:
        guild = interaction.guild
        assert guild is not None and isinstance(interaction.user, discord.Member)
        services = discord.utils.get(guild.categories, name="━━ SERVICES ━━")
        if not services:
            return await interaction.response.send_message("Le serveur n’est pas encore configuré. Lance `/setup`.", ephemeral=True)
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
        request_id = await self.bot.db.create_request(
            guild_id=guild.id,
            user_id=interaction.user.id,
            training_key=training_key,
            total_steps=len(FORMATIONS[training_key]["steps"]) if training_key in FORMATIONS else 1,
            **fields,
        )
        try:
            channel = await guild.create_text_channel(
                f"ticket-{request_id}-{interaction.user.name}"[:95],
                category=services,
                overwrites=overwrites,
                reason="Nouvelle demande Aide Bot",
            )
        except discord.Forbidden:
            if fields.get("invite_used"):
                await self.bot.db.add_invite_credit(guild.id, interaction.user.id, 1)
            return await interaction.response.send_message("Le bot n’a pas la permission de créer le ticket. L’invitation utilisée a été recréditée.", ephemeral=True)
        await self.bot.db.set_request_channel(request_id, channel.id)
        title = FORMATIONS.get(training_key, {"title": "Aide communautaire"})["title"]
        desc = (
            f"Demande **#{request_id}** de {interaction.user.mention}\n"
            f"**Type :** {title}\n"
            f"**Niveau :** {fields.get('level', '-')}\n"
            f"**Objectif :** {fields.get('objective', '-')}\n"
            f"**Disponibilités :** {fields.get('availability', '-')}\n"
            f"**Statut :** `{fields.get('status', 'open')}`\n"
            f"**Paiement :** `{fields.get('payment_status', 'not_required')}`"
        )
        await channel.send(embed=embed("Nouvelle demande", desc), view=TicketActionsView(self))
        await self.log_action(guild, "Nouvelle demande", f"#{request_id} • {title} • {interaction.user.mention}")
        await interaction.response.send_message(f"Ta demande est créée : {channel.mention}", ephemeral=True)

    async def post_panel(self, channel: discord.TextChannel) -> None:
        text = (
            "Choisis une formation ci-dessous. Les formations classiques demandent **1 invitation valide**. "
            f"La formule VIP est actuellement configurée à **{self.bot.settings.vip_price_robux} Robux** et doit être confirmée manuellement par la Direction."
        )
        await channel.send(embed=embed("Aide Bot — Formations", text), view=TrainingPanel(self))

    formation = app_commands.Group(name="formation", description="Formations Aide Bot")

    @formation.command(name="catalogue", description="Voir les formations disponibles")
    async def catalogue(self, interaction: discord.Interaction) -> None:
        lines = []
        for data in FORMATIONS.values():
            suffix = f" • {self.bot.settings.vip_price_robux} Robux" if data["vip"] else " • 1 invitation valide"
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TrainingCog(bot))
