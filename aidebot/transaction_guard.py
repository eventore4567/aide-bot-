from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator


_CONNECTION_LOCKS: dict[int, asyncio.Lock] = {}


def register_connection_lock(conn: Any, lock: asyncio.Lock) -> None:
    _CONNECTION_LOCKS[id(conn)] = lock


def unregister_connection_lock(conn: Any) -> None:
    _CONNECTION_LOCKS.pop(id(conn), None)


@asynccontextmanager
async def guarded_connection(conn: Any) -> AsyncIterator[None]:
    """Serialize explicit multi-statement transactions on one SQLite connection.

    aiosqlite serializes individual statements, not whole application-level
    transactions. Without this guard, two coroutines can interleave between
    BEGIN and COMMIT and trigger `cannot start a transaction within a
    transaction` or accidentally share one transaction boundary.
    """
    lock = _CONNECTION_LOCKS.get(id(conn))
    if lock is None:
        yield
        return
    async with lock:
        yield
