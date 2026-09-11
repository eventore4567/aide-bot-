from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs.community import ApplicationModal
from aidebot.experience_content import BANNER_URL


RECRUITMENT_TITLE = "Rejoindre l’équipe Aide Bot"


def recruitment_embed() -> discord.Embed:
    e = discord.Embed(
        title=RECRUITMENT_TITLE,
        description=(
            "Aide Bot recherche des personnes capables d’**expliquer**, pas seulement de donner une réponse. Les Helpers et Formateurs "
            "doivent rester patients, vérifier les informations, respecter la confidentialité et ne jamais demander de secrets.\n\n"
            "Clique sur **Candidater** pour envoyer ton expérience, tes spécialités et tes disponibilités. La candidature arrive dans l’espace staff."
        ),
        color=0x57F287,
    )
    e.add_field(
        name="Ce que nous regardons",
        value="Clarté des explications, sérieux, disponibilité, sécurité, connaissances Discord/bots et capacité à aider sans faire à la place du membre.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Les permissions staff restent minimales et explicites")
    return e


class RecruitmentView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Candidater", style=discord.ButtonStyle.success, custom_id="aidebot:recruitment:apply")
    async def apply(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(ApplicationModal(self.bot))


class RecruitmentPanelCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(RecruitmentView(self.bot))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RecruitmentPanelCog(bot))
