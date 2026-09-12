from __future__ import annotations

from discord.ext import commands

from aidebot.catalog import FORMATIONS
from aidebot.cogs.premium_service_v47 import PREMIUM_SERVICE_FORMS, SERVER_BUILD_KEY


def _remove_internal_premium_routes_from_training_catalog() -> None:
    """V48 service tickets use TrainingCog's ticket engine, not the public training selector.

    premium_service_v48 temporarily registers metadata while it is imported so ticket
    creation can reuse the same internal engine. Those routes must not remain in the
    public FORMATIONS catalog because TrainingPanel expects a dedicated TRAINING_FORMS
    modal for every catalog entry.
    """
    for service_key in PREMIUM_SERVICE_FORMS:
        FORMATIONS.pop(f"premium_service_{service_key.replace('-', '_')}", None)
    FORMATIONS.pop(SERVER_BUILD_KEY, None)


_remove_internal_premium_routes_from_training_catalog()


async def setup(bot: commands.Bot) -> None:
    _remove_internal_premium_routes_from_training_catalog()
