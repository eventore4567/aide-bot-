from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.catalog import FORMATIONS
from aidebot.cogs.training import TrainingRequestModal
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed
from aidebot.video_catalog import VIDEO_LIBRARY


COLOR = 0x5865F2
PREMIUM = 0x9B59B6
SUCCESS = 0x57F287


SUPPORT_TYPES = {
    "discord": {
        "label": "Discord / compte / interface",
        "description": "Réglages, rôles, salons, interface ou comportement Discord.",
        "level": ("Ton niveau sur Discord", "Débutant / intermédiaire / avancé"),
        "problem": ("Le problème exact", "Décris ce qui ne fonctionne pas, ce que tu vois et le résultat attendu."),
        "context": ("Contexte utile", "Appareil, salon/rôle concerné, réglage ou action effectuée."),
    },
    "serveur": {
        "label": "Serveur / permissions",
        "description": "Structure, permissions, rôles, catégories, staff ou sécurité.",
        "level": ("État du serveur", "Nouveau / existant / public / privé"),
        "problem": ("Ce que tu veux corriger", "Explique qui doit voir/faire quoi et ce qui ne marche pas aujourd’hui."),
        "context": ("Rôles / salons concernés", "Ex: @Membre, @Modo, catégorie Staff, salon tickets..."),
    },
    "bot": {
        "label": "Bot Discord / code",
        "description": "Python, discord.py, erreur, commande, DB ou déploiement.",
        "level": ("Ton niveau en code", "Aucun / bases Python / intermédiaire / avancé"),
        "problem": ("Erreur ou fonctionnalité", "Copie l’erreur utile ou décris précisément ce que le bot doit faire."),
        "context": ("Stack / hébergement", "Python, discord.py, Railway, GitHub, SQLite... ou aucun"),
    },
    "security": {
        "label": "Sécurité / raid / accès",
        "description": "Incident, permissions sensibles, bots, webhooks ou anti-raid.",
        "level": ("Contexte du serveur", "Taille, public/privé, rôle que tu occupes"),
        "problem": ("Risque ou incident", "Décris le problème sans envoyer de token, cookie, mot de passe ou code 2FA."),
        "context": ("Éléments concernés", "Rôles, bots, webhooks, salons, permissions, logs..."),
    },
    "other": {
        "label": "Autre demande",
        "description": "Une demande qui ne rentre pas clairement dans les catégories ci-dessus.",
        "level": ("Ton niveau / contexte", "Explique rapidement ta situation"),
        "problem": ("Ta demande", "Décris précisément ce que tu veux obtenir."),
        "context": ("Informations utiles", "Tout détail qui permettra au staff de comprendre plus vite."),
    },
}


VIDEO_CATEGORIES = {
    "discord": {
        "label": "Discord & serveur",
        "description": "Interface, rôles, permissions, onboarding et modération.",
        "keys": ("discord", "server", "roles", "permissions", "onboarding", "moderation"),
    },
    "bot": {
        "label": "Créer un bot",
        "description": "Developer Portal, Python, discord.py, slash commands et composants.",
        "keys": ("developer", "python", "bot", "slash", "components", "webhooks"),
    },
    "hosting": {
        "label": "Hébergement & données",
        "description": "Railway, stockage persistant, SQLite et déploiement.",
        "keys": ("railway", "sqlite", "deployment"),
    },
    "workflow": {
        "label": "GitHub & qualité",
        "description": "Git, GitHub, tests et CI/CD.",
        "keys": ("github", "tests", "actions"),
    },
    "support": {
        "label": "Support & sécurité",
        "description": "Tickets, anti-raid et bonnes pratiques de support.",
        "keys": ("tickets", "security", "support"),
    },
}


def _safe_video_keys(category: str) -> list[str]:
    wanted = VIDEO_CATEGORIES[category]["keys"]
    return [key for key in wanted if key in VIDEO_LIBRARY][:5]


def video_home_embed() -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Bibliothèque vidéo",
        description=(
            "Pas une liste de 20 boutons jetés au hasard. Choisis d’abord une **catégorie** : Aide Bot affiche ensuite seulement les vidéos utiles "
            "au sujet avec une explication claire de ce qu’elles vont t’apprendre.\n\n"
            "Les vidéos complètent les guides Aide Bot : elles montrent les écrans et manipulations, tandis que les guides expliquent la logique et la sécurité."
        ),
        color=0xE67E22,
    )
    for data in VIDEO_CATEGORIES.values():
        e.add_field(name=data["label"], value=data["description"], inline=True)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Catégorie → sélection courte → vidéo utile")
    return e


def video_category_embed(category: str) -> discord.Embed:
    data = VIDEO_CATEGORIES[category]
    keys = _safe_video_keys(category)
    e = discord.Embed(title=f"Vidéos — {data['label']}", description=data["description"], color=0xE67E22)
    if not keys:
        e.description += "\n\nAucune vidéo n’est encore référencée dans cette catégorie."
    for key in keys:
        video = VIDEO_LIBRARY[key]
        e.add_field(name=video["title"][:256], value=video["note"][:1024], inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Regarde, applique, puis vérifie avec le guide correspondant")
    return e


class VideoCategoryLinks(discord.ui.View):
    def __init__(self, category: str) -> None:
        super().__init__(timeout=900)
        for key in _safe_video_keys(category):
            video = VIDEO_LIBRARY[key]
            self.add_item(discord.ui.Button(label=video["title"][:80], url=video["url"], style=discord.ButtonStyle.link))


class VideoCategorySelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(label=data["label"], value=key, description=data["description"][:100])
            for key, data in VIDEO_CATEGORIES.items()
        ]
        super().__init__(
            placeholder="Choisis une catégorie vidéo",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:v43:videos:category",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        category = self.values[0]
        await interaction.response.send_message(
            embed=video_category_embed(category),
            view=VideoCategoryLinks(category),
            ephemeral=True,
        )


class VideoLibraryView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(VideoCategorySelect())


class SupportRequestModal(discord.ui.Modal):
    tried = discord.ui.TextInput(
        label="Ce que tu as déjà essayé",
        placeholder="Étapes testées, réglages changés, messages d’erreur observés...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=650,
    )
    availability = discord.ui.TextInput(
        label="Tes disponibilités",
        placeholder="Ex: aujourd’hui 18h-21h / samedi après-midi",
        max_length=140,
    )

    def __init__(self, bot: commands.Bot, support_type: str) -> None:
        data = SUPPORT_TYPES[support_type]
        super().__init__(title=data["label"][:45])
        self.bot = bot
        self.support_type = support_type
        self.level = discord.ui.TextInput(label=data["level"][0], placeholder=data["level"][1][:100], max_length=150)
        self.problem = discord.ui.TextInput(
            label=data["problem"][0],
            placeholder=data["problem"][1][:100],
            style=discord.TextStyle.paragraph,
            min_length=15,
            max_length=950,
        )
        self.context = discord.ui.TextInput(
            label=data["context"][0],
            placeholder=data["context"][1][:100],
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=550,
        )
        self.add_item(self.level)
        self.add_item(self.problem)
        self.add_item(self.context)
        self.add_item(self.tried)
        self.add_item(self.availability)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Le module de tickets est indisponible.", ephemeral=True)
        data = SUPPORT_TYPES[self.support_type]
        details = [
            f"**Catégorie :** {data['label']}",
            f"**Problème / objectif :** {str(self.problem).strip()}",
        ]
        context = str(self.context).strip()
        if context:
            details.append(f"**Contexte :** {context}")
        tried = str(self.tried).strip()
        if tried:
            details.append(f"**Déjà essayé :** {tried}")
        await training.create_request_channel(
            interaction,
            "community_help",
            level=str(self.level).strip(),
            objective="\n\n".join(details),
            availability=str(self.availability).strip(),
            budget="Aide gratuite",
            status="open",
            payment_status="not_required",
            requires_invite=False,
        )


class SupportTypeSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(label=data["label"], value=key, description=data["description"][:100])
            for key, data in SUPPORT_TYPES.items()
        ]
        super().__init__(
            placeholder="Quel type de problème veux-tu résoudre ?",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:v43:support:type",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(SupportRequestModal(self.bot, self.values[0]))


class TicketPortalView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(SupportTypeSelect(bot))

    @discord.ui.button(label="Mon accompagnement Premium", style=discord.ButtonStyle.success, custom_id="aidebot:v43:ticket:premium", row=1)
    async def premium(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_modal(TrainingRequestModal(training, "vip"))


async def member_space_embed(bot: commands.Bot, member: discord.Member) -> discord.Embed:
    premium = has_premium(member)
    e = discord.Embed(
        title=f"Mon espace — {member.display_name}",
        description=(
            "Ton tableau de bord personnel Aide Bot : accès Premium, demandes en cours et raccourcis utiles. "
            "Ce message est privé et visible uniquement par toi."
        ),
        color=PREMIUM if premium else COLOR,
    )
    e.add_field(
        name="Abonnement",
        value="💎 **Premium actif**" if premium else "**Gratuit** — Premium non activé",
        inline=True,
    )
    special = [name for name in ("🤝・Helper", "🎓・Formateur", "✅・Apprenant certifié") if discord.utils.get(member.roles, name=name)]
    e.add_field(name="Profil", value=" • ".join(special) if special else "Membre", inline=True)

    active = []
    for key in ("community_help", *FORMATIONS.keys()):
        try:
            req = await bot.db.active_request_for_training(member.guild.id, member.id, key)
        except Exception:
            req = None
        if not req:
            continue
        channel = member.guild.get_channel(req["channel_id"]) if req["channel_id"] else None
        destination = channel.mention if isinstance(channel, discord.TextChannel) else f"ticket #{req['id']}"
        title = "Aide gratuite" if key == "community_help" else FORMATIONS[key]["title"]
        active.append(f"• **{title}** → {destination}")
    e.add_field(
        name="Demandes en cours",
        value="\n".join(active[:6]) if active else "Aucune demande active. Tu peux ouvrir un ticket ou commencer une formation quand tu veux.",
        inline=False,
    )
    e.add_field(
        name="Où aller maintenant ?",
        value=(
            "`🎓・centre-aide` pour apprendre gratuitement • `🎓・formations` pour un parcours guidé • "
            "`🎫・ouvrir-ticket` pour un problème précis • `🛒・shop` pour Premium."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Mon espace • statut calculé au moment où tu cliques")
    return e


class ExperienceV43Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(VideoLibraryView())
        self.bot.add_view(TicketPortalView(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ExperienceV43Cog(bot))
