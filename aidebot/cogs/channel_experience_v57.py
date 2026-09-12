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

# Chaque salon permanent doit garder UNE mission visible et différente, y
# compris les deux espaces communautaires ajoutés plus tard.
CHANNEL_PURPOSES: dict[str, str] = {
    "👋・bienvenue": "Point d’entrée : commencer son parcours sur Aide Bot.",
    "📜・règlement": "Lire les règles puis valider son accès membre.",
    "📢・annonces": "Recevoir les nouveautés et gérer le rôle de notification.",
    "🎓・centre-aide": "Résoudre un problème : diagnostic, IA ou support humain.",
    "🎓・formations": "Choisir un parcours, apprendre et progresser.",
    "🤝・entraide": "Poser une question structurée et échanger dans un thread communautaire.",
    "📌・solutions": "Consulter l’archive en lecture seule des solutions communautaires validées.",
    "🛒・shop": "Consulter et acheter les offres Aide Bot.",
    "💎・espace-premium": "Utiliser les ressources et services réservés aux VIP.",
    "⭐・avis": "Noter une aide ou une formation réellement terminée.",
    "🧑‍🏫・recrutement": "Déposer et suivre une candidature staff.",
    "📋・staff": "Auditer, construire, personnaliser et sécuriser le serveur.",
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
        description="Ce salon sert uniquement de **journal des actions importantes**. Il n’y a aucun bouton d’administration ici.",
        color=0x95A5A6,
    )
    e.add_field(name="Lecture", value="Utilise ce journal pour comprendre qui a fait quoi et quand. Les actions se font depuis les panneaux dédiés.", inline=False)
    e.set_image(url=BANNER_URL)
    return e


def followup_embed_v57() -> discord.Embed:
    e = discord.Embed(
        title="Suivi formations — Aide Bot",
        description="Espace staff uniquement pour suivre les apprenants et l’avancement de leurs parcours.",
        color=COLOR,
    )
    e.add_field(name="Progression", value="Le panneau affiche les formations actives, l’élève, le statut et la progression disponible.", inline=False)
    e.set_image(url=BANNER_URL)
    return e


class RulesAckViewV57(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="J’ai lu le règlement", style=discord.ButtonStyle.success, custom_id="aidebot:v57:rules:ack")
    async def acknowledge(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        role = discord.utils.get(interaction.guild.roles, name=MEMBER_ROLE)
        if role is None:
            return await interaction.response.send_message("Le rôle membre n’est pas configuré. Un administrateur doit relancer `/setup`.", ephemeral=True)
        if role in interaction.user.roles:
            return await interaction.response.send_message("Ton accès membre est déjà validé.", ephemeral=True)
        me = interaction.guild.me
        if me is None or role >= me.top_role:
            return await interaction.response.send_message("Aide Bot ne peut pas attribuer le rôle membre à cause de la hiérarchie.", ephemeral=True)
        try:
            await interaction.user.add_roles(role, reason="Aide Bot — règlement validé")
        except (discord.Forbidden, discord.HTTPException):
            return await interaction.response.send_message("Impossible d’attribuer le rôle membre pour le moment.", ephemeral=True)
        await interaction.response.send_message("Règlement validé. Ton accès membre est actif.", ephemeral=True)


class AnnouncementPreferenceViewV57(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Notifications", style=discord.ButtonStyle.secondary, custom_id="aidebot:v57:announcements:toggle")
    async def toggle(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        role = discord.utils.get(interaction.guild.roles, name=NOTIFICATION_ROLE)
        if role is None:
            return await interaction.response.send_message("Le rôle Notifications n’est pas configuré. Relance `/setup`.", ephemeral=True)
        me = interaction.guild.me
        if me is None or role >= me.top_role:
            return await interaction.response.send_message("Aide Bot ne peut pas gérer ce rôle à cause de la hiérarchie.", ephemeral=True)
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role, reason="Aide Bot — notifications désactivées")
                message = "Notifications désactivées."
            else:
                await interaction.user.add_roles(role, reason="Aide Bot — notifications activées")
                message = "Notifications activées."
        except (discord.Forbidden, discord.HTTPException):
            return await interaction.response.send_message("Impossible de modifier ton rôle Notifications.", ephemeral=True)
        await interaction.response.send_message(message, ephemeral=True)


class ReviewsSelectV57(discord.ui.Select):
    def __init__(self, cog) -> None:
        self.cog = cog
        super().__init__(placeholder="Choisis une note", min_values=1, max_values=1, options=[discord.SelectOption(label=f"{n}/5", value=str(n)) for n in range(1, 6)])

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("L’avis sera lié à ta dernière demande terminée éligible.", ephemeral=True)


class ReviewsViewV57(discord.ui.View):
    def __init__(self, cog) -> None:
        super().__init__(timeout=None)
        self.add_item(ReviewsSelectV57(cog))


class TrainingFollowupViewV57(discord.ui.View):
    def __init__(self, cog) -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Actualiser le suivi", style=discord.ButtonStyle.secondary, custom_id="aidebot:v57:training:refresh")
    async def refresh(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message("Le suivi des formations est à jour.", ephemeral=True)


class ChannelExperienceV57Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(RulesAckViewV57())
        self.bot.add_view(AnnouncementPreferenceViewV57())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChannelExperienceV57Cog(bot))
