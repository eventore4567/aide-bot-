from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.catalog import FORMATIONS
from aidebot.cogs.experience_v43 import SUPPORT_TYPES, _safe_video_keys, member_space_embed
from aidebot.cogs.training import TrainingRequestModal
from aidebot.experience_content import BANNER_URL, GUIDES
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed
from aidebot.video_catalog import VIDEO_LIBRARY

COLOR = 0x5865F2
SUCCESS = 0x57F287
PREMIUM = 0x9B59B6
WARNING = 0xF1C40F

SUPPORT_PREFLIGHT = {
    "discord": {
        "title": "Diagnostic rapide — Discord",
        "summary": "Avant d’ouvrir un ticket, vérifie les causes les plus fréquentes. Si ça ne règle rien, le bouton en bas ouvre le vrai formulaire Discord.",
        "checks": (
            "Redémarre Discord et vérifie si le problème existe aussi sur navigateur ou téléphone.",
            "Vérifie le salon, le rôle et les permissions visibles depuis un compte membre normal.",
            "Si une option semble absente, vérifie que ton compte possède bien la permission nécessaire.",
            "Pour un bot, vérifie aussi la hiérarchie de son rôle et les permissions du salon.",
        ),
        "video_category": "discord",
    },
    "serveur": {
        "title": "Diagnostic rapide — Serveur & permissions",
        "summary": "Les problèmes de serveur viennent souvent d’un rôle mal placé ou d’un overwrite contradictoire. Fais ces contrôles avant le ticket.",
        "checks": (
            "Teste le problème avec un rôle membre normal, pas uniquement avec le propriétaire.",
            "Vérifie d’abord les permissions du rôle, puis celles de la catégorie, puis celles du salon.",
            "Contrôle la hiérarchie : un rôle ou un bot ne peut pas gérer un rôle placé au-dessus de lui.",
            "Évite Administrateur pour corriger vite : identifie exactement la permission manquante.",
        ),
        "video_category": "discord",
    },
    "bot": {
        "title": "Diagnostic rapide — Bot & code",
        "summary": "Un bon ticket de code contient l’erreur exacte, l’étape qui casse et le résultat attendu. Vérifie ces points avant de l’ouvrir.",
        "checks": (
            "Lis la dernière erreur complète dans les logs et note le fichier + la ligne concernée.",
            "Vérifie les variables d’environnement, intents Discord et permissions du bot.",
            "Si ça marche en local mais pas en production, vérifie version Python, dépendances et stockage persistant.",
            "Ne colle jamais token, cookie, mot de passe ou secret dans le ticket.",
        ),
        "video_category": "bot",
    },
    "security": {
        "title": "Diagnostic rapide — Sécurité",
        "summary": "Pour un incident ou une permission dangereuse, évite toute action qui pourrait empirer la situation. Prépare les faits avant d’ouvrir le ticket.",
        "checks": (
            "Identifie les rôles/bots/webhooks concernés sans publier de secret.",
            "Vérifie les permissions Administrateur, Gérer les rôles, Gérer les webhooks et Gérer le serveur.",
            "Conserve les logs utiles et note l’heure de l’incident.",
            "Si un token a fuité, régénère-le immédiatement au lieu de l’envoyer au staff.",
        ),
        "video_category": "support",
    },
    "other": {
        "title": "Préparer une bonne demande",
        "summary": "Plus ton ticket est précis, plus le staff peut t’aider vite. Prépare ces quatre éléments avant de continuer.",
        "checks": (
            "Écris le résultat exact que tu veux obtenir.",
            "Explique ce qui se passe actuellement au lieu de dire seulement « ça marche pas ».",
            "Liste ce que tu as déjà essayé pour éviter de recommencer les mêmes étapes.",
            "Ajoute une capture ou une erreur seulement si elle apporte une information utile.",
        ),
        "video_category": "support",
    },
}

GUIDE_COLLECTIONS = {
    "start": {
        "label": "Bien démarrer",
        "description": "Discord, structure d’un serveur et bonnes pratiques de base.",
        "keys": ("discord", "serveur"),
    },
    "security": {
        "label": "Permissions & sécurité",
        "description": "Rôles, overwrites, hiérarchie et protection du serveur.",
        "keys": ("permissions", "tickets"),
    },
    "bot": {
        "label": "Créer un bot",
        "description": "Python, discord.py, déploiement, données et workflow propre.",
        "keys": ("bot",),
    },
}


def dashboard_embed(vip_price: int) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — ton tableau de bord",
        description=(
            "Un seul point d’entrée pour tout le service. **Tu choisis ce que tu veux faire, Aide Bot t’envoie directement au bon parcours.**\n\n"
            "Tu peux apprendre gratuitement, suivre une formation, diagnostiquer un problème avant d’ouvrir un ticket, regarder les vidéos utiles, "
            "consulter ton espace personnel ou utiliser Premium si ton abonnement est actif."
        ),
        color=COLOR,
    )
    e.add_field(name="Apprendre", value="Guides détaillés + exemples + erreurs fréquentes + vidéos liées.", inline=True)
    e.add_field(name="Résoudre", value="Diagnostic rapide d’abord, ticket seulement si nécessaire.", inline=True)
    e.add_field(name="Être accompagné", value="Formations guidées et parcours Premium selon ton accès.", inline=True)
    e.add_field(name="Premium", value=f"Abonnement configuré à **{vip_price} Robux**. Achat uniquement dans `🛒・shop` ou avec `/buy`.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V44 • Comprendre → choisir → agir → suivre le résultat")
    return e


def premium_compare_embed(price_robux: int) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot Premium — ce que tu achètes réellement",
        description=(
            "Premium ne sert pas à cacher les bases derrière un paiement. **Le gratuit reste utilisable.** "
            "Premium ajoute surtout du temps humain, du suivi personnalisé et les parcours avancés."
        ),
        color=PREMIUM,
    )
    e.add_field(name="Gratuit", value="• guides complets\n• bibliothèque vidéo\n• diagnostic avant ticket\n• aide communautaire\n• formations classiques selon les conditions du serveur\n• exemples et bonnes pratiques", inline=True)
    e.add_field(name=f"Premium — {price_robux} Robux", value="• rôle 💎・VIP après validation\n• Formateur / accompagnement dédié\n• audit serveur ou bot\n• parcours avancés\n• plan personnalisé\n• suivi jusqu’à un résultat vérifiable", inline=True)
    e.add_field(name="Activation propre", value="1. Achat depuis `🛒・shop` ou `/buy` uniquement.\n2. Ticket d’activation privé.\n3. La Direction valide le paiement.\n4. Le rôle **💎・VIP** est ajouté automatiquement.\n5. Les boutons Premium deviennent utilisables.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V44 • Le paiement débloque un accompagnement, pas les bases essentielles")
    return e


def support_preflight_embed(support_type: str) -> discord.Embed:
    data = SUPPORT_PREFLIGHT[support_type]
    e = discord.Embed(title=data["title"], description=data["summary"], color=WARNING)
    e.add_field(name="Checklist avant ticket", value="\n".join(f"**{i}.** {text}" for i, text in enumerate(data["checks"], start=1)), inline=False)
    e.add_field(name="Si le problème continue", value="Clique sur **Ouvrir le formulaire**. Les questions seront adaptées à cette catégorie et le ticket reprendra ton contexte proprement.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V44 • Vérifie d’abord • Ticket ensuite si nécessaire")
    return e


def guide_collection_embed(collection: str) -> discord.Embed:
    data = GUIDE_COLLECTIONS[collection]
    e = discord.Embed(title=f"Guides — {data['label']}", description=data["description"], color=SUCCESS)
    for key in data["keys"]:
        if key not in GUIDES:
            continue
        guide = GUIDES[key]
        e.add_field(name=guide["title"], value=guide["subtitle"], inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V44 • Choisis un guide précis dans le centre")
    return e


class SupportPreflightView(discord.ui.View):
    def __init__(self, bot: commands.Bot, support_type: str) -> None:
        super().__init__(timeout=900)
        self.bot = bot
        self.support_type = support_type
        category = SUPPORT_PREFLIGHT[support_type]["video_category"]
        keys = _safe_video_keys(category)
        if keys:
            video = VIDEO_LIBRARY[keys[0]]
            self.add_item(discord.ui.Button(label="Vidéo recommandée", style=discord.ButtonStyle.link, url=video["url"], row=1))

    @discord.ui.button(label="Ouvrir le formulaire", style=discord.ButtonStyle.primary, row=0)
    async def open_form(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.experience_v43 import SupportRequestModal
        await interaction.response.send_modal(SupportRequestModal(self.bot, self.support_type))

    @discord.ui.button(label="C’est résolu", style=discord.ButtonStyle.success, row=0)
    async def resolved(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=discord.Embed(title="Problème résolu", description="Parfait. Aucun ticket n’a été créé. Si le problème revient, recommence le diagnostic depuis le panneau Support.", color=SUCCESS), view=None)


class SmartSupportSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__(placeholder="Choisis ton problème — diagnostic avant ticket", min_values=1, max_values=1, custom_id="aidebot:v44:support:smart", options=[discord.SelectOption(label=data["label"], value=key, description=data["description"][:100]) for key, data in SUPPORT_TYPES.items()])

    async def callback(self, interaction: discord.Interaction) -> None:
        key = self.values[0]
        await interaction.response.send_message(embed=support_preflight_embed(key), view=SupportPreflightView(self.bot, key), ephemeral=True)


class SmartSupportView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(SmartSupportSelect(bot))

    @discord.ui.button(label="Mon accompagnement Premium", style=discord.ButtonStyle.success, custom_id="aidebot:v44:support:premium", row=1)
    async def premium(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_modal(TrainingRequestModal(training, "vip"))


class GuideCollectionSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(placeholder="Choisis une famille de guides", min_values=1, max_values=1, custom_id="aidebot:v44:guides:collection", options=[discord.SelectOption(label=data["label"], value=key, description=data["description"][:100]) for key, data in GUIDE_COLLECTIONS.items()])

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=guide_collection_embed(self.values[0]), ephemeral=True)


class DashboardView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(GuideCollectionSelect())

    @discord.ui.button(label="Formations", style=discord.ButtonStyle.primary, custom_id="aidebot:v44:dashboard:training", row=1)
    async def training(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.training_experience_v42 import V42TrainingPanel, training_catalog_embed
        cog = interaction.client.get_cog("TrainingCog")
        if cog is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_message(embed=training_catalog_embed(), view=V42TrainingPanel(cog), ephemeral=True)

    @discord.ui.button(label="Support intelligent", style=discord.ButtonStyle.success, custom_id="aidebot:v44:dashboard:support", row=1)
    async def support(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(embed=discord.Embed(title="Support — commence par le diagnostic", description="Choisis la catégorie de ton problème. Aide Bot te donne d’abord une checklist rapide, puis ouvre un formulaire adapté seulement si tu en as encore besoin.", color=COLOR), view=SmartSupportView(self.bot), ephemeral=True)

    @discord.ui.button(label="Vidéos", style=discord.ButtonStyle.secondary, custom_id="aidebot:v44:dashboard:videos", row=1)
    async def videos(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.experience_v43 import VideoLibraryView, video_home_embed
        await interaction.response.send_message(embed=video_home_embed(), view=VideoLibraryView(), ephemeral=True)

    @discord.ui.button(label="Mon espace", style=discord.ButtonStyle.secondary, custom_id="aidebot:v44:dashboard:space", row=2)
    async def space(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=await member_space_embed(self.bot, interaction.user), ephemeral=True)

    @discord.ui.button(label="Premium", style=discord.ButtonStyle.secondary, custom_id="aidebot:v44:dashboard:premium", row=2)
    async def premium(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            return await interaction.response.send_message(embed=premium_member_embed(interaction.user), ephemeral=True)
        await interaction.response.send_message(embed=premium_compare_embed(self.bot.settings.vip_price_robux), ephemeral=True)


class ExperienceV44Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(DashboardView(self.bot))
        self.bot.add_view(SmartSupportView(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ExperienceV44Cog(bot))
