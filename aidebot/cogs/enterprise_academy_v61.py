from __future__ import annotations

import asyncio
from collections import defaultdict

import aiohttp
import discord
from discord.ext import commands

from aidebot.catalog import CHALLENGES, FORMATIONS
from aidebot.challenge_workflow import challenge_already_completed, resolve_challenge_atomic
from aidebot.cogs.product_suite_v60 import StaffSelectV60, staff_embed_v60
from aidebot.cogs.setup_experience_v55 import SetupExperienceV55Cog
from aidebot.cogs.training import TrainingPanel
from aidebot.enterprise_catalog import (
    CERTIFICATIONS,
    CHALLENGE_LIBRARY,
    LEARNING_RESOURCES,
    challenge_categories,
    challenges_for_category,
    resources_for,
)
from aidebot.experience_content import BANNER_URL
from aidebot.permissions import can, decide

COLOR = 0x5865F2
SUCCESS = 0x57F287
WARNING = 0xF1C40F
DANGER = 0xED4245
ACADEMY_CHANNEL = "🎓・formations"
STAFF_CHANNEL = "📋・staff"
ACADEMY_TITLE = "Aide Bot — Formations"

# Le dictionnaire historique reste la source utilisée par les anciens workflows.
# On l'enrichit en place pour conserver la compatibilité DB / réputation.
CHALLENGES.update(CHALLENGE_LIBRARY)


def academy_home_embed() -> discord.Embed:
    fr_count = len(resources_for("fr"))
    en_count = len(resources_for("en"))
    embed = discord.Embed(
        title=ACADEMY_TITLE,
        description=(
            "L’**Aide Bot Academy** regroupe la formation, les ressources, les challenges, le coaching IA et les parcours de certification "
            "dans un seul espace. Chaque outil a un rôle précis : apprendre → pratiquer → faire vérifier → progresser."
        ),
        color=COLOR,
    )
    embed.add_field(
        name="Academy bilingue",
        value=f"**{fr_count} ressources FR** • **{en_count} resources EN** • documentation officielle + recherches vidéo ciblées.",
        inline=True,
    )
    embed.add_field(
        name="Practice Lab",
        value=f"**{len(CHALLENGE_LIBRARY)} challenges** avec difficulté, durée, critères de validation et réputation.",
        inline=True,
    )
    embed.add_field(
        name="AI Coach",
        value="Indice, explication, revue de plan et débogage guidé. Le coach aide à comprendre sans faire automatiquement tout le travail à ta place.",
        inline=False,
    )
    embed.add_field(
        name="Parcours entreprise",
        value=f"**{len(CERTIFICATIONS)} parcours de certification** : foundations, opérations serveur, sécurité et bot engineering.",
        inline=False,
    )
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Aide Bot Academy • apprendre → pratiquer → valider → certifier")
    return embed


def resources_embed(language: str) -> discord.Embed:
    language = language.casefold().strip()
    resources = resources_for(language)
    label = "Ressources françaises" if language == "fr" else "English resources"
    description = (
        "Liens classés par domaine. Les entrées **Docs** pointent vers des références officielles ; les entrées **Vidéo** ouvrent une recherche YouTube ciblée "
        "pour éviter de figer l’Academy sur une seule vidéo qui peut devenir obsolète."
        if language == "fr"
        else "Resources are grouped by domain. **Docs** entries use official references; **Video** entries open focused YouTube searches so the Academy does not depend on one video becoming outdated."
    )
    embed = discord.Embed(title=f"Academy — {label}", description=description, color=0x3498DB)
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in resources:
        groups[item["category"]].append(item)
    for category, items in groups.items():
        lines = []
        for item in items:
            kind = "Docs" if item["type"] == "docs" else "Vidéo" if language == "fr" else "Video"
            lines.append(f"• **[{item['title']}]({item['url']})** — {kind} • {item['level']}\n  {item['note']}")
        embed.add_field(name=category, value="\n".join(lines)[:1024], inline=False)
    embed.set_footer(text=f"{len(resources)} ressources • {'FR' if language == 'fr' else 'EN'}")
    return embed


def challenge_detail_embed(key: str) -> discord.Embed:
    data = CHALLENGE_LIBRARY[key]
    embed = discord.Embed(
        title=f"Challenge — {data['title']}",
        description=str(data["description"]),
        color=WARNING if data["difficulty"] != "Avancé" else DANGER,
    )
    embed.add_field(name="Domaine", value=str(data["category"]), inline=True)
    embed.add_field(name="Difficulté", value=str(data["difficulty"]), inline=True)
    embed.add_field(name="Durée cible", value=str(data["estimated"]), inline=True)
    embed.add_field(name="Récompense", value=f"**+{int(data['reward'])} réputation**", inline=True)
    embed.add_field(
        name="Critères de validation",
        value="\n".join(f"• {criterion}" for criterion in data["criteria"]),
        inline=False,
    )
    embed.add_field(
        name="Preuve attendue",
        value="Lien, capture non sensible, extrait de code, explication ou checklist permettant au staff de vérifier les critères. Ne partage jamais token, cookie, mot de passe ou clé API.",
        inline=False,
    )
    embed.set_footer(text=f"Clé : {key} • validation humaine avant récompense")
    return embed


def certification_catalog_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Academy — Parcours de certification",
        description=(
            "Les certifications sont basées sur des **preuves pratiques**. Un parcours est prêt pour validation quand tous ses challenges requis sont acceptés. "
            "Aide Bot n’attribue pas automatiquement un titre professionnel réel : il suit la progression interne de l’Academy."
        ),
        color=0x9B59B6,
    )
    for data in CERTIFICATIONS.values():
        embed.add_field(
            name=f"{data['title']} • {data['level']}",
            value=f"{data['description']}\n**Challenges requis : {len(data['challenges'])}**",
            inline=False,
        )
    return embed


def staff_enterprise_embed() -> discord.Embed:
    embed = staff_embed_v60()
    embed.add_field(
        name="Academy QA",
        value="File de challenges à vérifier : preuve → critères → accepter/refuser → réputation atomique.",
        inline=False,
    )
    embed.set_footer(text="Aide Bot • opérations serveur + qualité Academy")
    return embed


class ChallengeProofModalV61(discord.ui.Modal, title="Envoyer la preuve du challenge"):
    proof = discord.ui.TextInput(
        label="Preuve et explication",
        placeholder="Explique ce que tu as fait et ajoute un lien si nécessaire. Aucun secret.",
        style=discord.TextStyle.paragraph,
        min_length=20,
        max_length=1500,
    )

    def __init__(self, cog: "EnterpriseAcademyV61Cog", challenge_key: str) -> None:
        super().__init__()
        self.cog = cog
        self.challenge_key = challenge_key

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if self.challenge_key not in CHALLENGE_LIBRARY:
            return await interaction.response.send_message("Challenge introuvable.", ephemeral=True)
        if await challenge_already_completed(
            self.cog.bot.db._db(), interaction.guild.id, interaction.user.id, self.challenge_key
        ):
            return await interaction.response.send_message(
                "Ce challenge est déjà validé sur ton profil. La récompense ne peut être obtenue qu’une seule fois.",
                ephemeral=True,
            )
        submission_id = await self.cog.bot.db.submit_challenge(
            interaction.guild.id,
            interaction.user.id,
            self.challenge_key,
            str(self.proof).strip()[:1500],
        )
        if submission_id is None:
            return await interaction.response.send_message(
                "Tu as déjà une soumission en attente pour ce challenge.", ephemeral=True
            )

        staff = discord.utils.get(interaction.guild.text_channels, name=STAFF_CHANNEL)
        data = CHALLENGE_LIBRARY[self.challenge_key]
        if staff is not None:
            embed = discord.Embed(
                title=f"Academy QA — challenge #{submission_id}",
                description=(
                    f"**Membre :** {interaction.user.mention}\n"
                    f"**Challenge :** {data['title']} (`{self.challenge_key}`)\n"
                    f"**Difficulté :** {data['difficulty']}\n\n"
                    f"**Preuve**\n{str(self.proof).strip()[:1200]}"
                ),
                color=WARNING,
            )
            embed.add_field(
                name="Critères",
                value="\n".join(f"• {item}" for item in data["criteria"])[:1024],
                inline=False,
            )
            embed.set_footer(text="Outils avancés → Academy QA pour traiter la soumission")
            try:
                await staff.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            except (discord.Forbidden, discord.HTTPException):
                pass
        await self.cog.log(interaction.guild, "Challenge Academy envoyé", f"#{submission_id} • {interaction.user.mention} • `{self.challenge_key}`")
        await interaction.response.send_message(
            f"Soumission **#{submission_id}** envoyée à l’Academy QA. Le staff vérifiera les critères avant d’accorder la récompense.",
            ephemeral=True,
        )


class AcademyCoachModalV61(discord.ui.Modal, title="Academy AI Coach"):
    challenge = discord.ui.TextInput(
        label="Challenge / sujet (optionnel)",
        placeholder="Ex: bot-2, permissions, Railway...",
        required=False,
        max_length=100,
    )
    question = discord.ui.TextInput(
        label="Ce qui te bloque",
        placeholder="Ex: je comprends les overwrites mais mon test Membre voit encore le salon",
        style=discord.TextStyle.paragraph,
        min_length=8,
        max_length=1200,
    )

    def __init__(self, cog: "EnterpriseAcademyV61Cog", *, preset_key: str | None = None) -> None:
        super().__init__()
        self.cog = cog
        if preset_key:
            self.challenge.default = preset_key

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        assistant = interaction.client.get_cog("AssistantGuardianV52Cog")
        if assistant is None or not assistant.ai.configured:
            return await interaction.response.send_message(
                "Le Coach IA n’est pas disponible actuellement. Les ressources, challenges et mentors restent utilisables.",
                ephemeral=True,
            )
        allowed, reason = await assistant.ai_limiter.allow(interaction.guild.id, interaction.user.id)
        if not allowed:
            return await interaction.response.send_message(reason or "Réessaie plus tard.", ephemeral=True)

        key = str(self.challenge).strip().casefold()
        challenge_context = ""
        if key in CHALLENGE_LIBRARY:
            data = CHALLENGE_LIBRARY[key]
            challenge_context = (
                f"Challenge: {data['title']} ({key}). Objectif: {data['description']}. "
                f"Critères: {'; '.join(str(x) for x in data['criteria'])}."
            )
        elif key:
            challenge_context = f"Sujet indiqué par l’apprenant: {key}."

        prompt = (
            "MODE ACADEMY COACH. Réponds dans la langue utilisée par l’apprenant. "
            "Ton rôle est de faire progresser : donne d’abord un diagnostic ou un indice, explique le concept, puis propose une prochaine action concrète. "
            "Pour un challenge, ne fournis pas automatiquement une solution finale prête à soumettre ; aide la personne à construire et vérifier sa propre réponse. "
            "Tu peux relire un plan, expliquer une erreur ou proposer une mini-checklist. "
            f"{challenge_context}\n\nBlocage de l’apprenant:\n{str(self.question).strip()}"
        )
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            answer, redacted = await assistant.ai.answer(question=prompt, guild=interaction.guild, member=interaction.user)
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as exc:
            return await interaction.followup.send(
                f"Le Coach IA est temporairement indisponible : {str(exc)[:300]}", ephemeral=True
            )
        embed = discord.Embed(title="Academy AI Coach", description=answer, color=COLOR)
        if redacted:
            embed.add_field(
                name="Secret détecté",
                value="Une valeur ressemblant à un secret a été masquée. Si c’était un vrai token ou une clé, régénère-la.",
                inline=False,
            )
        embed.set_footer(text="Coach = guider et expliquer • la validation du challenge reste humaine")
        await interaction.followup.send(embed=embed, ephemeral=True)


class ChallengeActionViewV61(discord.ui.View):
    def __init__(self, cog: "EnterpriseAcademyV61Cog", challenge_key: str) -> None:
        super().__init__(timeout=900)
        self.cog = cog
        self.challenge_key = challenge_key

    @discord.ui.button(label="Envoyer ma preuve", style=discord.ButtonStyle.success)
    async def submit(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(ChallengeProofModalV61(self.cog, self.challenge_key))

    @discord.ui.button(label="Indice IA", style=discord.ButtonStyle.primary)
    async def hint(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(AcademyCoachModalV61(self.cog, preset_key=self.challenge_key))


class ChallengeSelectV61(discord.ui.Select):
    def __init__(self, cog: "EnterpriseAcademyV61Cog", category: str) -> None:
        self.cog = cog
        self.category = category
        options = []
        for key, data in challenges_for_category(category):
            options.append(
                discord.SelectOption(
                    label=str(data["title"])[:100],
                    value=key,
                    description=f"{data['difficulty']} • {data['estimated']} • +{data['reward']} rep"[:100],
                )
            )
        super().__init__(placeholder=f"Choisis un challenge — {category}", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        key = self.values[0]
        await interaction.response.send_message(
            embed=challenge_detail_embed(key),
            view=ChallengeActionViewV61(self.cog, key),
            ephemeral=True,
        )


class ChallengeCategorySelectV61(discord.ui.Select):
    def __init__(self, cog: "EnterpriseAcademyV61Cog") -> None:
        self.cog = cog
        categories = challenge_categories()
        options = [
            discord.SelectOption(
                label=category,
                value=category,
                description=f"{len(challenges_for_category(category))} challenge(s)",
            )
            for category in categories
        ]
        super().__init__(placeholder="Choisis un domaine de challenge", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        category = self.values[0]
        view = discord.ui.View(timeout=900)
        view.add_item(ChallengeSelectV61(self.cog, category))
        embed = discord.Embed(
            title=f"Practice Lab — {category}",
            description=(
                "Choisis un challenge. Tu verras son objectif, sa durée cible et les critères exacts utilisés par le staff pour la validation."
            ),
            color=WARNING,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PendingChallengeSelectV61(discord.ui.Select):
    def __init__(self, cog: "EnterpriseAcademyV61Cog", rows) -> None:
        self.cog = cog
        options = []
        for row in rows[:25]:
            key = str(row["challenge_key"])
            title = str(CHALLENGES.get(key, {}).get("title", key))
            options.append(
                discord.SelectOption(
                    label=f"#{int(row['id'])} — {title}"[:100],
                    value=str(int(row["id"])),
                    description=f"Membre {int(row['user_id'])} • {key}"[:100],
                )
            )
        super().__init__(placeholder="Soumission à vérifier", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        submission_id = int(self.values[0])
        row = await self.cog.bot.db.challenge_submission(submission_id)
        if not row or row["status"] != "pending":
            return await interaction.response.send_message("Cette soumission n’est plus en attente.", ephemeral=True)
        key = str(row["challenge_key"])
        data = CHALLENGES.get(key, {})
        embed = discord.Embed(
            title=f"Academy QA — #{submission_id}",
            description=(
                f"**Membre :** <@{int(row['user_id'])}>\n"
                f"**Challenge :** {data.get('title', key)} (`{key}`)\n\n"
                f"**Preuve**\n{str(row['proof'])[:1600]}"
            ),
            color=WARNING,
        )
        criteria = data.get("criteria")
        if criteria:
            embed.add_field(name="Critères", value="\n".join(f"• {item}" for item in criteria)[:1024], inline=False)
        await interaction.response.send_message(
            embed=embed,
            view=ChallengeDecisionViewV61(self.cog, submission_id),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class ChallengeDecisionViewV61(discord.ui.View):
    def __init__(self, cog: "EnterpriseAcademyV61Cog", submission_id: int) -> None:
        super().__init__(timeout=900)
        self.cog = cog
        self.submission_id = int(submission_id)

    async def _resolve(self, interaction: discord.Interaction, accepted: bool) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "challenge.review"):
            return await interaction.response.send_message("Accès refusé : `challenge.review` requis.", ephemeral=True)
        row = await self.cog.bot.db.challenge_submission(self.submission_id)
        if not row or row["guild_id"] != interaction.guild.id or row["status"] != "pending":
            return await interaction.response.send_message("Cette soumission a déjà été traitée ou est introuvable.", ephemeral=True)
        key = str(row["challenge_key"])
        reward = int(CHALLENGES.get(key, {}).get("reward", 0))
        result = await resolve_challenge_atomic(
            self.cog.bot.db._db(),
            submission_id=self.submission_id,
            guild_id=interaction.guild.id,
            reviewer_id=interaction.user.id,
            accepted=accepted,
            reward=reward,
        )
        if not result.changed:
            return await interaction.response.send_message("Cette soumission a été traitée entre-temps.", ephemeral=True)
        await self.cog.log(
            interaction.guild,
            "Academy QA",
            f"#{self.submission_id} • {'accepté' if accepted else 'refusé'} par {interaction.user.mention}",
        )
        suffix = f" • +{reward} réputation" if accepted and reward else ""
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="Challenge accepté" if accepted else "Challenge refusé",
                description=f"Soumission **#{self.submission_id}** traitée{suffix}.",
                color=SUCCESS if accepted else DANGER,
            ),
            view=None,
        )

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._resolve(interaction, True)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._resolve(interaction, False)


class EnterpriseStaffViewV61(discord.ui.View):
    def __init__(self, cog: "EnterpriseAcademyV61Cog") -> None:
        super().__init__(timeout=None)
        self.cog = cog
        product = cog.bot.get_cog("ProductSuiteV60Cog")
        if product is not None:
            self.add_item(StaffSelectV60(product))

    @discord.ui.button(label="Academy QA", style=discord.ButtonStyle.secondary, custom_id="aidebot:v61:staff:academy", row=1)
    async def academy_qa(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "challenge.review"):
            return await interaction.response.send_message("Academy QA est réservé au staff autorisé.", ephemeral=True)
        rows = await self.cog.pending_challenges(interaction.guild.id)
        if not rows:
            return await interaction.response.send_message("Aucun challenge n’attend de validation.", ephemeral=True)
        view = discord.ui.View(timeout=900)
        view.add_item(PendingChallengeSelectV61(self.cog, rows))
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Academy QA — file de validation",
                description=f"**{len(rows)}** soumission(s) en attente. Vérifie la preuve contre les critères avant d’accepter.",
                color=WARNING,
            ),
            view=view,
            ephemeral=True,
        )


class AcademyHomeSelectV61(discord.ui.Select):
    def __init__(self, cog: "EnterpriseAcademyV61Cog") -> None:
        self.cog = cog
        super().__init__(
            placeholder="Que veux-tu faire dans l’Academy ?",
            min_values=1,
            max_values=1,
            custom_id="aidebot:v61:academy:menu",
            options=[
                discord.SelectOption(label="Parcours & formations", value="training", description="Choisir un parcours accompagné"),
                discord.SelectOption(label="Ressources FR", value="resources_fr", description="Docs et vidéos ciblées en français"),
                discord.SelectOption(label="Resources EN", value="resources_en", description="Official docs and focused English videos"),
                discord.SelectOption(label="Practice Lab — Challenges", value="challenges", description="Pratiquer avec critères de validation"),
                discord.SelectOption(label="Academy AI Coach", value="coach", description="Indice, explication, revue et debug guidé"),
                discord.SelectOption(label="Certifications", value="certifications", description="Parcours internes basés sur des preuves"),
                discord.SelectOption(label="Ma progression", value="progress", description="Leçons, challenges et readiness"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        value = self.values[0]
        if value == "resources_fr":
            return await interaction.response.send_message(embed=resources_embed("fr"), ephemeral=True)
        if value == "resources_en":
            return await interaction.response.send_message(embed=resources_embed("en"), ephemeral=True)
        if value == "challenges":
            view = discord.ui.View(timeout=900)
            view.add_item(ChallengeCategorySelectV61(self.cog))
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="Practice Lab — Challenges",
                    description=(
                        f"**{len(CHALLENGE_LIBRARY)} challenges** répartis par domaine. Chaque challenge annonce les critères avant la soumission."
                    ),
                    color=WARNING,
                ),
                view=view,
                ephemeral=True,
            )
        if value == "coach":
            return await interaction.response.send_modal(AcademyCoachModalV61(self.cog))
        if value == "certifications":
            if not interaction.guild:
                return
            embed = await self.cog.certification_status(interaction.guild.id, interaction.user.id)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        if value == "progress":
            if not interaction.guild:
                return
            embed = await self.cog.progress_embed(interaction.guild.id, interaction.user.id)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        if value == "training":
            training = interaction.client.get_cog("TrainingCog")
            if training is None:
                return await interaction.response.send_message("Le module de formations accompagnées est indisponible.", ephemeral=True)
            embed = discord.Embed(
                title="Parcours accompagnés",
                description="Choisis le parcours correspondant à ton objectif. Chaque demande utilise un formulaire adapté au sujet.",
                color=COLOR,
            )
            for key, data in FORMATIONS.items():
                embed.add_field(
                    name=data["title"],
                    value=f"{data['difficulty']} • {data['duration']}\n{data['description']}",
                    inline=False,
                )
            return await interaction.response.send_message(embed=embed, view=TrainingPanel(training), ephemeral=True)


class AcademyHomeViewV61(discord.ui.View):
    def __init__(self, cog: "EnterpriseAcademyV61Cog") -> None:
        super().__init__(timeout=None)
        self.add_item(AcademyHomeSelectV61(cog))


class EnterpriseAcademyV61Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._reconciled: set[int] = set()
        self._patched = False

    async def cog_load(self) -> None:
        self.bot.add_view(AcademyHomeViewV61(self))
        self.bot.add_view(EnterpriseStaffViewV61(self))
        self._patch_setup_pipeline()

    async def log(self, guild: discord.Guild, title: str, description: str) -> None:
        channel = discord.utils.get(guild.text_channels, name="🧾・logs")
        if channel is None:
            return
        try:
            await channel.send(
                embed=discord.Embed(title=title, description=description, color=0x2B2D31),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def accepted_challenges(self, guild_id: int, user_id: int) -> set[str]:
        cur = await self.bot.db._db().execute(
            """SELECT DISTINCT challenge_key FROM challenge_submissions
               WHERE guild_id=? AND user_id=? AND status='accepted'""",
            (guild_id, user_id),
        )
        return {str(row["challenge_key"]) for row in await cur.fetchall()}

    async def pending_challenges(self, guild_id: int):
        cur = await self.bot.db._db().execute(
            """SELECT id,user_id,challenge_key,proof,status FROM challenge_submissions
               WHERE guild_id=? AND status='pending' ORDER BY id ASC LIMIT 100""",
            (guild_id,),
        )
        return await cur.fetchall()

    async def certification_status(self, guild_id: int, user_id: int) -> discord.Embed:
        accepted = await self.accepted_challenges(guild_id, user_id)
        embed = certification_catalog_embed()
        embed.clear_fields()
        ready = 0
        for data in CERTIFICATIONS.values():
            required = tuple(str(key) for key in data["challenges"])
            done = sum(1 for key in required if key in accepted)
            complete = done == len(required)
            ready += int(complete)
            embed.add_field(
                name=f"{'PRÊT' if complete else 'EN COURS'} — {data['title']} • {data['level']}",
                value=f"{data['description']}\n**Progression : {done}/{len(required)} challenges validés**",
                inline=False,
            )
        embed.description = (
            f"**Parcours prêts pour validation : {ready}/{len(CERTIFICATIONS)}**\n"
            "Les certifications Aide Bot sont des validations internes basées sur des challenges pratiques vérifiés."
        )
        return embed

    async def progress_embed(self, guild_id: int, user_id: int) -> discord.Embed:
        accepted = await self.accepted_challenges(guild_id, user_id)
        cur = await self.bot.db._db().execute(
            """SELECT COUNT(*) AS n FROM challenge_submissions
               WHERE guild_id=? AND user_id=? AND status='pending'""",
            (guild_id, user_id),
        )
        row = await cur.fetchone()
        pending = int(row["n"]) if row else 0
        learning = await self.bot.db.learning_progress(guild_id, user_id)
        started = sum(1 for item in learning if int(item["max_lesson"]) > 0)
        correct = sum(int(item["quiz_correct"]) for item in learning)
        ready = 0
        for data in CERTIFICATIONS.values():
            required = {str(key) for key in data["challenges"]}
            if required.issubset(accepted):
                ready += 1
        embed = discord.Embed(title="Academy — Ma progression", color=SUCCESS if accepted else COLOR)
        embed.add_field(name="Parcours commencés", value=str(started), inline=True)
        embed.add_field(name="Quiz corrects", value=str(correct), inline=True)
        embed.add_field(name="Challenges validés", value=f"{len(accepted)}/{len(CHALLENGE_LIBRARY)}", inline=True)
        embed.add_field(name="En attente QA", value=str(pending), inline=True)
        embed.add_field(name="Certifications prêtes", value=f"{ready}/{len(CERTIFICATIONS)}", inline=True)
        if accepted:
            latest = sorted(accepted)[-8:]
            embed.add_field(name="Validations", value=" • ".join(f"`{key}`" for key in latest), inline=False)
        embed.set_footer(text="Progression calculée depuis les leçons et challenges réellement enregistrés")
        return embed

    async def publish(self, guild: discord.Guild, channels: dict[str, discord.TextChannel] | None = None) -> list[tuple[str, str]]:
        base = self.bot.get_cog("SetupServerCog")
        if base is None:
            return []
        academy = channels.get(ACADEMY_CHANNEL) if channels else discord.utils.get(guild.text_channels, name=ACADEMY_CHANNEL)
        staff = channels.get(STAFF_CHANNEL) if channels else discord.utils.get(guild.text_channels, name=STAFF_CHANNEL)
        actions: list[tuple[str, str]] = []
        actions.append(("Enterprise Academy", await base._upsert_panel(academy, academy_home_embed(), AcademyHomeViewV61(self))))
        actions.append(("Academy QA", await base._upsert_panel(staff, staff_enterprise_embed(), EnterpriseStaffViewV61(self))))
        return actions

    def _patch_setup_pipeline(self) -> None:
        if self._patched:
            return
        original = SetupExperienceV55Cog._publish_panels
        if getattr(original, "_aidebot_v61_wrapped", False):
            self._patched = True
            return

        async def wrapped(setup_cog, guild, channels, roles):
            actions = await original(setup_cog, guild, channels, roles)
            academy_cog = setup_cog.bot.get_cog("EnterpriseAcademyV61Cog")
            if academy_cog is not None:
                actions.extend(await academy_cog.publish(guild, channels))
            return actions

        wrapped._aidebot_v61_wrapped = True
        SetupExperienceV55Cog._publish_panels = wrapped
        self._patched = True

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            if guild.id in self._reconciled:
                continue
            self._reconciled.add(guild.id)
            await self.publish(guild)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EnterpriseAcademyV61Cog(bot))
