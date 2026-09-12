from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs.experience_v43 import SupportRequestModal, member_space_embed
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import missing_premium_embed, premium_member_embed
from aidebot.video_catalog import VIDEO_LIBRARY

COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F
PREMIUM = 0xEB459E


HELP_TOPICS = {
    "discord": {
        "label": "Discord : compte & interface",
        "description": "Réglages, interface, notifications, rôles visibles et problèmes courants.",
        "support_type": "discord",
        "video_key": "discord",
        "covers": "Compte Discord, interface PC/mobile, notifications, rôles visibles, accès aux salons et réglages de base.",
        "steps": (
            "Teste le problème sur navigateur ou téléphone pour savoir s’il vient de l’application.",
            "Vérifie le salon, le rôle et les permissions depuis un compte membre normal.",
            "Redémarre Discord et contrôle les paramètres concernés avant de modifier le serveur.",
        ),
        "mistakes": "Changer dix réglages en même temps, tester uniquement avec le propriétaire, ou donner Administrateur juste pour faire disparaître le problème.",
    },
    "server": {
        "label": "Créer / organiser un serveur",
        "description": "Catégories, salons, rôles, onboarding et structure claire.",
        "support_type": "serveur",
        "video_key": "onboarding",
        "covers": "Architecture du serveur, catégories, salons utiles, parcours membre, rôles, onboarding et lisibilité générale.",
        "steps": (
            "Définis le parcours d’un nouveau membre avant de créer des dizaines de salons.",
            "Sépare informations, communauté, support et staff avec une fonction claire par espace.",
            "Teste le serveur avec un compte membre pour vérifier ce qui est réellement visible.",
        ),
        "mistakes": "Trop de salons, permissions copiées au hasard, noms incompréhensibles et catégories qui n’ont aucun rôle précis.",
    },
    "permissions": {
        "label": "Rôles & permissions",
        "description": "Hiérarchie, catégories, overwrites et accès privés.",
        "support_type": "serveur",
        "video_key": "roles",
        "covers": "Permissions de rôle, permissions de catégorie/salon, hiérarchie, accès privés et conflits d’overwrites.",
        "steps": (
            "Commence par les permissions du rôle, puis regarde la catégorie, puis le salon.",
            "Vérifie la hiérarchie : un bot ou un rôle ne gère pas ce qui est placé au-dessus.",
            "Teste avec le membre exact qui rencontre le problème au lieu de te fier à la vue administrateur.",
        ),
        "mistakes": "Utiliser Administrateur comme correction, oublier un overwrite de salon ou placer le rôle du bot trop bas.",
    },
    "security": {
        "label": "Sécurité & anti-raid",
        "description": "Permissions sensibles, bots, webhooks, incidents et anti-raid.",
        "support_type": "security",
        "video_key": "security",
        "covers": "Audit de permissions sensibles, anti-raid, bots, webhooks, journal d’audit et réaction à un incident.",
        "steps": (
            "Repère qui possède Administrateur, Gérer les rôles, Gérer les webhooks et Gérer le serveur.",
            "Vérifie les bots et intégrations ajoutés récemment et conserve les logs utiles.",
            "Si un token ou secret a fuité, régénère-le immédiatement au lieu de le partager au staff.",
        ),
        "mistakes": "Envoyer un token dans un ticket, supprimer les preuves avant l’audit ou donner des permissions sensibles à des rôles inutiles.",
    },
    "moderation": {
        "label": "Modération & staff",
        "description": "Organisation du staff, sanctions, procédures et permissions.",
        "support_type": "serveur",
        "video_key": "moderation",
        "covers": "Hiérarchie staff, procédures, sanctions, permissions de modération, responsabilité et communication interne.",
        "steps": (
            "Définis précisément ce que chaque rôle staff peut faire et ce qu’il ne peut pas faire.",
            "Utilise des procédures courtes : preuve, action, motif, log et recours si nécessaire.",
            "Évite les permissions globales quand une permission ciblée suffit.",
        ),
        "mistakes": "Tous les staff Administrateur, sanctions sans preuve, rôles qui se chevauchent et procédures connues seulement par deux personnes.",
    },
    "tickets": {
        "label": "Tickets & support",
        "description": "Confidentialité, prise en charge, catégories et suivi.",
        "support_type": "serveur",
        "video_key": "tickets",
        "covers": "Ouverture de ticket, confidentialité, claim, transfert, fermeture, logs, formulaire et expérience membre.",
        "steps": (
            "Demande le contexte utile avant de créer le ticket.",
            "Fais qu’un seul staff soit responsable du suivi à la fois.",
            "Conserve un statut clair : ouvert, pris en charge, en attente, résolu ou fermé.",
        ),
        "mistakes": "Ticket vide, tout le staff ping, aucune attribution et fermeture sans résumé du résultat.",
    },
    "bot": {
        "label": "Créer un bot Discord",
        "description": "Developer Portal, Python, discord.py, intents et composants.",
        "support_type": "bot",
        "video_key": "developer-portal",
        "covers": "Application Discord, token, intents, Python, discord.py, slash commands, boutons, menus et modals.",
        "steps": (
            "Crée l’application dans le Developer Portal et configure seulement les intents nécessaires.",
            "Mets le token dans une variable d’environnement, jamais directement dans GitHub.",
            "Commence par une petite fonction testable avant d’ajouter tickets, économie et dashboard.",
        ),
        "mistakes": "Token dans le code, tout mettre dans un seul fichier, utiliser tous les intents sans raison et tester uniquement en production.",
    },
    "webhooks": {
        "label": "Embeds & webhooks",
        "description": "Annonces, logs, intégrations et sécurité des webhooks.",
        "support_type": "bot",
        "video_key": "webhooks",
        "covers": "Embeds lisibles, webhooks, annonces, logs, intégrations et protection des URLs de webhook.",
        "steps": (
            "Utilise un embed pour structurer l’information, pas pour mettre un mur de texte.",
            "Considère l’URL d’un webhook comme un secret : ne la publie pas.",
            "Sépare annonces publiques, logs techniques et messages internes.",
        ),
        "mistakes": "URL webhook publique, trop de champs, couleurs/format incohérents et logs impossibles à lire rapidement.",
    },
    "hosting": {
        "label": "Railway & hébergement",
        "description": "Déploiement, variables, logs, volume et redémarrages.",
        "support_type": "bot",
        "video_key": "railway",
        "covers": "Déploiement Railway, variables d’environnement, logs, commandes de démarrage, stockage persistant et redémarrages.",
        "steps": (
            "Vérifie le commit réellement déployé et la commande de démarrage.",
            "Lis la première erreur complète dans les logs plutôt que les dernières lignes au hasard.",
            "Si tu utilises SQLite, monte un volume persistant ou passe à une base externe.",
        ),
        "mistakes": "Modifier la prod sans PR, oublier le volume SQLite et croire qu’un statut BUILDING signifie que le bot est déjà connecté.",
    },
    "database": {
        "label": "Base de données",
        "description": "SQLite, PostgreSQL, persistance et concurrence.",
        "support_type": "bot",
        "video_key": "database",
        "covers": "Persistance, tables, transactions, SQLite, PostgreSQL, concurrence et sauvegarde des données.",
        "steps": (
            "Décide quelles données doivent survivre à un redéploiement avant de choisir le stockage.",
            "Utilise des transactions pour les actions sensibles : paiement, claim, progression ou économie.",
            "Teste les accès concurrents quand plusieurs boutons peuvent modifier la même donnée.",
        ),
        "mistakes": "SQLite sans volume, double validation d’un paiement et mises à jour non atomiques qui créent des doublons.",
    },
    "github": {
        "label": "GitHub, tests & CI",
        "description": "Branches, pull requests, pytest et GitHub Actions.",
        "support_type": "bot",
        "video_key": "github",
        "covers": "Git, branches, commits, pull requests, tests, CI, revue avant merge et déploiement sûr.",
        "steps": (
            "Travaille sur une branche dédiée et garde `main` stable.",
            "Ajoute un test qui reproduit le bug avant de le corriger quand c’est possible.",
            "Merge seulement après compilation, tests complets et vérification des changements.",
        ),
        "mistakes": "Push direct sur main, gros commit impossible à relire et déploiement avant la fin de la CI.",
    },
    "premium": {
        "label": "Premium & achat",
        "description": "Comprendre l’abonnement, le rôle VIP et ce qui est débloqué.",
        "support_type": "other",
        "video_key": None,
        "covers": "Achat Premium, validation, rôle 💎・VIP, formations avancées, vidéos Premium et accompagnement personnalisé.",
        "steps": (
            "Utilise uniquement `🛒・shop` ou `/buy` pour lancer un achat.",
            "Attends la validation enregistrée par la Direction avant de considérer l’abonnement actif.",
            "Une fois le rôle 💎・VIP ajouté, utilise l’espace Premium et ses ressources privées.",
        ),
        "mistakes": "Payer via un message privé non prévu, partager des informations sensibles ou croire qu’un simple ticket active automatiquement VIP.",
    },
    "recruitment": {
        "label": "Candidatures staff",
        "description": "Helper, Formateur, Expert Bots et Expert Sécurité.",
        "support_type": "other",
        "video_key": None,
        "covers": "Postes ouverts, attentes, questionnaire, cas pratique, disponibilités et traitement par le staff.",
        "steps": (
            "Choisis le poste qui correspond réellement à tes compétences.",
            "Réponds précisément aux questions et au cas pratique au lieu d’écrire seulement « je suis motivé ».",
            "Une candidature en attente doit être traitée avant d’en envoyer une nouvelle.",
        ),
        "mistakes": "Copier une réponse générique, mentir sur son expérience ou postuler à un rôle technique sans pouvoir expliquer sa méthode.",
    },
    "other": {
        "label": "Autre question",
        "description": "Tu ne sais pas où classer ton problème ? Commence ici.",
        "support_type": "other",
        "video_key": None,
        "covers": "Toute demande qui ne rentre pas clairement dans les catégories précédentes.",
        "steps": (
            "Écris le résultat exact que tu veux obtenir.",
            "Explique ce qui se passe actuellement et ce que tu as déjà essayé.",
            "Ajoute seulement les captures, erreurs et détails réellement utiles.",
        ),
        "mistakes": "Dire uniquement « ça marche pas », envoyer des secrets ou ouvrir plusieurs tickets pour le même problème.",
    },
}


def help_center_embed(vip_price: int) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Centre d’aide",
        description=(
            "Un **vrai centre d’aide**, pas une liste de commandes. Choisis directement ton sujet dans le menu : le bot t’explique ce que ça couvre, "
            "les premières vérifications, les erreurs à éviter et la prochaine action utile.\n\n"
            "Tu peux ensuite continuer avec une vidéo, une formation, un ticket, ton espace personnel, Premium ou une candidature staff."
        ),
        color=COLOR,
    )
    e.add_field(
        name="Aide immédiate",
        value="**13 sujets** : Discord, serveur, permissions, sécurité, modération, tickets, bots, webhooks, Railway, base de données, GitHub/CI, Premium et recrutement.",
        inline=False,
    )
    e.add_field(name="Apprendre", value="Guides + vidéos + formations structurées.", inline=True)
    e.add_field(name="Résoudre", value="Diagnostic ciblé puis ticket uniquement si nécessaire.", inline=True)
    e.add_field(name="Être accompagné", value="Support gratuit ou suivi Premium selon ton accès.", inline=True)
    e.add_field(name="Premium", value=f"Prix configuré : **{vip_price} Robux**. Achat uniquement via `🛒・shop` ou `/buy`.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V46 • Choisis ton sujet → comprends → vérifie → agis")
    return e


def help_topic_embed(topic: str) -> discord.Embed:
    data = HELP_TOPICS[topic]
    e = discord.Embed(
        title=f"Centre d’aide — {data['label']}",
        description=data["description"],
        color=COLOR,
    )
    e.add_field(name="Ce que cette aide couvre", value=data["covers"], inline=False)
    e.add_field(
        name="Commence par ça",
        value="\n".join(f"**{index}.** {step}" for index, step in enumerate(data["steps"], start=1)),
        inline=False,
    )
    e.add_field(name="Erreurs fréquentes", value=data["mistakes"], inline=False)
    e.add_field(
        name="Si tu bloques encore",
        value="Utilise **Ouvrir un ticket** : le formulaire reprend la bonne catégorie et demande le contexte nécessaire au staff.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V46 • Une réponse utile avant de créer un ticket")
    return e


class HelpTopicDetailView(discord.ui.View):
    def __init__(self, bot: commands.Bot, topic: str) -> None:
        super().__init__(timeout=900)
        self.bot = bot
        self.topic = topic
        data = HELP_TOPICS[topic]
        video_key = data.get("video_key")
        if video_key and video_key in VIDEO_LIBRARY:
            video = VIDEO_LIBRARY[video_key]
            self.add_item(
                discord.ui.Button(
                    label="Voir la vidéo liée",
                    url=video["url"],
                    style=discord.ButtonStyle.link,
                    row=1,
                )
            )

    @discord.ui.button(label="Ouvrir un ticket", style=discord.ButtonStyle.primary, row=0)
    async def ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        support_type = HELP_TOPICS[self.topic]["support_type"]
        await interaction.response.send_modal(SupportRequestModal(self.bot, support_type))

    @discord.ui.button(label="Voir les formations", style=discord.ButtonStyle.secondary, row=0)
    async def training(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.training_experience_v42 import V42TrainingPanel, training_catalog_embed

        cog = interaction.client.get_cog("TrainingCog")
        if cog is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_message(embed=training_catalog_embed(), view=V42TrainingPanel(cog), ephemeral=True)

    @discord.ui.button(label="Candidatures", style=discord.ButtonStyle.secondary, row=0)
    async def recruitment(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.recruitment_v46 import RecruitmentV46View, recruitment_v46_embed

        await interaction.response.send_message(
            embed=recruitment_v46_embed(),
            view=RecruitmentV46View(self.bot),
            ephemeral=True,
        )


class HelpTopicSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(
                label=data["label"][:100],
                value=key,
                description=data["description"][:100],
            )
            for key, data in HELP_TOPICS.items()
        ]
        super().__init__(
            placeholder="Choisis exactement ce que tu veux comprendre ou corriger",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:v46:help:topic",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        topic = self.values[0]
        await interaction.response.send_message(
            embed=help_topic_embed(topic),
            view=HelpTopicDetailView(self.bot, topic),
            ephemeral=True,
        )


class HelpCenterV46View(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(HelpTopicSelect(bot))

    @discord.ui.button(label="Formations", style=discord.ButtonStyle.primary, custom_id="aidebot:v46:center:training", row=1)
    async def training(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.training_experience_v42 import V42TrainingPanel, training_catalog_embed

        cog = interaction.client.get_cog("TrainingCog")
        if cog is None:
            return await interaction.response.send_message("Module de formations indisponible.", ephemeral=True)
        await interaction.response.send_message(embed=training_catalog_embed(), view=V42TrainingPanel(cog), ephemeral=True)

    @discord.ui.button(label="Support / Tickets", style=discord.ButtonStyle.success, custom_id="aidebot:v46:center:support", row=1)
    async def support(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.experience_v44 import SmartSupportView

        e = discord.Embed(
            title="Support — diagnostic avant ticket",
            description="Choisis ton problème. Aide Bot te donne d’abord une checklist ciblée, puis le formulaire adapté seulement si tu bloques encore.",
            color=SUCCESS,
        )
        await interaction.response.send_message(embed=e, view=SmartSupportView(self.bot), ephemeral=True)

    @discord.ui.button(label="Vidéos", style=discord.ButtonStyle.secondary, custom_id="aidebot:v46:center:videos", row=1)
    async def videos(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.experience_v43 import VideoLibraryView, video_home_embed

        await interaction.response.send_message(embed=video_home_embed(), view=VideoLibraryView(), ephemeral=True)

    @discord.ui.button(label="Candidatures", style=discord.ButtonStyle.secondary, custom_id="aidebot:v46:center:recruitment", row=1)
    async def recruitment(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        from aidebot.cogs.recruitment_v46 import RecruitmentV46View, recruitment_v46_embed

        await interaction.response.send_message(
            embed=recruitment_v46_embed(),
            view=RecruitmentV46View(self.bot),
            ephemeral=True,
        )

    @discord.ui.button(label="Premium", style=discord.ButtonStyle.secondary, custom_id="aidebot:v46:center:premium", row=1)
    async def premium(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            from aidebot.cogs.premium_v45 import PremiumHubView, premium_hub_embed

            return await interaction.response.send_message(
                embed=premium_hub_embed(),
                view=PremiumHubView(self.bot),
                ephemeral=True,
            )
        shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
        await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)

    @discord.ui.button(label="Mon espace", style=discord.ButtonStyle.secondary, custom_id="aidebot:v46:center:space", row=2)
    async def space(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        await interaction.response.send_message(embed=await member_space_embed(self.bot, interaction.user), ephemeral=True)

    @discord.ui.button(label="Statut Premium", style=discord.ButtonStyle.secondary, custom_id="aidebot:v46:center:premium-status", row=2)
    async def premium_status(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        if has_premium(interaction.user):
            return await interaction.response.send_message(embed=premium_member_embed(interaction.user), ephemeral=True)
        shop = discord.utils.get(interaction.guild.text_channels, name="🛒・shop") if interaction.guild else None
        await interaction.response.send_message(embed=missing_premium_embed(shop), ephemeral=True)
