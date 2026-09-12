import asyncio

from aidebot.cogs.setup_polish_v43 import SetupPolishV43Cog
from aidebot.cogs.setup_server import SetupServerCog


def test_v44_polish_keeps_app_command_callback_immutable():
    original = SetupServerCog.setup_server.callback
    asyncio.run(SetupPolishV43Cog(object()).cog_load())
    assert SetupServerCog.setup_server.callback is original
    assert callable(getattr(SetupServerCog, "_post_setup_v44", None))
