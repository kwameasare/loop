"""Voice provider failover (S389) — graceful degrade on outages.

The voice runtime calls three external providers per turn (ASR, LLM,
TTS). Any of them can fail or slow down. We want the call to keep
working with audible-but-degraded quality rather than hang up.

Strategy:

* Each provider has a *primary* and zero or more *fallbacks*, in
  preference order.
* A :class:`ProviderHealth` struct tracks consecutive failures per
  provider with a sliding-window count.
* :class:`ProviderFailover` picks the highest-preference provider
  whose health is currently ``HEALTHY`` (failures below threshold)
  *or* falls through the list, ending in a final
  :class:`ProviderFailoverExhausted` if everything is down.
* A successful call resets the failure count; a failure increments
  it. After ``cooldown_seconds`` a provider becomes eligible again
  even if its count is still over threshold (slow recovery).

The module is provider-agnostic: it takes a list of
:class:`ProviderEntry` and an async ``call`` that the caller
supplies; it never imports an SDK.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar

__all__ = [
    "ProviderEntry",
    "ProviderFailover",
    "ProviderFailoverExhausted",
    "ProviderHealth",
    "ProviderState",
]


T = TypeVar("T")


class ProviderState(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    COOLDOWN = "cooldown"


class ProviderFailoverExhausted(RuntimeError):  # noqa: N818 - public name w/o Error suffix is intentional
    """All providers are unhealthy and none reached cooldown again."""

    def __init__(self, *, attempted: Sequence[str], last_error: BaseException | None) -> None:
        self.attempted = tuple(attempted)
        self.last_error = last_error
        super().__init__(
            f"all {len(attempted)} providers failed: {list(attempted)!r}"
        )


@dataclass
class ProviderEntry:
    """A single provider in the failover chain.

    ``id`` is the stable identifier (``deepgram``, ``whisper-cpp``).
    ``call`` is an async callable that performs one request; the
    caller closes over the actual SDK and audio/text payload.
    """

    id: str
    call: Callable[..., Awaitable[object]]


@dataclass
class ProviderHealth:
    """Mutable health tracker per provider id."""

    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    consecutive_failures: int = 0
    last_failure_at: float | None = None
    last_success_at: float | None = None

    def state(self, *, now: float) -> ProviderState:
        if self.consecutive_failures < self.failure_threshold:
            return ProviderState.HEALTHY
        if self.last_failure_at is None:
            return ProviderState.UNHEALTHY
        if now - self.last_failure_at >= self.cooldown_seconds:
            return ProviderState.COOLDOWN
        return ProviderState.UNHEALTHY

    def record_success(self, *, now: float) -> None:
        self.consecutive_failures = 0
        self.last_success_at = now

    def record_failure(self, *, now: float) -> None:
        self.consecutive_failures += 1
        self.last_failure_at = now


@dataclass
class ProviderFailover:
    """Failover-with-cooldown for a list of providers."""

    providers: list[ProviderEntry]
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    _health: dict[str, ProviderHealth] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if not self.providers:
            raise ValueError("ProviderFailover requires at least one provider")
        seen: set[str] = set()
        for p in self.providers:
            if p.id in seen:
                raise ValueError(f"duplicate provider id: {p.id!r}")
            seen.add(p.id)
            self._health[p.id] = ProviderHealth(
                failure_threshold=self.failure_threshold,
                cooldown_seconds=self.cooldown_seconds,
            )

    def health(self, provider_id: str) -> ProviderHealth:
        return self._health[provider_id]

    def state(self, provider_id: str, *, now: float) -> ProviderState:
        return self._health[provider_id].state(now=now)

    async def call(
        self,
        *args: object,
        now_fn: Callable[[], float],
        **kwargs: object,
    ) -> object:
        """Try providers in order until one succeeds or all fail.

        ``now_fn`` is supplied by the caller so tests can pin time.
        Production passes ``time.monotonic``.
        """
        attempted: list[str] = []
        last_error: BaseException | None = None
        for provider in self.providers:
            now = now_fn()
            state = self._health[provider.id].state(now=now)
            if state is ProviderState.UNHEALTHY:
                continue
            attempted.append(provider.id)
            try:
                result = await provider.call(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                self._health[provider.id].record_failure(now=now_fn())
                continue
            self._health[provider.id].record_success(now=now_fn())
            return result
        raise ProviderFailoverExhausted(
            attempted=attempted, last_error=last_error
        )
