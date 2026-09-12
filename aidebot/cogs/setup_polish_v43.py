from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.cogs.setup_server import SetupServerCog
from aidebot.cogs.training_experience_v42 import training_catalog_embed
from aidebot.experience_content import BANNER_URL


def _training_embed_v43(self: SetupServerCog) -> discord.Embed:
    e = training_catalog_embed()
    e.title = "Aide Bot — Formations & parcours"
    e.description = (
        "Ce salon est le **catalogue interactif des formations**. Le membre choisit un parcours, lit d’abord sa fiche complète, "
        "voit le niveau, la durée, le programme et les ressources, puis ouvre seulement ensuite le formulaire adapté.\n\n"
        + (e.description or "")
    )[:4000]
    e.set_footer(text="Aide Bot V43 • Fiche complète avant inscription • Parcours réellement différents")
    return e


def _staff_embed_v43(self: SetupServerCog) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Cockpit staff",
        description=(
            "Le staff n’a pas besoin d’une longue liste de commandes. Le travail quotidien se fait directement dans les **tickets, candidatures et panneaux**.\n\n"
            "**Tickets** : Prendre → répondre → Étape suivante → Terminer → avis → archivage.\n"
            "**Premium** : vérifier le paiement → bouton de validation → rôle `💎・VIP` automatique.\n"
            "**Recrutement** : candidature complète → Accepter / Refuser → rôle attribué automatiquement si accepté.\n"
            "**Sécurité** : aucun secret utilisateur ne doit être demandé ou copié."
        ),
        color=0xF1C40F,
    )
    e.add_field(
        name="Règle de prise en charge",
        value="Une seule personne est responsable d’un ticket à la fois. La Direction et les administrateurs peuvent superviser les demandes.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V43 • Staff panel-first • Actions sensibles contrôlées")
    return e


def _rules_embed_v43(self: SetupServerCog) -> discord.Embed:
    e = discord.Embed(
        title="Règlement — Aide Bot",
        description=(
            "**Respect** — pas d’insultes, harcèlement, spam ou contenu nuisible.\n"
            "**Sécurité** — jamais de token, mot de passe, cookie, code 2FA ou code de récupération.\n"
            "**Tickets** — une demande précise par ticket ; donne le contexte et ce que tu as déjà essayé.\n"
            "**Premium** — l’achat passe uniquement par `🛒・shop` ou `/buy` ; seule la validation enregistrée par la Direction fait foi.\n"
            "**Staff** — évite les pings multiples ; le membre assigné suit le ticket jusqu’au résultat ou au transfert décidé par un responsable.\n"
            "**Formation** — le but est de comprendre et pouvoir refaire seul, pas seulement copier une réponse."
        ),
        color=0x2B2D31,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V43 • Simple, sécurisé, compréhensible")
    return e


def _setup_success_embed() -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot V43 — configuration prête",
        description=(
            "Le setup vient de terminer sa réconciliation. L’expérience membre est maintenant organisée comme un vrai service : "
            "accueil, centre d’aide, formations, vidéos, support, boutique, recrutement et espace staff ont chacun une fonction claire."
        ),
        color=0x57F287,
    )
    e.add_field(
        name="Parcours membre",
        value="`👋・bienvenue` → `🎓・centre-aide` / `🎓・formations` / `🎫・ouvrir-ticket` / `🛒・shop`",
        inline=False,
    )
    e.add_field(
        name="À tester maintenant",
        value=(
            "**1.** Bienvenue → **Mon espace**\n"
            "**2.** Formations → choisir 2 parcours différents et comparer les fiches/formulaires\n"
            "**3.** Support → choisir Bot puis Serveur et vérifier que les questions changent\n"
            "**4.** Vidéos → changer de catégorie\n"
            "**5.** Premium → vérifier qu’un non-VIP est renvoyé vers la boutique"
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V43 • Relancer /setup met à jour l’existant sans recréer inutilement")
    return e


class SetupPolishV43Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        SetupServerCog._training_embed = _training_embed_v43
        SetupServerCog._staff_embed = _staff_embed_v43
        SetupServerCog._rules_embed = _rules_embed_v43

        command = SetupServerCog.setup_server
        if getattr(command, "_aidebot_v43_wrapped", False):
            return
        original = command.callback

        async def callback(cog: SetupServerCog, interaction: discord.Interaction) -> None:
            await original(cog, interaction)
            # Le callback historique gère lui-même tous les refus. On n’ajoute la
            # carte V43 que lorsqu’une réponse différée/followup est disponible.
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=_setup_success_embed(), ephemeral=True)
            except (discord.HTTPException, discord.NotFound):
                pass

        command.callback = callback
        command._aidebot_v43_wrapped = True


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupPolishV43Cog(bot))
