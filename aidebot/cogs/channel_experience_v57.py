from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs.setup_experience_v55 import SetupExperienceV55Cog
from aidebot.experience_content import BANNER_URL

COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F
NOTIFICATION_ROLE = "🔔・Notifications"
MEMBER_ROLE = "👤・Membre"

# V57 : chaque salon permanent doit avoir UNE mission visible et différente.
CHANNEL_PURPOSES: dict[str, str] = {
    "👋・bienvenue": "Point d’entrée : commencer son parcours sur Aide Bot.",
    "📜・règlement": "Lire les règles puis valider son accès membre.",
    "📢・annonces": "Recevoir les nouveautés et gérer le rôle de notification.",
    "🎓・centre-aide": "Résoudre un problème : diagnostic, IA ou support humain.",
    "🎓・formations": "Choisir un parcours, apprendre et progresser.",
    "🛒・shop": "Consulter et acheter les offres Aide Bot.",
    "💎・espace-premium": "Utiliser les ressources et services réservés aux VIP.",
    "⭐・avis": "Noter une aide ou une formation réellement terminée.",
    "🧑‍🏫・recrutement": "Déposer et suivre une candidature staff.",
    "📋・staff": "Gérer la sécurité du serveur avec Guardian.",
    "🧾・logs": "Consulter la trace automatique des actions importantes.",
    "🧠・suivi-formations": "Voir les formations actives et leur progression.",
}


def rules_embed_v57() -> discord.Embed:
    e = discord.Embed(
        title="Règlement — Aide Bot",
        description=(
            "Ce salon sert uniquement aux **règles et à la validation d’accès**.\n\n"
            "**Respect** — pas d’insultes, harcèlement, spam ou contenu nuisible.\n"
            "**Sécurité** — ne partage jamais token, mot de passe, cookie, 2FA ou code de récupération.\n"
            "**Support** — une demande précise par problème ; utilise le Centre d’aide avant d’escalader.\n"
            "**Paiement** — les achats passent uniquement par `🛒・shop`.\n"
            "**Staff** — aucune action sensible ne doit être faite sans les permissions nécessaires."
        ),
        color=0x2B2D31,
    )
    e.add_field(
        name="Validation",
        value="Après lecture, clique sur **J’ai lu le règlement**. Le bot vérifie puis ajoute le rôle membre si nécessaire.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Règlement = règles + validation • aucune autre fonction ici")
    return e


def announcements_embed_v57() -> discord.Embed:
    e = discord.Embed(
        title="Annonces — Aide Bot",
        description=(
            "Ce salon sert uniquement aux **nouveautés importantes** : mises à jour, maintenance, nouvelles formations et changements de service.\n\n"
            "Tu peux activer ou retirer le rôle **🔔・Notifications** avec le bouton ci-dessous."
        ),
        color=COLOR,
    )
    e.add_field(
        name="Pas de spam",
        value="Le rôle est optionnel. Les annonces restent visibles même si tu ne souhaites pas être notifié.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Annonces = informations officielles + préférence de notification")
    return e


def reviews_embed_v57() -> discord.Embed:
    e = discord.Embed(
        title="Avis vérifiés — Aide Bot",
        description=(
            "Ici, on ne poste pas des messages au hasard. Tu peux noter uniquement une **aide ou une formation terminée** qui t’appartient.\n\n"
            "Choisis une note : Aide Bot retrouve automatiquement ta dernière demande terminée non notée, puis te demande un commentaire."
        ),
        color=0xFEE75C,
    )
    e.add_field(
        name="Avis liés à une vraie demande",
        value="Chaque avis est rattaché à un ticket terminé et ne peut être enregistré qu’une fois.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Avis = retour après service terminé • pas un deuxième salon support")
    return e


def logs_embed_v57() -> discord.Embed:
    e = discord.Embed(
        title="Journal automatique — Aide Bot",
        description=(
            "Ce salon est un **journal**, pas un panneau de commandes. Il reçoit les événements importants générés par Aide Bot : "
            "setup, sécurité, tickets, paiements, changements critiques et alertes Guardian."
        ),
        color=0x2B2D31,
    )
    e.add_field(
        name="Pourquoi aucun bouton ?",
        value="Les actions se font dans leur salon dédié. Ici on garde uniquement une trace chronologique claire pour le staff.",
        inline=False,
    )
    e.set_footer(text="Logs = historique seulement • aucune action dupliquée")
    return e


def followup_embed_v57() -> discord.Embed:
    e = discord.Embed(
        title="Suivi des formations — Aide Bot",
        description=(
            "Ce salon sert uniquement au **suivi pédagogique interne**. Il ne remplace ni le Centre d’aide, ni les tickets, ni le catalogue de formations."
        ),
        color=0x3498DB,
    )
    e.add_field(
        name="Vue active",
        value="Le bouton affiche les formations actuellement ouvertes avec l’élève, l’état et la progression enregistrée.",
        inline=False,
    )
    e.set_footer(text="Suivi = progression des apprenants • réservé au staff")
    return e


class RulesAckViewV57(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="J’ai lu le règlement",
        style=discord.ButtonStyle.success,
        custom_id="aidebot:v57:rules:ack",
    )
    async def acknowledge(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        role = discord.utils.get(interaction.guild.roles, name=MEMBER_ROLE)
        if role is None:
            return await interaction.response.send_message(
                "Le rôle membre n’est pas encore configuré. Un administrateur doit relancer `/setup`.",
                ephemeral=True,
            )
        if role in interaction.user.roles:
            return await interaction.response.send_message("Tu as déjà validé le règlement.", ephemeral=True)
        try:
            await interaction.user.add_roles(role, reason="Aide Bot — règlement accepté")
        except (discord.Forbidden, discord.HTTPException):
            return await interaction.response.send_message(
                "Je ne peux pas attribuer le rôle membre. Vérifie la hiérarchie du rôle Aide Bot.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            "Règlement validé. Ton rôle **👤・Membre** est maintenant actif.",
            ephemeral=True,
        )


class AnnouncementPreferenceViewV57(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Activer / retirer les notifications",
        style=discord.ButtonStyle.secondary,
        custom_id="aidebot:v57:announcements:toggle",
    )
    async def toggle(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        role = discord.utils.get(interaction.guild.roles, name=NOTIFICATION_ROLE)
        if role is None:
            return await interaction.response.send_message(
                "Le rôle de notification n’est pas encore prêt. Un administrateur doit relancer `/setup`.",
                ephemeral=True,
            )
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role, reason="Aide Bot — notifications désactivées")
                text = "Notifications désactivées. Tu ne seras plus ping via ce rôle."
            else:
                await interaction.user.add_roles(role, reason="Aide Bot — notifications activées")
                text = "Notifications activées. Tu recevras les annonces qui utilisent **🔔・Notifications**."
        except (discord.Forbidden, discord.HTTPException):
            return await interaction.response.send_message(
                "Impossible de modifier le rôle de notification. Vérifie la hiérarchie des rôles.",
                ephemeral=True,
            )
        await interaction.response.send_message(text, ephemeral=True)


class ReviewCommentModalV57(discord.ui.Modal, title="Donner un avis"):
    comment = discord.ui.TextInput(
        label="Ton retour",
        placeholder="Qu’est-ce qui t’a aidé ? Qu’est-ce qui pourrait être amélioré ?",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=600,
    )

    def __init__(self, cog: "ChannelExperienceV57Cog", *, request_id: int, trainer_id: int, rating: int) -> None:
        super().__init__()
        self.cog = cog
        self.request_id = int(request_id)
        self.trainer_id = int(trainer_id)
        self.rating = int(rating)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        ok = await self.cog.bot.db.add_review(
            interaction.guild.id,
            self.request_id,
            interaction.user.id,
            self.trainer_id,
            self.rating,
            str(self.comment).strip(),
        )
        if not ok:
            return await interaction.response.send_message(
                "Cet avis n’est plus disponible : la demande n’est pas terminée, ne t’appartient pas ou a déjà été notée.",
                ephemeral=True,
            )

        channel = discord.utils.get(interaction.guild.text_channels, name="⭐・avis")
        if channel is not None:
            stars = "★" * self.rating + "☆" * (5 - self.rating)
            e = discord.Embed(
                title=f"Avis vérifié • {stars}",
                description=str(self.comment).strip(),
                color=0xFEE75C,
            )
            e.add_field(name="Membre", value=interaction.user.mention, inline=True)
            e.add_field(name="Pris en charge par", value=f"<@{self.trainer_id}>", inline=True)
            e.set_footer(text=f"Demande #{self.request_id} • avis lié à un service terminé")
            try:
                await channel.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
            except (discord.Forbidden, discord.HTTPException):
                pass
        await interaction.response.send_message("Merci. Ton avis vérifié a été enregistré.", ephemeral=True)


class ReviewRatingSelectV57(discord.ui.Select):
    def __init__(self, cog: "ChannelExperienceV57Cog") -> None:
        self.cog = cog
        super().__init__(
            placeholder="Noter ma dernière aide terminée",
            min_values=1,
            max_values=1,
            custom_id="aidebot:v57:reviews:rating",
            options=[
                discord.SelectOption(label=f"{rating}/5", value=str(rating), description=label)
                for rating, label in (
                    (1, "Très décevant"),
                    (2, "À améliorer"),
                    (3, "Correct"),
                    (4, "Très bien"),
                    (5, "Excellent"),
                )
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        request = await self.cog.latest_reviewable_request(interaction.guild.id, interaction.user.id)
        if request is None:
            return await interaction.response.send_message(
                "Tu n’as aucune aide/formation terminée et non notée pour le moment.",
                ephemeral=True,
            )
        await interaction.response.send_modal(
            ReviewCommentModalV57(
                self.cog,
                request_id=int(request["id"]),
                trainer_id=int(request["trainer_id"]),
                rating=int(self.values[0]),
            )
        )


class ReviewsViewV57(discord.ui.View):
    def __init__(self, cog: "ChannelExperienceV57Cog") -> None:
        super().__init__(timeout=None)
        self.add_item(ReviewRatingSelectV57(cog))


class TrainingFollowupViewV57(discord.ui.View):
    def __init__(self, cog: "ChannelExperienceV57Cog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    def _staff(self, member: discord.Member) -> bool:
        allowed = {"👑・Direction", "📘・Responsable Formation", "🎓・Formateur"}
        return member.guild_permissions.administrator or any(role.name in allowed for role in member.roles)

    @discord.ui.button(
        label="Voir les formations actives",
        style=discord.ButtonStyle.primary,
        custom_id="aidebot:v57:training:active",
    )
    async def active(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not self._staff(interaction.user):
            return await interaction.response.send_message("Ce suivi est réservé à l’équipe formation.", ephemeral=True)
        rows = await self.cog.bot.db.active_requests_for_guild(interaction.guild.id, limit=100)
        rows = [row for row in rows if str(row["training_key"]) != "community_help"]
        e = discord.Embed(title="Formations actives", color=0x3498DB)
        if not rows:
            e.description = "Aucune formation active actuellement."
        else:
            lines = []
            for row in rows[:15]:
                progress = f"{int(row['progress'])}/{int(row['total_steps'])}"
                lines.append(
                    f"• **#{int(row['id'])}** <@{int(row['user_id'])}> — `{row['training_key']}` — **{row['status']}** — {progress}"
                )
            e.description = "\n".join(lines)
            if len(rows) > 15:
                e.set_footer(text=f"{len(rows) - 15} autre(s) formation(s) active(s)")
        await interaction.response.send_message(embed=e, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


class ChannelExperienceV57Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._patched = False

    async def cog_load(self) -> None:
        self.bot.add_view(RulesAckViewV57())
        self.bot.add_view(AnnouncementPreferenceViewV57())
        self.bot.add_view(ReviewsViewV57(self))
        self.bot.add_view(TrainingFollowupViewV57(self))
        self._patch_setup_pipeline()

    async def latest_reviewable_request(self, guild_id: int, user_id: int):
        cur = await self.bot.db._db().execute(
            """SELECT r.*
               FROM requests AS r
               LEFT JOIN reviews AS v
                 ON v.guild_id=r.guild_id AND v.request_id=r.id AND v.author_id=r.user_id
               WHERE r.guild_id=?
                 AND r.user_id=?
                 AND r.trainer_id IS NOT NULL
                 AND r.status IN ('completed','closed')
                 AND v.request_id IS NULL
               ORDER BY r.id DESC
               LIMIT 1""",
            (guild_id, user_id),
        )
        return await cur.fetchone()

    async def _ensure_notification_role(self, guild: discord.Guild) -> discord.Role | None:
        role = discord.utils.get(guild.roles, name=NOTIFICATION_ROLE)
        if role is not None:
            return role
        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            return None
        try:
            return await guild.create_role(
                name=NOTIFICATION_ROLE,
                colour=discord.Colour(0x99AAB5),
                reason="Aide Bot V57 — notifications opt-in",
            )
        except (discord.Forbidden, discord.HTTPException):
            return None

    async def _upsert(self, channel: discord.TextChannel | None, embed: discord.Embed, view: discord.ui.View | None = None) -> str:
        if channel is None:
            return "absent"
        base = self.bot.get_cog("SetupServerCog")
        if base is None:
            return "absent"
        return await base._upsert_panel(channel, embed, view)

    async def _apply_topics(self, guild: discord.Guild) -> None:
        for name, purpose in CHANNEL_PURPOSES.items():
            channel = discord.utils.get(guild.text_channels, name=name)
            if channel is None or channel.topic == purpose:
                continue
            try:
                await channel.edit(topic=purpose, reason="Aide Bot V57 — fonction unique par salon")
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def _reconcile_unique_panels(
        self,
        guild: discord.Guild,
        channels: dict[str, discord.TextChannel] | None = None,
    ) -> list[tuple[str, str]]:
        await self._ensure_notification_role(guild)
        await self._apply_topics(guild)
        mapping = channels or {channel.name: channel for channel in guild.text_channels}
        actions: list[tuple[str, str]] = []
        actions.append(("Règlement interactif", await self._upsert(mapping.get("📜・règlement"), rules_embed_v57(), RulesAckViewV57())))
        actions.append(("Préférences annonces", await self._upsert(mapping.get("📢・annonces"), announcements_embed_v57(), AnnouncementPreferenceViewV57())))
        actions.append(("Avis vérifiés", await self._upsert(mapping.get("⭐・avis"), reviews_embed_v57(), ReviewsViewV57(self))))
        actions.append(("Journal", await self._upsert(mapping.get("🧾・logs"), logs_embed_v57())))
        actions.append(("Suivi formations", await self._upsert(mapping.get("🧠・suivi-formations"), followup_embed_v57(), TrainingFollowupViewV57(self))))
        return actions

    def _patch_setup_pipeline(self) -> None:
        if getattr(SetupExperienceV55Cog, "_aidebot_v57_channel_identity", False):
            return
        original_publish = SetupExperienceV55Cog._publish_panels

        async def publish(setup_self, guild, channels, roles):
            actions = await original_publish(setup_self, guild, channels, roles)
            cog = setup_self.bot.get_cog("ChannelExperienceV57Cog")
            if cog is not None:
                actions.extend(await cog._reconcile_unique_panels(guild, channels))
            return actions

        SetupExperienceV55Cog._publish_panels = publish
        SetupExperienceV55Cog._aidebot_v57_channel_identity = True

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            await self._reconcile_unique_panels(guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.TextChannel):
            return
        if channel.name in CHANNEL_PURPOSES:
            await self._reconcile_unique_panels(channel.guild)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChannelExperienceV57Cog(bot))
