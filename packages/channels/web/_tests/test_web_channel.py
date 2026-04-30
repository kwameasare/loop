from __future__ import annotations

import json
from uuid import uuid4

import pytest
from loop_channels_core import (
    InboundEvent,
    InboundEventKind,
    OutboundFrame,
    OutboundFrameKind,
    from_async_generator,
)
from loop_channels_web import WebChannel, sse_serialise


def _event() -> InboundEvent:
    return InboundEvent(
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
        kind=InboundEventKind.MESSAGE,
        text="hello",
    )


def test_sse_serialise_format() -> None:
    cid = uuid4()
    frame = OutboundFrame(
        conversation_id=cid,
        kind=OutboundFrameKind.AGENT_TOKEN,
        text="hi",
        sequence=0,
    )
    out = sse_serialise(frame).decode("utf-8")
    assert out.startswith("event: agent_token\n")
    assert "id: " in out
    assert out.endswith("\n\n")
    # data line is JSON
    data_line = next(line for line in out.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload["text"] == "hi"
    assert payload["sequence"] == 0


@pytest.mark.asyncio
async def test_web_channel_streams_sse_bytes() -> None:
    cid = uuid4()

    async def dispatcher(event):
        for i, kind in enumerate(
            [
                OutboundFrameKind.AGENT_TOKEN,
                OutboundFrameKind.AGENT_TOKEN,
                OutboundFrameKind.DONE,
            ]
        ):
            yield OutboundFrame(conversation_id=cid, kind=kind, text=str(i), sequence=i)

    ch = WebChannel()
    await ch.start(from_async_generator(dispatcher))
    chunks = [c async for c in ch.handle(_event())]
    assert len(chunks) == 3
    assert b"event: agent_token" in chunks[0]
    assert b"event: done" in chunks[2]


@pytest.mark.asyncio
async def test_handle_before_start_raises() -> None:
    ch = WebChannel()
    with pytest.raises(RuntimeError):
        async for _ in ch.handle(_event()):
            break


@pytest.mark.asyncio
async def test_collect_returns_frames() -> None:
    cid = uuid4()

    async def dispatcher(event):
        yield OutboundFrame(
            conversation_id=cid, kind=OutboundFrameKind.AGENT_MESSAGE, text="ok", sequence=0
        )

    ch = WebChannel()
    await ch.start(from_async_generator(dispatcher))
    frames = await ch.collect(_event())
    assert len(frames) == 1
    assert frames[0].text == "ok"
