from __future__ import annotations

from dataclasses import dataclass

import discord


@dataclass(frozen=True)
class ReconcileResult:
    checked: bool
    action: str
    message_id: int | None = None


async def find_bot_embed_by_title(
    channel: discord.TextChannel,
    *,
    bot_user_id: int,
    title: str,
    limit: int = 100,
) -> tuple[bool, discord.Message | None]:
    """Find the most recent bot-authored embed with an exact title.

    Returns ``(False, None)`` when history could not be inspected. Callers must
    treat that as fail-closed and avoid creating a possible duplicate.
    """
    try:
        async for message in channel.history(limit=limit):
            if message.author.id != bot_user_id:
                continue
            if any(item.title == title for item in message.embeds):
                return True, message
    except (discord.Forbidden, discord.HTTPException):
        return False, None
    return True, None


async def upsert_bot_embed_by_title(
    channel: discord.TextChannel,
    *,
    bot_user_id: int,
    embed: discord.Embed,
) -> ReconcileResult:
    title = embed.title or ""
    checked, existing = await find_bot_embed_by_title(
        channel,
        bot_user_id=bot_user_id,
        title=title,
    )
    if existing is not None:
        try:
            await existing.edit(embed=embed)
            return ReconcileResult(True, "updated", existing.id)
        except (discord.Forbidden, discord.HTTPException):
            return ReconcileResult(True, "failed", existing.id)

    if not checked:
        return ReconcileResult(False, "skipped", None)

    try:
        created = await channel.send(embed=embed)
        return ReconcileResult(True, "created", created.id)
    except (discord.Forbidden, discord.HTTPException):
        return ReconcileResult(True, "failed", None)
