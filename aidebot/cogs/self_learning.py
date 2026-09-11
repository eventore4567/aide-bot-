from __future__ import annotations

import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.lessons import GLOSSARY, LESSON_PATHS, QUIZZES, QuizQuestion, get_lesson, glossary_lookup, path_size

log = logging.getLogger("aidebot.learning")


def _progress_bar(done: int, total: int, width: int = 10) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, max(0, round(width * done / total)))
    return "█" * filled + "░" * (width - filled)


def _progress_status(max_lesson: int, total: int, quiz_correct: int) -> str:
    if max_lesson >= total and quiz_correct > 0:
        return "Validé"
    if max_lesson >= total:
        return "Quiz à valider"
    if max_lesson > 0:
        return "En cours"
    return "Non commencé"


class QuizAnswerButton(discord.ui.Button):
    def __init__(self, index: int, label: str) -> None:
        super().__init__(label=label[:80], style=discord.ButtonStyle.secondary)
        self.answer_index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, QuizView):
            return
        await view.answer(interaction, self.answer_index)


class QuizView(discord.ui.View):
    def __init__(self, bot: commands.Bot, guild_id: int, user_id: int, subject: str, question: QuizQuestion) -> None:
        super().__init__(timeout=180)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.subject = subject
        self.question = question
        self.finished = False
        for index, option in enumerate(question.options):
            self.add_item(QuizAnswerButton(index, option))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ce mini-quiz appartient à un autre membre.", ephemeral=True)
            return False
        return True

    async def answer(self, interaction: discord.Interaction, selected: int) -> None:
        if self.finished:
            return await interaction.response.send_message("Cette question est déjà terminée.", ephemeral=True)
        self.finished = True
        correct = selected == self.question.correct
        try:
            await self.bot.db.record_quiz_answer(self.guild_id, self.user_id, self.subject, correct)
        except Exception:
            log.exception("Impossible d'enregistrer la progression du quiz")

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
                if isinstance(child, QuizAnswerButton) and child.answer_index == self.question.correct:
                    child.style = discord.ButtonStyle.success
                elif isinstance(child, QuizAnswerButton) and child.answer_index == selected and not correct:
                    child.style = discord.ButtonStyle.danger
        result = "Bonne réponse." if correct else "Pas tout à fait."
        suffix = "\n\nTa progression a été enregistrée. Utilise `/apprendre progression` pour la voir."
        embed = discord.Embed(
            title=result,
            description=self.question.explanation + suffix,
            color=0x57F287 if correct else 0xED4245,
        )
        await interaction.response.edit_message(embed=embed, view=self)


class SelfLearningCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    apprendre = app_commands.Group(name="apprendre", description="Apprendre Discord directement avec Aide Bot")

    @apprendre.command(name="parcours", description="Voir les mini-parcours gratuits disponibles")
    async def parcours(self, interaction: discord.Interaction) -> None:
        progress = {}
        if interaction.guild:
            rows = await self.bot.db.learning_progress(interaction.guild.id, interaction.user.id)
            progress = {row["path_key"]: row for row in rows}

        lines = []
        for key, data in LESSON_PATHS.items():
            total = path_size(key)
            row = progress.get(key)
            seen = min(int(row["max_lesson"]), total) if row else 0
            correct = int(row["quiz_correct"]) if row else 0
            status = _progress_status(seen, total, correct)
            lines.append(
                f"**{data['title']}** (`{key}`) • {seen}/{total} leçons • {status}\n"
                f"`{_progress_bar(seen, total)}` {data['description']}"
            )
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Mini-parcours gratuits",
                description="\n\n".join(lines) + "\n\nUtilise `/apprendre reprendre` pour continuer automatiquement.",
                color=0x5865F2,
            ),
            ephemeral=True,
        )

    @apprendre.command(name="lecon", description="Lire une étape d'un mini-parcours")
    @app_commands.describe(sujet="discord / serveur / permissions / bot", numero="Numéro de la leçon")
    async def lecon(self, interaction: discord.Interaction, sujet: str, numero: app_commands.Range[int, 1, 20] = 1) -> None:
        key = sujet.casefold().strip()
        lesson = get_lesson(key, int(numero))
        total = path_size(key)
        if lesson is None:
            return await interaction.response.send_message(
                "Leçon introuvable. Utilise `/apprendre parcours` pour voir les sujets et le nombre d'étapes.",
                ephemeral=True,
            )
        if interaction.guild:
            await self.bot.db.mark_lesson_seen(interaction.guild.id, interaction.user.id, key, int(numero))
        next_line = (
            f"Ensuite : `/apprendre lecon sujet:{key} numero:{numero + 1}`"
            if int(numero) < total
            else f"Toutes les leçons sont vues. Valide le parcours avec `/apprendre quiz sujet:{key}`."
        )
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{numero}/{total} — {lesson.title}",
                description=(
                    f"{lesson.explanation}\n\n"
                    f"**À faire**\n{lesson.exercise}\n\n"
                    f"**Progression**\n`{_progress_bar(int(numero), total)}` {numero}/{total}\n\n"
                    f"**Suite**\n{next_line}"
                ),
                color=0x3498DB,
            ),
            ephemeral=True,
        )

    @apprendre.command(name="quiz", description="Faire une question rapide sur un sujet")
    @app_commands.describe(sujet="discord / serveur / permissions / bot")
    async def quiz(self, interaction: discord.Interaction, sujet: str) -> None:
        key = sujet.casefold().strip()
        questions = QUIZZES.get(key)
        if not questions:
            return await interaction.response.send_message(
                "Quiz inconnu. Sujets disponibles : " + ", ".join(f"`{name}`" for name in QUIZZES),
                ephemeral=True,
            )
        if not interaction.guild:
            return await interaction.response.send_message("Les quiz avec progression sont disponibles uniquement dans le serveur.", ephemeral=True)
        question = random.choice(questions)
        await interaction.response.send_message(
            embed=discord.Embed(title="Mini-quiz", description=question.question, color=0xF1C40F),
            view=QuizView(self.bot, interaction.guild.id, interaction.user.id, key, question),
            ephemeral=True,
        )

    @apprendre.command(name="progression", description="Voir ta progression dans les parcours gratuits")
    async def progression(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Cette progression est disponible uniquement dans le serveur.", ephemeral=True)
        rows = await self.bot.db.learning_progress(interaction.guild.id, interaction.user.id)
        by_key = {row["path_key"]: row for row in rows}
        lines = []
        validated = 0
        for key, data in LESSON_PATHS.items():
            total = path_size(key)
            row = by_key.get(key)
            seen = min(int(row["max_lesson"]), total) if row else 0
            attempts = int(row["quiz_attempts"]) if row else 0
            correct = int(row["quiz_correct"]) if row else 0
            status = _progress_status(seen, total, correct)
            if status == "Validé":
                validated += 1
            lines.append(
                f"**{data['title']}** — {status}\n"
                f"`{_progress_bar(seen, total)}` {seen}/{total} leçons • quiz {correct}/{attempts} correct(s)"
            )
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Ta progression d'apprentissage",
                description=f"**Parcours validés : {validated}/{len(LESSON_PATHS)}**\n\n" + "\n\n".join(lines),
                color=0x57F287 if validated == len(LESSON_PATHS) else 0x3498DB,
            ),
            ephemeral=True,
        )

    @apprendre.command(name="reprendre", description="Continuer automatiquement là où tu t'es arrêté")
    async def reprendre(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return await interaction.response.send_message("Cette fonction est disponible uniquement dans le serveur.", ephemeral=True)
        rows = await self.bot.db.learning_progress(interaction.guild.id, interaction.user.id)
        by_key = {row["path_key"]: row for row in rows}

        for key, data in LESSON_PATHS.items():
            total = path_size(key)
            row = by_key.get(key)
            if row is None:
                return await interaction.response.send_message(
                    f"Commence **{data['title']}** avec `/apprendre lecon sujet:{key} numero:1`.",
                    ephemeral=True,
                )
            seen = min(int(row["max_lesson"]), total)
            if seen < total:
                return await interaction.response.send_message(
                    f"Reprends **{data['title']}** à la leçon **{seen + 1}/{total}** : `/apprendre lecon sujet:{key} numero:{seen + 1}`.",
                    ephemeral=True,
                )
            if int(row["quiz_correct"]) <= 0:
                return await interaction.response.send_message(
                    f"Tu as vu toutes les leçons de **{data['title']}**. Il reste à valider un quiz : `/apprendre quiz sujet:{key}`.",
                    ephemeral=True,
                )

        await interaction.response.send_message(
            "Tous les mini-parcours gratuits sont validés. Tu peux maintenant passer aux `/challenge liste` ou ouvrir une formation complète depuis `/centre`.",
            ephemeral=True,
        )

    @apprendre.command(name="glossaire", description="Comprendre rapidement un terme Discord")
    async def glossaire(self, interaction: discord.Interaction, terme: str) -> None:
        result = glossary_lookup(terme)
        if result is None:
            known = ", ".join(f"`{term}`" for term in GLOSSARY)
            return await interaction.response.send_message(
                f"Terme introuvable. Quelques termes disponibles : {known}.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=discord.Embed(title=f"Glossaire — {terme}", description=result, color=0x5865F2),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SelfLearningCog(bot))
