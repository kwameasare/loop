"""Tests for pass3 alert delivery dispatcher (S291)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from loop_control_plane.alerts import (
    Alert,
    AlertDispatcher,
    AlertRule,
    InMemoryAlertSink,
)


def _alert(severity: str = "warning") -> Alert:
    rule = AlertRule(
        name="r1",
        metric="m",
        op=">",
        threshold=1.0,
        severity=severity,  # type: ignore[arg-type]
    )
    return Alert(rule=rule, observed=2.0, message="r1 fired")


def test_dispatcher_fans_out_to_all_matching_sinks() -> None:
    sink_a = InMemoryAlertSink(name="a")
    sink_b = InMemoryAlertSink(name="b")
    dispatcher = AlertDispatcher(sinks=(sink_a, sink_b))
    results = asyncio.run(dispatcher.dispatch((_alert(),)))
    assert len(results) == 2
    assert all(r.delivered for r in results)
    assert len(sink_a.delivered) == 1
    assert len(sink_b.delivered) == 1


def test_dispatcher_filters_by_severity_acceptance() -> None:
    critical_only = InMemoryAlertSink(name="pager", accepts=frozenset({"critical"}))
    dispatcher = AlertDispatcher(sinks=(critical_only,))
    results = asyncio.run(
        dispatcher.dispatch((_alert(severity="warning"), _alert(severity="critical")))
    )
    delivered = [r for r in results if r.delivered]
    assert len(delivered) == 1
    assert delivered[0].alert.rule.severity == "critical"
    assert len(critical_only.delivered) == 1


@dataclass
class _ExplodingSink:
    name: str = "boom"
    accepts: frozenset = field(default_factory=lambda: frozenset({"info", "warning", "critical"}))

    async def send(self, alert: Alert) -> None:
        raise RuntimeError("network down")


def test_dispatcher_isolates_sink_failure() -> None:
    good = InMemoryAlertSink(name="ok")
    dispatcher = AlertDispatcher(sinks=(_ExplodingSink(), good))
    results = asyncio.run(dispatcher.dispatch((_alert(),)))
    assert len(results) == 2
    by_sink = {r.sink: r for r in results}
    assert by_sink["boom"].delivered is False
    assert "RuntimeError" in by_sink["boom"].error
    assert by_sink["ok"].delivered is True
    assert len(good.delivered) == 1


def test_dispatcher_with_no_alerts_returns_empty() -> None:
    dispatcher = AlertDispatcher(sinks=(InMemoryAlertSink(name="a"),))
    results = asyncio.run(dispatcher.dispatch(()))
    assert results == ()


def test_dispatcher_with_no_sinks_is_noop() -> None:
    dispatcher = AlertDispatcher(sinks=())
    results = asyncio.run(dispatcher.dispatch((_alert(),)))
    assert results == ()
