from __future__ import annotations

from uuid import uuid4

import pytest
from loop_channels_core import (
    InboundEvent,
    InboundEventKind,
    OutboundFrame,
    OutboundFrameKind,
    from_async_generator,
    from_list_factory,
)
from pydantic import ValidationError


def _event(text: str = "hi") -> InboundEvent:
    return InboundEvent(
        workspace_id=uuid4(),
        agent_id=uuid4(),
        conversation_id=uuid4(),
        kind=InboundEventKind.MESSAGE,
        text=text,
    )


def _frame(seq: int, kind: OutboundFrameKind = OutboundFrameKind.AGENT_TOKEN) -> OutboundFrame:
    return OutboundFrame(conversation_id=uuid4(), kind=kind, text="x", sequence=seq)


@pytest.mark.asyncio
async def test_from_async_generator_dispatcher() -> None:
    async def gen(event):
        yield _frame(0)
        yield _frame(1)

    d = from_async_generator(gen)
    out = [f async for f in d.dispatch(_event())]
    assert [f.sequence for f in out] == [0, 1]


@pytest.mark.asyncio
async def test_from_list_factory_dispatcher() -> None:
    async def factory(event):
        return [_frame(0), _frame(1, OutboundFrameKind.DONE)]

    d = from_list_factory(factory)
    out = [f async for f in d.dispatch(_event())]
    assert out[-1].kind is OutboundFrameKind.DONE


def test_inbound_event_strict_frozen() -> None:
    e = _event()
    with pytest.raises(ValidationError):
        e.text = "mutated"  # type: ignore[misc]
