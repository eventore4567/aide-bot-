from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs import recruitment_panel as legacy
from aidebot.experience_content import BANNER_URL


RECRUITMENT_TRACKS = {
    "helper": {
        "label": "Helper",
        "role": "🤝・Helper",
        "description": "Support membre, diagnostic, explications simples et suivi de tickets.",
        "questions": (
            ("Ton expérience en support", "Serveurs, tickets, modération, aide Discord... Donne des exemples précis.", 30, 700),
            ("Ta façon d’expliquer", "Comment aides-tu un débutant sans faire tout à sa place ?", 30, 600),
            ("Cas pratique : permission", "Un membre dit : « je ne vois pas le salon ». Que vérifies-tu, dans quel ordre ?", 40, 700),
            ("Conflit / membre énervé", "Comment réagis-tu si la personne devient impatiente ou agressive ?", 30, 550),
            ("Tes disponibilités", "Jours + horaires habituels et fréquence réelle.", 5, 180),
        ),
    },
    "trainer": {
        "label": "Formateur",
        "role": "🎓・Formateur",
        "description": "Accompagnement structuré, exercices, vérification des acquis et progression.",
        "questions": (
            ("Sujets que tu maîtrises", "Discord, permissions, bots, Python, sécurité... précise ton vrai niveau.", 30, 700),
            ("Ta méthode pédagogique", "Comment passes-tu d’un objectif à un plan de formation clair ?", 30, 600),
            ("Cas pratique : débutant", "Un membre veut créer son premier bot mais ne connaît pas Python. Fais un plan en étapes.", 50, 750),
            ("Comment tu valides un acquis", "Comment vérifies-tu que la personne a compris et peut refaire seule ?", 30, 550),
            ("Tes disponibilités", "Jours + horaires habituels et fréquence réelle.", 5, 180),
        ),
    },
    "bot_expert": {
        "label": "Expert Bots",
        "role": "🤖・Expert Bots",
        "description": "Python, discord.py, architecture, base de données, tests et déploiement.",
        "questions": (
            ("Tes projets / stack", "Python, discord.py, DB, Railway, GitHub... indique ce que tu as réellement utilisé.", 30, 700),
            ("Ta méthode de debug", "Comment trouves-tu la cause d’un bug avant de modifier le code ?", 30, 600),
            ("Cas pratique : crash prod", "Le bot marche en local mais crash sur Railway. Que vérifies-tu, dans quel ordre ?", 50, 750),
            ("Sécurité du code", "Comment protèges-tu tokens, paiements, données et actions concurrentes ?", 30, 600),
            ("Tes disponibilités", "Jours + horaires habituels et fréquence réelle.", 5, 180),
        ),
    },
    "security_expert": {
        "label": "Expert Sécurité",
        "role": "🛡️・Expert Sécurité",
        "description": "Audit de permissions, anti-raid, bots/webhooks et réponse à incident.",
        "questions": (
            ("Ton expérience sécurité", "Audits, anti-raid, permissions, incidents, logs... donne des exemples sans données sensibles.", 30, 700),
            ("Ta méthode d’audit", "Dans quel ordre vérifies-tu un serveur Discord ?", 30, 600),
            ("Cas pratique : raid", "Un raid vient de commencer. Quelles actions immédiates prends-tu et lesquelles évites-tu ?", 50, 750),
            ("Permissions sensibles", "Quelles permissions surveilles-tu en priorité et pourquoi ?", 30, 600),
            ("Tes disponibilités", "Jours + horaires habituels et fréquence réelle.", 5, 180),
        ),
    },
}


def recruitment_v46_embed() -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Candidatures staff",
        description=(
            "Choisis **le poste qui correspond réellement à tes compétences**. Chaque poste possède maintenant son propre questionnaire avec des questions "
            "techniques ou pratiques : ce n’est plus le même formulaire générique pour tout le monde.\n\n"
            "Le staff reçoit tes réponses complètes, puis peut accepter ou refuser la candidature depuis son panneau. Une seule candidature peut rester en attente à la fois."
        ),
        color=0x57F287,
    )
    for data in RECRUITMENT_TRACKS.values():
        e.add_field(name=data["label"], value=data["description"], inline=True)
    e.add_field(
        name="Ce qui compte vraiment",
        value=(
            "Réponses précises • exemples réels • méthode claire • sécurité • capacité à expliquer • honnêteté sur ton niveau • disponibilité réaliste. "
            "Une réponse courte du type « je suis motivé » ne suffit pas."
        ),
        inline=False,
    )
    e.add_field(
        name="Avant d’envoyer",
        value="Relis tes réponses, ne partage aucun token/mot de passe/cookie/code 2FA, et choisis un seul poste à la fois.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V46 • 4 postes • questionnaire spécifique • cas pratique")
    return e


class RoleApplicationModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, target_role: str) -> None:
        data = RECRUITMENT_TRACKS[target_role]
        super().__init__(title=f"Candidature — {data['label']}"[:45])
        self.bot = bot
        self.target_role = target_role
        self.role_label = data["label"]
        self.inputs: list[discord.ui.TextInput] = []

        for index, (label, placeholder, min_length, max_length) in enumerate(data["questions"]):
            field = discord.ui.TextInput(
                label=label[:45],
                placeholder=placeholder[:100],
                style=discord.TextStyle.paragraph if index < 4 else discord.TextStyle.short,
                min_length=min_length,
                max_length=max_length,
            )
            self.inputs.append(field)
            self.add_item(field)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return

        values = [str(field).strip() for field in self.inputs]
        question_defs = RECRUITMENT_TRACKS[self.target_role]["questions"]
        combined = "\n\n".join(
            f"Q{index + 1} — {question_defs[index][0]}\n{value}"
            for index, value in enumerate(values[:4])
        )
        skills = f"Poste demandé : {self.role_label}\n\n{question_defs[1][0]}\n{values[1]}"
        availability = values[4]

        application_id = await self.bot.db.create_application(
            interaction.guild.id,
            interaction.user.id,
            self.target_role,
            combined,
            skills,
            availability,
        )
        if application_id is None:
            return await interaction.response.send_message(
                "Tu as déjà une candidature en attente. Attends qu’elle soit traitée avant d’en envoyer une autre.",
                ephemeral=True,
            )

        staff = discord.utils.get(interaction.guild.text_channels, name="📋・staff")
        if staff is None:
            return await interaction.response.send_message(
                f"Candidature **#{application_id}** enregistrée, mais le salon staff est introuvable. Préviens la Direction.",
                ephemeral=True,
            )

        e = discord.Embed(
            title=f"Candidature #{application_id} — {self.role_label}",
            description=f"Candidat : {interaction.user.mention}\nPoste visé : **{RECRUITMENT_TRACKS[self.target_role]['role']}**",
            color=0x57F287,
        )
        for index, value in enumerate(values):
            label = question_defs[index][0]
            e.add_field(name=f"Q{index + 1} — {label}", value=value[:1024], inline=False)
        e.add_field(
            name="Décision staff",
            value="Vérifie surtout la méthode, le cas pratique, l’honnêteté du niveau et la disponibilité. Puis utilise **Accepter** ou **Refuser**.",
            inline=False,
        )
        e.set_footer(text=f"Aide Bot V46 • Candidature #{application_id} • en attente")

        await staff.send(
            embed=e,
            view=legacy.StaffApplicationReviewView(self.bot),
            allowed_mentions=discord.AllowedMentions.none(),
        )

        logs = discord.utils.get(interaction.guild.text_channels, name="🧾・logs")
        if logs:
            try:
                await logs.send(
                    embed=discord.Embed(
                        title="Candidature reçue",
                        description=f"#{application_id} • {interaction.user.mention} • {self.role_label}",
                        color=0x2B2D31,
                    ),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass

        await interaction.response.send_message(
            f"Candidature **#{application_id}** envoyée pour **{self.role_label}**. Tes 5 réponses ont été transmises au staff.",
            ephemeral=True,
        )


class RecruitmentRoleSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        options = [
            discord.SelectOption(
                label=data["label"],
                value=key,
                description=data["description"][:100],
            )
            for key, data in RECRUITMENT_TRACKS.items()
        ]
        super().__init__(
            placeholder="Choisis le poste pour ouvrir son questionnaire",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="aidebot:v46:recruitment:role",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(RoleApplicationModal(self.bot, self.values[0]))


class RecruitmentV46View(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(RecruitmentRoleSelect(bot))


class RecruitmentV46Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        # Le workflow d’acceptation atomique V41 reste la source de vérité.
        # On étend uniquement les postes et l’expérience de candidature.
        legacy.APPLICATION_ROLE_NAMES.update(
            {
                "bot_expert": "🤖・Expert Bots",
                "security_expert": "🛡️・Expert Sécurité",
            }
        )
        legacy.RecruitmentView = RecruitmentV46View
        legacy.recruitment_embed = recruitment_v46_embed
        self.bot.add_view(RecruitmentV46View(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RecruitmentV46Cog(bot))
