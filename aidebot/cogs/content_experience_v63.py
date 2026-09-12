from __future__ import annotations

import discord
from discord.ext import commands

import aidebot.cogs.enterprise_academy_v61 as academy_v61
import aidebot.cogs.experience_v56 as help_v56
import aidebot.cogs.premium_v45 as premium_v45
import aidebot.cogs.simple_help_v62 as simple_v62
from aidebot.content_catalog_v63 import (
    PREMIUM_CATEGORIES,
    free_resources,
    premium_resources,
)
from aidebot.experience_content import BANNER_URL

COLOR = 0x5865F2
PREMIUM = 0xEB459E
SUCCESS = 0x57F287


def quick_setup_embed_v63(guild: discord.Guild | None = None) -> discord.Embed:
    embed = discord.Embed(
        title="Aide Bot — Installer sur ce serveur",
        description=(
            "La configuration recommandée tient en **un clic**. Aide Bot analyse l’existant, réutilise ce qui est déjà propre "
            "et complète uniquement ce qui manque."
        ),
        color=COLOR,
    )
    embed.add_field(
        name="Recommandé — Installer automatiquement",
        value="Profil Général + thème Clean + aide + Academy + communauté + sécurité. Tu pourras personnaliser ensuite.",
        inline=False,
    )
    embed.add_field(
        name="Personnaliser",
        value="Pour choisir toi-même un profil ou un thème avant l’installation.",
        inline=True,
    )
    embed.add_field(
        name="Vérifier",
        value="Audit du serveur sans créer ni modifier quoi que ce soit.",
        inline=True,
    )
    if guild is not None:
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
    embed.set_footer(text="Aide Bot • simple par défaut • avancé seulement quand tu en as besoin")
    return embed


def instant_help_embed_v63(ai_ready: bool) -> discord.Embed:
    embed = discord.Embed(
        title="Aide Bot — Besoin d’aide ?",
        description=(
            "Écris simplement **@Aide Bot + ta question** dans ce salon. Je te réponds directement et je t’oriente vers "
            "la bonne solution si le problème demande un guide, un ticket ou une formation."
        ),
        color=COLOR,
    )
    embed.add_field(
        name="Exemple",
        value="`@Aide Bot pourquoi mon rôle ne voit pas le salon staff ?`",
        inline=False,
    )
    embed.add_field(
        name="Aide guidée",
        value="Problèmes fréquents, vérifications dans l’ordre et support humain si nécessaire.",
        inline=True,
    )
    embed.add_field(
        name="Assistant IA",
        value="Prêt à répondre." if ai_ready else "Indisponible actuellement — l’aide guidée reste disponible.",
        inline=True,
    )
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Aide Bot • pose ta question normalement • aucune commande à retenir")
    return embed


def help_hub_embed_v63() -> discord.Embed:
    embed = discord.Embed(
        title="Aide Bot — Centre d’aide",
        description=(
            "Dis-moi ce qui bloque. Aide Bot commence par la solution la plus simple, puis passe à l’IA ou au support humain "
            "uniquement si c’est utile."
        ),
        color=COLOR,
    )
    embed.add_field(
        name="Résoudre maintenant",
        value="Diagnostic guidé avec vérifications et correction dans le bon ordre.",
        inline=True,
    )
    embed.add_field(
        name="Question libre",
        value="L’IA traite les cas inhabituels et explique la cause, pas seulement la réponse.",
        inline=True,
    )
    embed.add_field(
        name="Besoin d’un humain ?",
        value="Le ticket reprend ton contexte pour éviter de tout réexpliquer au staff.",
        inline=False,
    )
    embed.add_field(
        name="Ressources",
        value="Les membres normaux ont les liens essentiels et quelques vidéos utiles. Les parcours avancés restent dans l’espace Premium.",
        inline=False,
    )
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Aide Bot • comprendre → corriger → vérifier")
    return embed


def academy_home_embed_v63() -> discord.Embed:
    fr = free_resources("fr")
    en = free_resources("en")
    embed = discord.Embed(
        title=academy_v61.ACADEMY_TITLE,
        description=(
            "L’Academy suit un parcours simple : **apprendre → pratiquer → faire vérifier → progresser**. "
            "Les ressources gratuites restent courtes pour que tu saches quoi regarder au lieu de te perdre dans 30 liens."
        ),
        color=COLOR,
    )
    embed.add_field(
        name="Ressources essentielles",
        value=f"**{len(fr)} FR** • **{len(en)} EN** • docs officielles + seulement quelques vidéos sélectionnées.",
        inline=True,
    )
    embed.add_field(
        name="Practice Lab",
        value=f"**{len(academy_v61.CHALLENGE_LIBRARY)} challenges** avec critères visibles et validation réelle.",
        inline=True,
    )
    embed.add_field(
        name="AI Coach",
        value="Explique, donne un indice, relit ton plan et t’aide à déboguer sans faire le challenge à ta place.",
        inline=False,
    )
    embed.add_field(
        name="Pour aller plus loin",
        value="L’espace Premium contient les ressources avancées séparées par langue et par domaine, avec un suivi plus poussé.",
        inline=False,
    )
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Aide Bot Academy • moins de liens • plus de progression")
    return embed


def free_resources_embed_v63(language: str) -> discord.Embed:
    language = language.casefold().strip()
    is_fr = language == "fr"
    resources = free_resources("fr" if is_fr else "en")
    embed = discord.Embed(
        title="Academy — Essentiels FR" if is_fr else "Academy — EN essentials",
        description=(
            "Une sélection courte : **documentation fiable + quelques vidéos utiles**. Commence par la ressource liée à ton problème ; "
            "inutile de tout regarder."
            if is_fr
            else "A short list of **reliable documentation + a few useful videos**. Start with the resource that matches your problem; you do not need to watch everything."
        ),
        color=0x3498DB,
    )
    for item in resources:
        embed.add_field(
            name=item["title"][:256],
            value=f"**{item['kind']} • {item['level']}**\n{item['note']}\n[Ouvrir la ressource]({item['url']})" if is_fr else f"**{item['kind']} • {item['level']}**\n{item['note']}\n[Open resource]({item['url']})",
            inline=False,
        )
    embed.add_field(
        name="Premium" if is_fr else "Premium",
        value=(
            "Besoin d’architecture avancée, sécurité, production, UX ou tests ? L’espace Premium sépare les ressources par **langue + domaine**."
            if is_fr
            else "Need advanced architecture, security, production, UX or testing? Premium separates resources by **language + topic**."
        ),
        inline=False,
    )
    embed.set_footer(text=f"Aide Bot Academy • {'FR' if is_fr else 'EN'} • {len(resources)} ressources essentielles")
    return embed


def premium_hub_embed_v63() -> discord.Embed:
    embed = discord.Embed(
        title="Aide Bot — Premium",
        description=(
            "Premium n’est pas une copie de l’Academy avec plus de liens. C’est le niveau **avancé** : ressources triées par langue, "
            "sujets production, accompagnement et application directe sur ton projet."
        ),
        color=PREMIUM,
    )
    embed.add_field(
        name="Bibliothèque avancée FR / EN",
        value="Choisis d’abord ta langue, puis le domaine. Les vidéos directes vérifiées sont distinguées des recherches récentes.",
        inline=False,
    )
    embed.add_field(
        name="5 parcours techniques",
        value="Architecture • Sécurité • Production • UX/Support • Qualité",
        inline=True,
    )
    embed.add_field(
        name="Accompagnement",
        value="Formation avancée + support Premium quand tu veux appliquer le contenu sur ton propre serveur ou bot.",
        inline=True,
    )
    embed.add_field(
        name="Pourquoi certains liens sont des recherches ?",
        value="Pour Railway, AutoMod ou certaines bibliothèques qui changent vite, une recherche récente vaut mieux qu’un vieux tutoriel présenté comme actuel.",
        inline=False,
    )
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Aide Bot Premium • contenu avancé • langue correcte • application pratique")
    return embed


def premium_video_home_embed_v63() -> discord.Embed:
    embed = discord.Embed(
        title="Premium — Bibliothèque avancée",
        description=(
            "Commence par choisir **Français** ou **English**. Tu verras ensuite uniquement les ressources correspondant à cette langue. "
            "Chaque domaine contient une sélection courte et exploitable."
        ),
        color=PREMIUM,
    )
    embed.add_field(name="FR", value="Vidéos et explications françaises quand elles sont de qualité suffisante.", inline=True)
    embed.add_field(name="EN", value="English resources when they are stronger or more complete for advanced topics.", inline=True)
    embed.add_field(
        name="Qualité des liens",
        value="**Sélection directe** = vidéo précise vérifiée • **Recherche récente** = sujet qui évolue vite • **Doc officielle** = référence principale.",
        inline=False,
    )
    embed.set_footer(text="Choisis ta langue ci-dessous")
    return embed


def premium_category_embed_v63(language: str, category: str) -> discord.Embed:
    lang = "fr" if language == "fr" else "en"
    meta = PREMIUM_CATEGORIES[category]
    title = meta[lang]
    description = meta["fr_desc" if lang == "fr" else "en_desc"]
    resources = premium_resources(lang, category)
    embed = discord.Embed(title=f"Premium — {title}", description=description, color=PREMIUM)
    for item in resources:
        if item["type"] == "docs":
            badge = "Doc officielle" if lang == "fr" else "Official docs"
        elif item.get("direct"):
            badge = "Vidéo sélectionnée" if lang == "fr" else "Selected video"
        else:
            badge = "Recherche vidéo récente" if lang == "fr" else "Recent video search"
        embed.add_field(
            name=str(item["title"])[:256],
            value=f"**{badge}**\n{item['note']}",
            inline=False,
        )
    embed.set_footer(
        text="Premium FR • choisis seulement ce qui sert à ton projet" if lang == "fr" else "Premium EN • use only what your project needs"
    )
    return embed


class PremiumResourceLinksV63(discord.ui.View):
    def __init__(self, language: str, category: str) -> None:
        super().__init__(timeout=900)
        for item in premium_resources(language, category):
            self.add_item(
                discord.ui.Button(
                    label=str(item["title"])[:80],
                    url=str(item["url"]),
                    style=discord.ButtonStyle.link,
                )
            )


class PremiumCategorySelectV63(discord.ui.Select):
    def __init__(self, language: str) -> None:
        self.language = "fr" if language == "fr" else "en"
        options = []
        for key, meta in PREMIUM_CATEGORIES.items():
            options.append(
                discord.SelectOption(
                    label=meta[self.language][:100],
                    value=key,
                    description=meta["fr_desc" if self.language == "fr" else "en_desc"][:100],
                )
            )
        super().__init__(
            placeholder="Choisis un domaine Premium" if self.language == "fr" else "Choose a Premium topic",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await premium_v45._require_premium(interaction):
            return
        category = self.values[0]
        await interaction.response.send_message(
            embed=premium_category_embed_v63(self.language, category),
            view=PremiumResourceLinksV63(self.language, category),
            ephemeral=True,
        )


class PremiumCategoryViewV63(discord.ui.View):
    def __init__(self, language: str) -> None:
        super().__init__(timeout=900)
        self.add_item(PremiumCategorySelectV63(language))


class PremiumLanguageSelectV63(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Choisis ta langue / Choose your language",
            min_values=1,
            max_values=1,
            custom_id="aidebot:v63:premium:language",
            options=[
                discord.SelectOption(label="Français", value="fr", description="Ressources avancées en français"),
                discord.SelectOption(label="English", value="en", description="Advanced resources in English"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await premium_v45._require_premium(interaction):
            return
        language = self.values[0]
        embed = discord.Embed(
            title="Premium — Choisis ton domaine" if language == "fr" else "Premium — Choose your topic",
            description=(
                "La bibliothèque affiche maintenant uniquement le contenu français."
                if language == "fr"
                else "The library now shows English content only."
            ),
            color=PREMIUM,
        )
        await interaction.response.send_message(embed=embed, view=PremiumCategoryViewV63(language), ephemeral=True)


class PremiumVideoLibraryViewV63(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(PremiumLanguageSelectV63())


class ContentExperienceV63Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._reconciled: set[int] = set()

    async def cog_load(self) -> None:
        # Patches visuels uniquement : les moteurs tickets/IA/Academy/Premium restent
        # les mêmes. Les callbacks existants résolvent ces fonctions via leurs
        # globals de module au moment du clic.
        academy_v61.academy_home_embed = academy_home_embed_v63
        academy_v61.resources_embed = free_resources_embed_v63
        help_v56.help_hub_embed = help_hub_embed_v63
        simple_v62.help_hub_embed = help_hub_embed_v63
        simple_v62.quick_setup_embed = quick_setup_embed_v63
        simple_v62.instant_help_embed = instant_help_embed_v63
        premium_v45.premium_hub_embed = premium_hub_embed_v63
        premium_v45.premium_video_home_embed = premium_video_home_embed_v63
        premium_v45.PremiumVideoLibraryView = PremiumVideoLibraryViewV63
        self.bot.add_view(PremiumVideoLibraryViewV63())

    async def reconcile_guild(self, guild: discord.Guild) -> None:
        setup = self.bot.get_cog("SetupServerCog")
        if setup is None:
            return

        center = discord.utils.get(guild.text_channels, name="🎓・centre-aide")
        if center is not None:
            await setup._upsert_panel(center, help_hub_embed_v63(), help_v56.HelpHubViewV56(self.bot))

        general = self.bot.get_cog("SimpleHelpV62Cog")
        if general is not None:
            await general.reconcile_general(guild)

        academy = self.bot.get_cog("EnterpriseAcademyV61Cog")
        if academy is not None:
            await academy.publish(guild)

        premium_channel = discord.utils.get(guild.text_channels, name=premium_v45.PREMIUM_HUB_CHANNEL)
        if premium_channel is not None:
            await setup._upsert_panel(
                premium_channel,
                premium_hub_embed_v63(),
                premium_v45.PremiumHubView(self.bot),
            )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            if guild.id in self._reconciled:
                continue
            self._reconciled.add(guild.id)
            await self.reconcile_guild(guild)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ContentExperienceV63Cog(bot))
