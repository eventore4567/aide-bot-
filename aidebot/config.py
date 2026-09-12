from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    token: str | None
    guild_id: int | None
    db_path: str
    invite_validation_hours: int
    vip_price_robux: int

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        raw_guild = os.getenv("GUILD_ID", "").strip()
        return cls(
            token=os.getenv("DISCORD_TOKEN") or None,
            guild_id=int(raw_guild) if raw_guild.isdigit() else None,
            db_path=os.getenv("AIDEBOT_DB_PATH", "data/aidebot.db"),
            invite_validation_hours=max(1, int(os.getenv("INVITE_VALIDATION_HOURS", "24"))),
            vip_price_robux=max(0, int(os.getenv("VIP_PRICE_ROBUX", "10000"))),
        )
