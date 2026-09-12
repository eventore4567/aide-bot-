from __future__ import annotations

import discord

from aidebot.experience_content import BANNER_URL


def missing_premium_embed(shop_channel: discord.TextChannel | None = None) -> discord.Embed:
    destination = shop_channel.mention if shop_channel else "`🛒・shop`"
    e = discord.Embed(
        title="Abonnement Premium requis",
        description=(
            "Cette partie est réservée aux membres qui possèdent le rôle **💎・VIP**.\n\n"
            f"Pour obtenir l’accès, ouvre {destination} ou utilise **`/buy`**, puis clique sur **Acheter Premium**. "
            "Un ticket d’activation est créé ; après validation du paiement par l’équipe, le rôle VIP est attribué automatiquement."
        ),
        color=0xED4245,
    )
    e.add_field(
        name="Tu gardes quoi gratuitement ?",
        value="Les guides, la bibliothèque vidéo, les formations classiques et les tickets d’aide restent disponibles sans Premium.",
        inline=False,
    )
    e.add_field(
        name="Important",
        value="Premium ne s’achète jamais depuis un ticket d’aide ou un bouton de formation. **La boutique est le seul point d’achat.**",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot • Achat dans la boutique • Accès après validation")
    return e


def premium_member_embed(member: discord.Member) -> discord.Embed:
    e = discord.Embed(
        title="Ton espace Premium est actif",
        description=(
            f"{member.mention}, ton rôle **💎・VIP** est actif. Tu peux utiliser les parcours Premium sans ouvrir un nouveau ticket de paiement.\n\n"
            "Va dans `🎓・formations`, choisis le parcours Premium qui correspond à ton projet, lis sa fiche détaillée puis remplis son formulaire spécifique."
        ),
        color=0x9B59B6,
    )
    e.add_field(
        name="Accès débloqués",
        value="Accompagnement sur mesure • Serveur professionnel • Bot avancé • Sécurité avancée • audits et suivi personnalisé.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot Premium • Rôle VIP actif")
    return e
