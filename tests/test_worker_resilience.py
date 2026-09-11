import asyncio

from aidebot.worker_resilience import run_isolated_batch


def test_worker_batch_continues_after_item_failure():
    async def run():
        seen = []
        errors = []

        async def callback(item: int) -> None:
            if item == 2:
                raise RuntimeError("boom")
            seen.append(item)

        async def on_error(item: int, exc: Exception) -> None:
            errors.append((item, type(exc).__name__))

        result = await run_isolated_batch([1, 2, 3], callback, on_error)
        assert seen == [1, 3]
        assert errors == [(2, "RuntimeError")]
        assert result.processed == 2
        assert result.failed == 1

    asyncio.run(run())


def test_error_reporter_failure_does_not_stop_batch():
    async def run():
        seen = []

        async def callback(item: int) -> None:
            if item == 1:
                raise ValueError("bad item")
            seen.append(item)

        async def broken_reporter(item: int, exc: Exception) -> None:
            raise RuntimeError("logger unavailable")

        result = await run_isolated_batch([1, 2, 3], callback, broken_reporter)
        assert seen == [2, 3]
        assert result.processed == 2
        assert result.failed == 1

    asyncio.run(run())


def test_empty_worker_batch_is_clean():
    async def run():
        async def callback(item) -> None:
            raise AssertionError("must not be called")

        result = await run_isolated_batch([], callback)
        assert result.processed == 0
        assert result.failed == 0

    asyncio.run(run())
