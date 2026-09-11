from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.catalog import search_knowledge
from aidebot.diagnostic import DiagnosticResult, diagnose, recommended_commands


def _result_embed(result: DiagnosticResult) -> discord.Embed:
    route = result.route
    lines = [
        f"**Orientation :** {route.title}",
        f"**Confiance :** {result.confidence}",
        "",
        f"**Conseil immédiat**\n{route.help_hint}",
    ]
    if result.secondary:
        lines.append(f"\n**Sujet proche détecté :** {result.secondary.title}")
    if result.urgent_security:
        lines.append(
            "\n**Sécurité prioritaire**\n"
            "Si un token ou compte est compromis, révoque/régénère d’abord le secret concerné, "
            "retire les permissions dangereuses et ne partage aucun token, mot de passe ou code de récupération."
        )
    lines.append("\n**Actions conseillées**\n" + "\n".join(f"• {item}" for item in recommended_commands(result)))
    return discord.Embed(
        title="Aide Bot — Diagnostic",
        description="\n".join(lines)[:4000],
        color=0xED4245 if result.urgent_security else 0x5865F2,
    )


class DiagnosticActions(discord.ui.View):
    def __init__(self, bot: commands.Bot, problem: str) -> None:
        super().__init__(timeout=300)
        self.bot = bot
        self.problem = problem[:700]

    @discord.ui.button(label="Chercher une réponse", style=discord.ButtonStyle.secondary)
    async def search_answer(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        matches = search_knowledge(self.problem, limit=3)
        if not matches:
            return await interaction.response.send_message(
                "Je n’ai pas trouvé d’article assez proche. Tu peux demander directement un Helper.",
                ephemeral=True,
            )
        lines = []
        for key, item in matches:
            lines.append(f"**{item['title']}** (`{key}`)\n{item['summary']}")
        await interaction.response.send_message(
            embed=discord.Embed(title="Réponses proches", description="\n\n".join(lines), color=0x3498DB),
            ephemeral=True,
        )

    @discord.ui.button(label="Demander à un Helper", style=discord.ButtonStyle.success)
    async def ask_helper(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Cette action doit être utilisée dans le serveur.", ephemeral=True)
        training = self.bot.get_cog("TrainingCog")
        if training is None:
            return await interaction.response.send_message("Le module d’aide est indisponible.", ephemeral=True)
        await training.create_request_channel(
            interaction,
            "community_help",
            level="Diagnostic automatique",
            objective=self.problem,
            availability="Dès qu’un Helper est disponible",
            budget="Gratuit",
            status="open",
            payment_status="not_required",
            invite_used=False,
        )


class DiagnosticCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="diagnostic", description="Décrire ton problème et recevoir le meilleur parcours Aide Bot")
    @app_commands.describe(probleme="Explique ce que tu veux faire ou ce qui bloque")
    @app_commands.checks.cooldown(3, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def diagnostic(self, interaction: discord.Interaction, probleme: app_commands.Range[str, 5, 900]) -> None:
        result = diagnose(str(probleme))
        await interaction.response.send_message(
            embed=_result_embed(result),
            view=DiagnosticActions(self.bot, str(probleme)),
            ephemeral=True,
        )

        if interaction.guild:
            logs = discord.utils.get(interaction.guild.text_channels, name="🧾・logs")
            if logs:
                try:
                    await logs.send(
                        embed=discord.Embed(
                            title="Diagnostic utilisé",
                            description=(
                                f"Membre : {interaction.user.mention}\n"
                                f"Orientation : `{result.route.key}`\n"
                                f"Confiance : `{result.confidence}`\n"
                                f"Sécurité prioritaire : `{'oui' if result.urgent_security else 'non'}`\n\n"
                                "Le texte libre du membre n’est pas copié dans les logs."
                            ),
                            color=0x2B2D31,
                        ),
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                except discord.HTTPException:
                    pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DiagnosticCog(bot))
