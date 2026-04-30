"""Pass9 telegram long-poll tests."""

from __future__ import annotations

import asyncio

import pytest
from loop_channels_telegram.long_poll import (
    DEFAULT_LONG_POLL_TIMEOUT_SECONDS,
    PollResult,
    TelegramLongPoller,
)


def _make_poller(updates_batches, handler=None):
    received: list[dict] = []

    async def default_handler(u):
        received.append(u)

    iter_batches = iter(updates_batches)

    async def fake_get_updates(offset, timeout):  # noqa: ASYNC109
        try:
            return next(iter_batches)
        except StopIteration:
            return []

    poller = TelegramLongPoller(
        get_updates=fake_get_updates,
        handler=handler or default_handler,
    )
    return poller, received


@pytest.mark.asyncio
async def test_first_poll_with_no_updates_does_not_advance_offset():
    poller, _ = _make_poller([[]])
    result = await poller.poll_once()
    assert result == PollResult(new_offset=0, delivered=0)
    assert poller.offset == 0


@pytest.mark.asyncio
async def test_offset_advances_to_max_plus_one():
    poller, received = _make_poller(
        [[{"update_id": 5, "message": {"text": "a"}},
          {"update_id": 7, "message": {"text": "b"}}]]
    )
    result = await poller.poll_once()
    assert result.new_offset == 8
    assert result.delivered == 2
    assert len(received) == 2
    assert poller.offset == 8


@pytest.mark.asyncio
async def test_offset_does_not_regress_on_old_update_id():
    poller, received = _make_poller([
        [{"update_id": 10}],
        [{"update_id": 5}],
    ])
    await poller.poll_once()
    assert poller.offset == 11
    await poller.poll_once()
    # Offset is monotonic: max_id 5 < current 11, so new = max(5, 10) + 1 = 11
    assert poller.offset == 11
    assert len(received) == 2


@pytest.mark.asyncio
async def test_error_increments_backoff_counter_and_keeps_offset():
    raises = [True, False]
    batches = iter([[{"update_id": 1}]])

    async def fake_get_updates(offset, timeout):  # noqa: ASYNC109
        if raises and raises.pop(0):
            raise RuntimeError("boom")
        return next(batches)

    received: list[dict] = []

    async def handler(u):
        received.append(u)

    poller = TelegramLongPoller(get_updates=fake_get_updates, handler=handler)
    r1 = await poller.poll_once()
    assert r1.delivered == 0
    assert poller.consecutive_errors == 1
    assert poller.offset == 0
    r2 = await poller.poll_once()
    assert r2.delivered == 1
    assert poller.consecutive_errors == 0
    assert poller.offset == 2


@pytest.mark.asyncio
async def test_missing_update_id_raises():
    poller, _ = _make_poller([[{"no_id_here": True}]])
    with pytest.raises(ValueError):
        await poller.poll_once()


@pytest.mark.asyncio
async def test_handler_runs_for_every_update_in_order():
    seen: list[int] = []

    async def handler(u):
        seen.append(u["update_id"])

    poller, _ = _make_poller(
        [[{"update_id": 1}, {"update_id": 2}, {"update_id": 3}]],
        handler=handler,
    )
    await poller.poll_once()
    assert seen == [1, 2, 3]


@pytest.mark.asyncio
async def test_run_stops_when_stop_called():
    async def fake_get_updates(offset, timeout):  # noqa: ASYNC109
        return []

    async def handler(u):
        pass

    poller = TelegramLongPoller(
        get_updates=fake_get_updates,
        handler=handler,
        error_backoff_seconds=0.01,
    )
    task = asyncio.create_task(poller.run())
    await asyncio.sleep(0.01)
    poller.stop()
    await asyncio.wait_for(task, timeout=1.0)


def test_default_timeout_is_50_seconds():
    assert DEFAULT_LONG_POLL_TIMEOUT_SECONDS == 50
