from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.lessons import GLOSSARY, LESSON_PATHS, QUIZZES, QuizQuestion, get_lesson, glossary_lookup, path_size


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
    def __init__(self, user_id: int, question: QuizQuestion) -> None:
        super().__init__(timeout=180)
        self.user_id = user_id
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
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
                if isinstance(child, QuizAnswerButton) and child.answer_index == self.question.correct:
                    child.style = discord.ButtonStyle.success
                elif isinstance(child, QuizAnswerButton) and child.answer_index == selected and not correct:
                    child.style = discord.ButtonStyle.danger
        result = "Bonne réponse." if correct else "Pas tout à fait."
        embed = discord.Embed(
            title=result,
            description=self.question.explanation,
            color=0x57F287 if correct else 0xED4245,
        )
        await interaction.response.edit_message(embed=embed, view=self)


class SelfLearningCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    apprendre = app_commands.Group(name="apprendre", description="Apprendre Discord directement avec Aide Bot")

    @apprendre.command(name="parcours", description="Voir les mini-parcours gratuits disponibles")
    async def parcours(self, interaction: discord.Interaction) -> None:
        lines = []
        for key, data in LESSON_PATHS.items():
            lines.append(
                f"**{data['title']}** (`{key}`) • {path_size(key)} leçons\n"
                f"{data['description']}"
            )
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Mini-parcours gratuits",
                description="\n\n".join(lines) + "\n\nUtilise `/apprendre lecon` pour commencer.",
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
        next_line = (
            f"Ensuite : `/apprendre lecon sujet:{key} numero:{numero + 1}`"
            if int(numero) < total
            else f"Parcours terminé. Teste-toi avec `/apprendre quiz sujet:{key}`."
        )
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{numero}/{total} — {lesson.title}",
                description=(
                    f"{lesson.explanation}\n\n"
                    f"**À faire**\n{lesson.exercise}\n\n"
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
        question = random.choice(questions)
        await interaction.response.send_message(
            embed=discord.Embed(title="Mini-quiz", description=question.question, color=0xF1C40F),
            view=QuizView(interaction.user.id, question),
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
