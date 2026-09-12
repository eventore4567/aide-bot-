from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OWNER_CONFIG: dict[str, Any] = {
    "ai_enabled": True,
    "guardian_alerts": True,
    "ai_daily_limit": 25,
}


class OwnerConfigStore:
    """Small persistent configuration store for owner-controlled runtime options."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = asyncio.Lock()

    def _read_sync(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"guilds": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"guilds": {}}
        if not isinstance(data, dict):
            return {"guilds": {}}
        guilds = data.get("guilds")
        if not isinstance(guilds, dict):
            data["guilds"] = {}
        return data

    def _write_sync(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _normalize(raw: dict[str, Any] | None) -> dict[str, Any]:
        raw = raw or {}
        result = dict(DEFAULT_OWNER_CONFIG)
        result["ai_enabled"] = bool(raw.get("ai_enabled", result["ai_enabled"]))
        result["guardian_alerts"] = bool(raw.get("guardian_alerts", result["guardian_alerts"]))
        try:
            limit = int(raw.get("ai_daily_limit", result["ai_daily_limit"]))
        except (TypeError, ValueError):
            limit = int(DEFAULT_OWNER_CONFIG["ai_daily_limit"])
        result["ai_daily_limit"] = max(1, min(100, limit))
        return result

    async def get(self, guild_id: int) -> dict[str, Any]:
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            raw = data.get("guilds", {}).get(str(int(guild_id)))
            return self._normalize(raw if isinstance(raw, dict) else None)

    async def update(self, guild_id: int, **changes: Any) -> dict[str, Any]:
        allowed = {"ai_enabled", "guardian_alerts", "ai_daily_limit"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unsupported owner config keys: {sorted(unknown)}")
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            guilds = data.setdefault("guilds", {})
            current = self._normalize(guilds.get(str(int(guild_id))) if isinstance(guilds, dict) else None)
            current.update(changes)
            current = self._normalize(current)
            guilds[str(int(guild_id))] = current
            await asyncio.to_thread(self._write_sync, data)
            return dict(current)


class OwnerBackupStore:
    """Rotating configuration backups. No message content is stored."""

    def __init__(self, base_dir: str | Path, *, retention: int = 5) -> None:
        self.base_dir = Path(base_dir)
        self.retention = max(1, int(retention))
        self._lock = asyncio.Lock()

    def _guild_dir(self, guild_id: int) -> Path:
        return self.base_dir / str(int(guild_id))

    def _save_sync(
        self,
        guild_id: int,
        guild_name: str,
        snapshot: dict[str, Any],
        *,
        digest: str,
        audit_score: int,
    ) -> Path:
        directory = self._guild_dir(guild_id)
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = directory / f"config-{stamp}.json"
        payload = {
            "schema": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "guild_id": int(guild_id),
            "guild_name": str(guild_name),
            "snapshot_hash": str(digest),
            "audit_score": int(audit_score),
            "contains_messages": False,
            "snapshot": snapshot,
        }
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)

        files = sorted(directory.glob("config-*.json"), key=lambda item: item.name, reverse=True)
        for old in files[self.retention :]:
            try:
                old.unlink()
            except OSError:
                pass
        return path

    async def save(
        self,
        guild_id: int,
        guild_name: str,
        snapshot: dict[str, Any],
        *,
        digest: str,
        audit_score: int,
    ) -> Path:
        async with self._lock:
            return await asyncio.to_thread(
                self._save_sync,
                guild_id,
                guild_name,
                snapshot,
                digest=digest,
                audit_score=audit_score,
            )

    def _latest_sync(self, guild_id: int) -> Path | None:
        directory = self._guild_dir(guild_id)
        if not directory.exists():
            return None
        files = sorted(directory.glob("config-*.json"), key=lambda item: item.name, reverse=True)
        return files[0] if files else None

    async def latest(self, guild_id: int) -> Path | None:
        async with self._lock:
            return await asyncio.to_thread(self._latest_sync, guild_id)

    async def latest_bytes(self, guild_id: int) -> tuple[str, bytes] | None:
        async with self._lock:
            path = await asyncio.to_thread(self._latest_sync, guild_id)
            if path is None:
                return None
            data = await asyncio.to_thread(path.read_bytes)
            return path.name, data
