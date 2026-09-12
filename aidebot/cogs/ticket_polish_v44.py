from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from aidebot.catalog import FORMATIONS
from aidebot.experience_content import BANNER_URL
from aidebot.payments import PAYMENT_LABELS

COLOR = 0x5865F2
PREMIUM = 0x9B59B6
SUCCESS = 0x57F287


def _human_status(status: str) -> str:
    return {
        "open": "Ouvert — en attente de prise en charge",
        "payment_pending": "Activation Premium — paiement à valider",
        "payment_refused": "Paiement refusé",
        "payment_refunded": "Remboursé",
        "completed": "Terminé — avis possible",
        "closed": "Archivé",
    }.get(status, status.replace("_", " ").capitalize())


def _service_name(key: str) -> str:
    if key == "community_help":
        return "Aide gratuite"
    return FORMATIONS.get(key, {}).get("title", "Demande Aide Bot")


def _next_step(req) -> str:
    if req["payment_status"] == "pending":
        return "La Direction vérifie le paiement. Le ticket ne peut pas être pris avant validation."
    if req["status"] == "completed":
        return "L’objectif est marqué terminé. Le membre peut laisser son avis puis archiver le ticket."
    if req["status"] == "closed":
        return "Ce ticket est archivé. Il reste disponible en lecture seule selon les permissions du serveur."
    if not req["trainer_id"]:
        return "Un seul Helper/Formateur autorisé doit cliquer sur **Prendre**. Une seule personne sera assignée au suivi."
    progress = int(req["progress"] or 0)
    data = FORMATIONS.get(req["training_key"])
    if data and progress < len(data.get("steps", [])):
        return f"Responsable assigné : <@{req['trainer_id']}>. Prochaine étape : **{data['steps'][progress]}**."
    return f"Responsable assigné : <@{req['trainer_id']}>. Continuez le diagnostic directement dans ce salon."


def ticket_card(req) -> discord.Embed:
    payment_status = str(req["payment_status"])
    status = str(req["status"])
    premium = payment_status != "not_required" or bool(FORMATIONS.get(req["training_key"], {}).get("vip"))
    e = discord.Embed(
        title=f"Ticket #{req['id']} — {_service_name(req['training_key'])}",
        description=(
            f"<@{req['user_id']}>, voici **le résumé unique de ta demande**. Le staff n’a pas besoin de chercher les informations dans plusieurs messages : "
            "objectif, contexte, état et prochaine étape sont regroupés ici."
        ),
        color=PREMIUM if premium else COLOR,
    )
    objective = str(req["objective"] or "Non précisé").strip()
    e.add_field(name="Ta demande", value=objective[:1024], inline=False)
    e.add_field(
        name="Contexte",
        value=(
            f"**Niveau / contexte :** {str(req['level'] or 'Non précisé')[:240]}\n"
            f"**Disponibilités :** {str(req['availability'] or 'Non précisées')[:240]}\n"
            f"**Formule :** {str(req['budget'] or 'Non précisée')[:240]}"
        ),
        inline=True,
    )
    payment = "Non requis" if payment_status == "not_required" else PAYMENT_LABELS.get(payment_status, payment_status)
    trainer = f"<@{req['trainer_id']}>" if req["trainer_id"] else "Personne pour le moment"
    e.add_field(
        name="Suivi",
        value=(
            f"**État :** {_human_status(status)}\n"
            f"**Responsable :** {trainer}\n"
            f"**Progression :** {int(req['progress'] or 0)}/{int(req['total_steps'] or 1)}\n"
            f"**Paiement :** {payment}"
        ),
        inline=True,
    )
    e.add_field(name="Ce qui se passe maintenant", value=_next_step(req)[:1024], inline=False)
    e.add_field(
        name="Sécurité",
        value="Captures et erreurs sont acceptées si utiles. **Jamais** de token, mot de passe, cookie, code 2FA, code de récupération ou donnée bancaire.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V44 • Un résumé • un responsable • une prochaine étape claire")
    return e


class TicketPolishV44Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _request_for_channel(self, channel: discord.TextChannel):
        for _ in range(15):
            req = await self.bot.db.request_by_channel(channel.id)
            if req is not None:
                return req
            await asyncio.sleep(0.25)
        return None

    async def _find_root_message(self, channel: discord.TextChannel) -> discord.Message | None:
        if self.bot.user is None:
            return None
        for _ in range(12):
            try:
                async for message in channel.history(limit=12, oldest_first=True):
                    if message.author.id != self.bot.user.id or not message.embeds:
                        continue
                    title = message.embeds[0].title or ""
                    if title.startswith("Ticket #") or title == "Nouvelle demande":
                        return message
            except (discord.Forbidden, discord.HTTPException):
                return None
            await asyncio.sleep(0.25)
        return None

    async def _refresh(self, channel: discord.TextChannel) -> None:
        req = await self.bot.db.request_by_channel(channel.id)
        if req is None:
            return
        root = await self._find_root_message(channel)
        if root is None:
            return
        try:
            await root.edit(embed=ticket_card(req))
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("ticket-"):
            return
        req = await self._request_for_channel(channel)
        if req is None:
            return
        root = await self._find_root_message(channel)
        if root is None:
            return
        try:
            await root.edit(embed=ticket_card(req))
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if self.bot.user is None or message.author.id != self.bot.user.id:
            return
        if not isinstance(message.channel, discord.TextChannel):
            return
        req = await self.bot.db.request_by_channel(message.channel.id)
        if req is None:
            return
        text = (message.content or "").casefold()
        signals = (
            "prise en charge par",
            "progression :",
            "demande terminée",
            "ticket archivé",
            "paiement **",
        )
        if not any(signal in text for signal in signals):
            return
        await self._refresh(message.channel)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketPolishV44Cog(bot))
