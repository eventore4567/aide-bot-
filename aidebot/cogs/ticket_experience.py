from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from aidebot.experience_content import BANNER_URL


class TicketExperienceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("ticket-"):
            return

        # Le channel est créé avant que son ID soit enregistré dans la demande.
        # On laisse la transaction de création finir puis on charge la demande.
        for _ in range(6):
            await asyncio.sleep(0.5)
            req = await self.bot.db.request_by_channel(channel.id)
            if req is not None:
                break
        else:
            return

        is_help = req["training_key"] == "community_help"
        is_premium = req["payment_status"] in {"pending", "paid", "refunded"}

        e = discord.Embed(
            title="Aide Bot — ton espace de suivi",
            description=(
                "Ce ticket est ton espace privé avec l’équipe Aide Bot. Explique ton problème avec le plus de contexte possible : "
                "ce que tu veux obtenir, ce qui ne fonctionne pas, ce que tu as déjà essayé et les messages d’erreur exacts. "
                "Tu peux envoyer des captures d’écran si elles aident à comprendre.\n\n"
                "**Ne partage jamais de token Discord, mot de passe, code 2FA, cookie, clé API ou autre secret.** "
                "Un membre de l’équipe n’a pas besoin de ton mot de passe pour t’aider."
            ),
            color=0x5865F2,
        )
        e.add_field(
            name="Comment la prise en charge fonctionne",
            value=(
                "Un Helper/Formateur autorisé, un Responsable, un Administrateur Discord ou le propriétaire peut cliquer sur "
                "**Prendre**. L’attribution est protégée : si deux personnes essaient en même temps, une seule devient responsable du ticket. "
                "Ensuite, cette personne te guide jusqu’à la résolution ou transfère le suivi à un responsable si nécessaire."
            ),
            inline=False,
        )
        if is_help:
            e.add_field(
                name="Type de service — aide gratuite",
                value=(
                    "Cette demande fait partie de l’entraide gratuite. Le but est de t’expliquer la solution et de te permettre de la refaire seul. "
                    "Si ton besoin devient un projet complet ou demande un accompagnement long, l’équipe peut te présenter une offre Premium, mais l’aide gratuite reste disponible."
                ),
                inline=False,
            )
        elif is_premium:
            e.add_field(
                name="Type de service — Premium",
                value=(
                    "Une demande Premium ne peut être prise en charge qu’après confirmation du paiement par la Direction. Une fois confirmé, "
                    "le Formateur peut commencer le diagnostic, proposer un plan, planifier un rendez-vous et suivre ta progression."
                ),
                inline=False,
            )
        else:
            e.add_field(
                name="Type de service — formation",
                value=(
                    "La formation avance étape par étape. Le Formateur explique, montre un exemple, te laisse pratiquer puis valide la progression. "
                    "À la fin, tu peux laisser un avis et garder les ressources utiles pour refaire seul."
                ),
                inline=False,
            )

        e.add_field(
            name="Pour obtenir une réponse plus vite",
            value=(
                "1. Décris l’objectif final.\n"
                "2. Copie le message d’erreur exact s’il y en a un.\n"
                "3. Dis ce que tu as déjà testé.\n"
                "4. Envoie une capture seulement si elle apporte une information utile.\n"
                "5. Évite de ping plusieurs membres du staff : la personne assignée suit ton ticket."
            ),
            inline=False,
        )
        e.set_image(url=BANNER_URL)
        e.set_footer(text=f"Aide Bot • Ticket #{req['id']} • suivi jusqu’à résolution")

        try:
            await channel.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
        except (discord.Forbidden, discord.HTTPException):
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketExperienceCog(bot))
