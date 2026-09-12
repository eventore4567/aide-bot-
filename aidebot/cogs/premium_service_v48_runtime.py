from __future__ import annotations

from discord.ext import commands

from aidebot.catalog import FORMATIONS
from aidebot.cogs.premium_service_v47 import PREMIUM_SERVICE_FORMS, SERVER_BUILD_KEY

INTERNAL_PREMIUM_PREFIX = "premium_service_"


def _remove_internal_premium_routes_from_training_catalog() -> None:
    """Keep Premium service-only routes out of the public formation catalog.

    V48 reuses TrainingCog's ticket engine for Premium missions, but those internal
    routes are not normal formations and must never appear in TrainingPanel. The
    V48 module registers temporary metadata while it loads; this cleanup runs
    immediately afterwards and again from extension setup for deterministic startup.
    """
    for service_key in PREMIUM_SERVICE_FORMS:
        route = f"{INTERNAL_PREMIUM_PREFIX}{service_key.replace('-', '_')}"
        FORMATIONS.pop(route, None)
    FORMATIONS.pop(SERVER_BUILD_KEY, None)


_remove_internal_premium_routes_from_training_catalog()


async def setup(bot: commands.Bot) -> None:
    _remove_internal_premium_routes_from_training_catalog()
