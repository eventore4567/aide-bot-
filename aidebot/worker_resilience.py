from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class WorkerBatchResult:
    processed: int
    failed: int


async def run_isolated_batch(
    items: Iterable[T],
    callback: Callable[[T], Awaitable[None]],
    on_error: Callable[[T, Exception], Awaitable[None]] | None = None,
) -> WorkerBatchResult:
    """Run independent worker items without letting one failure stop the batch.

    Discord background loops are long-lived. An unhandled exception from one
    guild or one database row must not prevent the remaining work from running
    or kill future iterations of the loop.
    """
    processed = 0
    failed = 0
    for item in items:
        try:
            await callback(item)
            processed += 1
        except Exception as exc:
            failed += 1
            if on_error is not None:
                try:
                    await on_error(item, exc)
                except Exception:
                    # Error reporting must never become a second failure that
                    # stops the worker batch.
                    pass
    return WorkerBatchResult(processed=processed, failed=failed)
