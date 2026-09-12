from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.catalog import FORMATIONS
from aidebot.cogs.experience_v43 import VideoCategoryLinks, video_category_embed
from aidebot.cogs.training import TrainingRequestModal
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed


COLOR = 0x5865F2
PREMIUM = 0x9B59B6


OUTCOMES: dict[str, tuple[str, ...]] = {
    "discord": (
        "Comprendre l’interface Discord sans chercher au hasard",
        "Savoir à quoi servent salons, catégories, rôles et permissions",
        "Configurer les réglages importants et éviter les erreurs de sécurité",
    ),
    "serveur": (
        "Construire une architecture claire adaptée à ton projet",
        "Créer les bons rôles et les bonnes permissions",
        "Préparer onboarding, support, modération et vérification finale",
    ),
    "permissions": (
        "Comprendre la hiérarchie et les overwrites",
        "Diagnostiquer pourquoi un rôle ou un bot est bloqué",
        "Réduire les permissions dangereuses et sécuriser les espaces privés",
    ),
    "bot": (
        "Créer un bot Python/discord.py propre depuis zéro",
        "Comprendre token, intents, slash commands, embeds et permissions",
        "Déployer sans exposer de secret et garder les données persistantes",
    ),
    "vip": (
        "Faire diagnostiquer ton projet réel",
        "Obtenir un plan de travail personnalisé",
        "Être suivi jusqu’à un résultat vérifiable, pas juste recevoir une réponse",
    ),
    "serveur-pro": (
        "Refaire l’architecture complète d’un serveur réel",
        "Professionnaliser onboarding, tickets, logs et organisation staff",
        "Terminer par un audit complet et une checklist de lancement",
    ),
    "bot-avance": (
        "Structurer le bot en modules maintenables",
        "Fiabiliser base de données, erreurs, permissions, logs et tests",
        "Mettre en place un vrai workflow GitHub → CI → déploiement",
    ),
    "securite-avancee": (
        "Cartographier les rôles, bots, webhooks et accès sensibles",
        "Détecter les permissions et scénarios d’abus dangereux",
        "Créer une procédure anti-raid et un plan d’urgence clair",
    ),
}


VIDEO_CATEGORY_FOR_TRAINING = {
    "discord": "discord",
    "serveur": "discord",
    "permissions": "discord",
    "bot": "bot",
    "vip": "support",
    "serveur-pro": "discord",
    "bot-avance": "workflow",
    "securite-avancee": "support",
}


def training_catalog_embed() -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Choisis ton parcours",
        description=(
            "Ici, **chaque choix est réellement différent**. Sélectionne un parcours : Aide Bot affiche d’abord sa **fiche complète** "
            "avec niveau, durée, accès, programme, résultat attendu et ressources utiles. Tu décides ensuite si tu veux commencer.\n\n"
            "Les parcours **Premium** nécessitent `💎・VIP`. L’achat reste uniquement dans `🛒・shop` ou avec `/buy`."
        ),
        color=COLOR,
    )
    free = []
    premium = []
    for data in FORMATIONS.values():
        line = f"**{data['title']}** — {data.get('difficulty', 'Niveau variable')} • {data.get('duration', 'Durée variable')}"
        (premium if data["vip"] else free).append(line)
    e.add_field(name="Formations classiques", value="\n".join(free), inline=False)
    e.add_field(name="Parcours Premium", value="\n".join(premium), inline=False)
    e.add_field(
        name="Le parcours en 4 temps",
        value="**1. Fiche complète** → **2. Formulaire adapté** → **3. Ticket + responsable** → **4. Étapes + validation finale**",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V43 • Sélection → fiche → formulaire → suivi")
    return e


def training_preview_embed(key: str) -> discord.Embed:
    data = FORMATIONS[key]
    premium = bool(data["vip"])
    e = discord.Embed(title=data["title"], description=data["description"], color=PREMIUM if premium else COLOR)
    e.add_field(
        name="En un coup d’œil",
        value=(
            f"**Niveau :** {data.get('difficulty', 'Variable')}\n"
            f"**Durée indicative :** {data.get('duration', 'Variable')}\n"
            f"**Accès :** {'💎 Premium requis' if premium else 'Formation classique'}"
        ),
        inline=True,
    )
    e.add_field(
        name="Ce que tu vas obtenir",
        value="\n".join(f"• {item}" for item in OUTCOMES.get(key, ("Un parcours guidé et vérifié",))),
        inline=True,
    )
    steps = data.get("steps", [])
    e.add_field(
        name=f"Programme — {len(steps)} étapes",
        value="\n".join(f"**{index}.** {step}" for index, step in enumerate(steps, start=1))[:1024],
        inline=False,
    )
    e.add_field(
        name="Le formulaire sera adapté à CE parcours",
        value=(
            "Les questions changent selon le sujet : contexte, objectif, éléments concernés, blocage réel et disponibilités. "
            "Le staff reçoit donc un ticket exploitable dès le premier message."
        ),
        inline=False,
    )
    e.add_field(
        name="Avant de commencer",
        value=(
            "Prépare ton objectif précis, ce que tu as déjà essayé et les informations utiles. "
            + ("Ton rôle `💎・VIP` doit être actif." if premium else "Une invitation valide peut être nécessaire selon la configuration actuelle.")
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V43 • Lis la fiche, regarde les ressources si besoin, puis commence")
    return e


class TrainingPreviewView(discord.ui.View):
    def __init__(self, cog: commands.Cog, key: str) -> None:
        super().__init__(timeout=900)
        self.cog = cog
        self.key = key

    @discord.ui.button(label="Commencer ce parcours", style=discord.ButtonStyle.success)
    async def start(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        data = FORMATIONS[self.key]
        if data["vip"] and not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        await interaction.response.send_modal(TrainingRequestModal(self.cog, self.key))

    @discord.ui.button(label="Vidéos utiles", style=discord.ButtonStyle.primary)
    async def videos(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        category = VIDEO_CATEGORY_FOR_TRAINING.get(self.key, "support")
        await interaction.response.send_message(
            embed=video_category_embed(category),
            view=VideoCategoryLinks(category),
            ephemeral=True,
        )

    @discord.ui.button(label="Retour aux parcours", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=training_catalog_embed(), view=V42TrainingPanel(self.cog))


class V42TrainingSelect(discord.ui.Select):
    def __init__(self, cog: commands.Cog) -> None:
        options = []
        for key, data in FORMATIONS.items():
            access = "Premium" if data["vip"] else "Classique"
            options.append(
                discord.SelectOption(
                    label=data["title"][:100],
                    value=key,
                    description=f"{access} • {data.get('difficulty', 'Variable')} • {data.get('duration', 'Variable')}"[:100],
                )
            )
        super().__init__(
            placeholder="Choisis un parcours pour voir sa fiche complète",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:v42:training:select",
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction) -> None:
        key = self.values[0]
        if not isinstance(interaction.user, discord.Member):
            return
        if FORMATIONS[key]["vip"] and not has_premium(interaction.user):
            shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
            return await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
        await interaction.response.send_message(embed=training_preview_embed(key), view=TrainingPreviewView(self.cog, key), ephemeral=True)


class V42TrainingPanel(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=None)
        self.add_item(V42TrainingSelect(cog))
