from __future__ import annotations

from discord.ext import commands

import aidebot.cogs.premium_service_v49 as v49

# Capture V49 renderers before V50 redirects the compatibility symbols.  This
# keeps V50 renderers acyclic even after the old V49 names point at V50.
_V49_HUB_EMBED = v49.premium_v49_hub_embed
_V49_SHOP_EMBED = v49.premium_shop_embed

import aidebot.cogs.premium_service_v50 as v50  # noqa: E402


def premium_v50_hub_embed(price: int):
    e = _V49_HUB_EMBED(max(price, v50.ELITE_PRICE_ROBUX))
    e.title = "Aide Bot — Premium Elite V50"
    e.description = (
        (e.description or "")
        + "\n\n**V50 ajoute un vrai standard de livraison :** cahier des charges avant achat, une mission active à la fois, critères d'acceptation, ajustements client et validation du résultat."
    )[:4000]
    e.add_field(
        name="Une mission = un dossier propre",
        value="Chaque réalisation possède un objectif, des livrables et des critères d'acceptation. Pas de tickets Elite lancés dans tous les sens.",
        inline=False,
    )
    e.set_footer(text="Aide Bot V50 • Elite = cadrage → exécution → validation → dossier final")
    return e


def premium_shop_embed(price: int):
    price = max(price, v50.ELITE_PRICE_ROBUX)
    e = _V49_SHOP_EMBED(price)
    e.title = "Aide Bot — Premium Elite 10K"
    e.description = (
        f"**Premium Elite — {price:,} Robux**\n\n".replace(",", " ")
        + "Avant le paiement, Aide Bot demande maintenant un **cahier des charges** : projet, situation actuelle, résultat attendu et critères d'acceptation. "
        "Le but est que le client sache exactement ce qu'il achète et que le staff sache exactement ce qu'il doit livrer."
    )
    e.add_field(name="Résultat, pas juste accès", value="Audit 360°, réalisation, tests, validation client et dossier final. Le rôle VIP n'est que la clé d'accès au service.", inline=False)
    e.add_field(name="Organisation", value="Une mission de réalisation active par membre. Les audits, vidéos et ressources Elite restent utilisables en parallèle.", inline=False)
    e.set_image(url=v50.BANNER_URL)
    e.set_footer(text="Aide Bot V50 • 10 000 Robux • cahier des charges + réalisation + validation")
    return e


# Replace the two renderers before the cog's cog_load installs its compatibility
# redirects into V48/V49/public_panels.
v50.premium_v50_hub_embed = premium_v50_hub_embed
v50.premium_shop_embed = premium_shop_embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(v50.PremiumServiceV50Cog(bot))
