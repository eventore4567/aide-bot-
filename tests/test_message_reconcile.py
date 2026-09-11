import asyncio

import discord

from aidebot.message_reconcile import upsert_bot_embed_by_title


class FakeAuthor:
    def __init__(self, user_id: int):
        self.id = user_id


class FakeMessage:
    _next_id = 1

    def __init__(self, author_id: int, embed: discord.Embed):
        self.author = FakeAuthor(author_id)
        self.embeds = [embed]
        self.id = FakeMessage._next_id
        FakeMessage._next_id += 1
        self.edits = 0

    async def edit(self, *, embed: discord.Embed):
        self.embeds = [embed]
        self.edits += 1


class FakeChannel:
    def __init__(self):
        self.messages: list[FakeMessage] = []
        self.send_count = 0

    def history(self, *, limit: int):
        async def iterator():
            for message in reversed(self.messages[-limit:]):
                yield message
        return iterator()

    async def send(self, *, embed: discord.Embed):
        self.send_count += 1
        message = FakeMessage(42, embed)
        self.messages.append(message)
        return message


def test_upsert_creates_once_then_updates_same_panel():
    async def scenario():
        channel = FakeChannel()
        first = discord.Embed(title="Centre d’apprentissage", description="v1")
        second = discord.Embed(title="Centre d’apprentissage", description="v2")

        created = await upsert_bot_embed_by_title(channel, bot_user_id=42, embed=first)
        updated = await upsert_bot_embed_by_title(channel, bot_user_id=42, embed=second)

        assert created.action == "created"
        assert updated.action == "updated"
        assert channel.send_count == 1
        assert len(channel.messages) == 1
        assert channel.messages[0].embeds[0].description == "v2"
        assert channel.messages[0].edits == 1

    asyncio.run(scenario())


def test_upsert_ignores_same_title_from_non_bot_author():
    async def scenario():
        channel = FakeChannel()
        channel.messages.append(FakeMessage(99, discord.Embed(title="Bienvenue sur Aide Bot", description="fake")))

        result = await upsert_bot_embed_by_title(
            channel,
            bot_user_id=42,
            embed=discord.Embed(title="Bienvenue sur Aide Bot", description="official"),
        )

        assert result.action == "created"
        assert channel.send_count == 1
        assert len(channel.messages) == 2
        assert channel.messages[-1].embeds[0].description == "official"

    asyncio.run(scenario())
