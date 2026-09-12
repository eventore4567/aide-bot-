from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

import aidebot.public_panels as public_panels
from aidebot.cogs.premium_service_v47 import (
    SERVER_BUILD_KEY,
    PremiumServiceHubView,
    ServerBuildTicketView,
    ServerTemplateChoiceView,
    premium_v47_hub_embed,
    server_build_control_embed,
    server_template_embed,
    _request_unlocked,
)
from aidebot.cogs.setup_server import SetupServerCog
from aidebot.cogs.ticket_experience import PremiumPaymentView
from aidebot.experience_content import BANNER_URL
from aidebot.premium_access import has_premium
from aidebot.ux_text import premium_member_embed

SHOP_CHANNEL = "🛒・shop"
SHOP_TITLE = "Aide Bot — Boutique Premium"


def premium_shop_embed(price: int) -> discord.Embed:
    e = discord.Embed(
        title=SHOP_TITLE,
        description=(
            f"**Pack Premium — {price} Robux**\n\n"
            "Tu n’achètes pas juste un rôle VIP. Le pack débloque un **vrai service** : audit personnalisé, création/configuration de serveur, "
            "support prioritaire, aide bot et production, sécurité, système de tickets, plan personnalisé et ressources avancées."
        ),
        color=0xEB459E,
    )
    e.add_field(
        name="Serveur fait avec toi / pour toi",
        value="5 modèles au choix. Après paiement + autorisation OAuth2, Aide Bot peut créer rôles, catégories, salons, permissions, accueil et tickets sur ton serveur.",
        inline=False,
    )
    e.add_field(
        name="Audit & accompagnement",
        value="Audit serveur/bot, priorités, plan d’amélioration, suivi humain et vérification finale.",
        inline=True,
    )
    e.add_field(
        name="Bot & production",
        value="Architecture, bugs, Railway, SQLite/PostgreSQL, logs, tests, GitHub et déploiement.",
        inline=True,
    )
    e.add_field(
        name="Sécurité & support",
        value="Permissions, anti-raid, webhooks, tickets avancés et support prioritaire.",
        inline=True,
    )
    e.add_field(
        name="Vidéos VIP",
        value="Vidéos directes sélectionnées + bibliothèque technique avancée de 25 sujets.",
        inline=True,
    )
    e.add_field(
        name="Comment ça marche",
        value=(
            "**1.** Achète Premium ici.\n"
            "**2.** Un ticket privé est créé.\n"
            "**3.** La Direction valide le paiement.\n"
            "**4.** Le rôle 💎・VIP est attribué.\n"
            "**5.** Les services Premium deviennent utilisables.\n"
            "**Création serveur :** après validation, Discord te demande une autorisation OAuth2 avant que le bot puisse rejoindre ton serveur."
        ),
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V47 • 2000 Robux doit acheter un service, pas juste un badge")
    return e


class ShopV47View(public_panels.ShopView):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.bot = bot

    @discord.ui.button(
        label="Commander un serveur",
        style=discord.ButtonStyle.primary,
        custom_id="aidebot:v47:shop:server",
        row=1,
    )
    async def server(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            embed=server_template_embed(),
            view=ServerTemplateChoiceView(self.bot),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Voir tout le pack",
        style=discord.ButtonStyle.secondary,
        custom_id="aidebot:v47:shop:full-pack",
        row=1,
    )
    async def full_pack(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if isinstance(interaction.user, discord.Member) and has_premium(interaction.user):
            return await interaction.response.send_message(
                embed=premium_member_embed(interaction.user),
                view=PremiumServiceHubView(self.bot),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=premium_v47_hub_embed(self.bot.settings.vip_price_robux),
            ephemeral=True,
        )


def _install_shop_patch(bot: commands.Bot) -> None:
    public_panels.ShopView = ShopV47View
    public_panels.shop_embed = premium_shop_embed
    public_panels.premium_embed = premium_v47_hub_embed

    # Storefront est déjà chargé quand ce runtime est chargé. Ses fonctions
    # résolvent ces globals à l’exécution, donc on remplace proprement les
    # références sans toucher à app_commands.Command.callback.
    try:
        import aidebot.cogs.storefront as storefront

        storefront.ShopView = ShopV47View
        storefront.shop_embed = premium_shop_embed
    except Exception:
        pass

    # Le setup_server a importé l’ancienne ShopView avant V47 ; on applique donc
    # un upsert final sur le salon shop pour que /setup publie bien la V47.
    if getattr(SetupServerCog, "_aidebot_v47_shop_patched", False):
        return
    original = SetupServerCog._reconcile_channel_permissions

    async def reconcile(self: SetupServerCog, guild: discord.Guild, channel: discord.TextChannel, roles: dict[str, discord.Role]) -> None:
        await original(self, guild, channel, roles)
        if channel.name == SHOP_CHANNEL:
            await self._upsert_panel(
                channel,
                premium_shop_embed(self.bot.settings.vip_price_robux),
                ShopV47View(self.bot),
            )

    SetupServerCog._reconcile_channel_permissions = reconcile
    SetupServerCog._aidebot_v47_shop_patched = True


def _install_payment_unlock_patch() -> None:
    if getattr(PremiumPaymentView, "_aidebot_v47_patched", False):
        return
    original = PremiumPaymentView._transition

    async def transition(self: PremiumPaymentView, interaction: discord.Interaction, target: str) -> None:
        req_before = None
        if interaction.channel is not None:
            req_before = await self.bot.db.request_by_channel(interaction.channel.id)
        previous_payment = str(req_before["payment_status"]) if req_before else ""
        await original(self, interaction, target)

        if (
            target != "paid"
            or req_before is None
            or str(req_before["training_key"]) != SERVER_BUILD_KEY
            or previous_payment == "paid"
            or not isinstance(interaction.channel, discord.TextChannel)
        ):
            return
        refreshed = await self.bot.db.request_by_id(int(req_before["id"]))
        if refreshed is None or str(refreshed["payment_status"]) != "paid":
            return
        cog = self.bot.get_cog("PremiumServiceV47Cog")
        if cog is not None:
            await cog.unlock_server_build_ticket(interaction.channel, refreshed)

    PremiumPaymentView._transition = transition
    PremiumPaymentView._aidebot_v47_patched = True


class PremiumServiceV47RuntimeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        _install_shop_patch(self.bot)
        _install_payment_unlock_patch()
        self.bot.add_view(ShopV47View(self.bot))

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        """Reliable V47 server-order panel; replaces the early V47 race."""
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("ticket-"):
            return
        req = None
        for _ in range(12):
            await asyncio.sleep(0.35)
            req = await self.bot.db.request_by_channel(channel.id)
            if req is not None:
                break
        if req is None or str(req["training_key"]) != SERVER_BUILD_KEY:
            return
        client = channel.guild.get_member(int(req["user_id"]))
        ready = _request_unlocked(req, client)
        try:
            await channel.send(
                embed=server_build_control_embed(req, ready),
                view=ServerBuildTicketView(self.bot),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PremiumServiceV47RuntimeCog(bot))
