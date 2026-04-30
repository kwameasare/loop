"""EmailSender Protocol parity test harness (S779).

Loop ships three sender backends (SES, Resend, SMTP) plus an
in-process fake. To keep them interchangeable, we publish a single
**parity spec**: a callable that takes any object satisfying the
``EmailSender`` Protocol and runs a checklist of behavioural
assertions. Each backend's test module imports the spec and calls
it with its own factory.

The spec is the contract; the protocol is the surface.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class EmailSenderError(RuntimeError):
    """Backend-agnostic send failure."""


@dataclass(frozen=True, slots=True)
class OutboundEmail:
    """Wire-format-agnostic outbound email envelope."""

    from_address: str
    to_addresses: tuple[str, ...]
    subject: str
    body_text: str
    headers: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class SendResult:
    """Backend response surfaced to the caller."""

    message_id: str
    backend: str


@runtime_checkable
class EmailSender(Protocol):
    """Surface every email backend MUST implement."""

    @property
    def backend_name(self) -> str: ...

    async def send(self, email: OutboundEmail) -> SendResult: ...


@dataclass(slots=True)
class InMemoryEmailSender:
    """Reference implementation used by the parity spec itself."""

    backend_name: str = "in-memory"
    sent: list[OutboundEmail] = field(default_factory=list)
    fail_subject: str | None = None
    next_id: int = 0

    async def send(self, email: OutboundEmail) -> SendResult:
        if not email.from_address or not email.to_addresses:
            raise EmailSenderError("from/to required")
        if self.fail_subject and email.subject == self.fail_subject:
            raise EmailSenderError(f"forced failure on subject {email.subject!r}")
        self.next_id += 1
        self.sent.append(email)
        return SendResult(
            message_id=f"in-memory-{self.next_id}", backend=self.backend_name
        )


SenderFactory = Callable[[], EmailSender]


@dataclass(frozen=True, slots=True)
class ParityCheck:
    name: str
    description: str


PARITY_CHECKS: tuple[ParityCheck, ...] = (
    ParityCheck("backend_name", "exposes a non-empty backend_name"),
    ParityCheck("send_returns_id", "send() returns a SendResult with a non-empty id"),
    ParityCheck("rejects_empty_to", "send() rejects empty to_addresses"),
    ParityCheck("rejects_empty_from", "send() rejects empty from_address"),
    ParityCheck("preserves_headers", "custom headers reach the backend (best-effort)"),
)


@dataclass(frozen=True, slots=True)
class ParityFailure:
    check: str
    detail: str


async def run_parity(
    factory: SenderFactory,
    *,
    sample: OutboundEmail | None = None,
) -> list[ParityFailure]:
    """Run the parity spec against ``factory()`` and return failures.

    Empty list means total parity. Individual backends will use this
    to assert ``await run_parity(...) == []`` in their test suites.
    """
    failures: list[ParityFailure] = []
    sender = factory()
    if not getattr(sender, "backend_name", ""):
        failures.append(ParityFailure("backend_name", "backend_name is empty"))

    msg = sample or OutboundEmail(
        from_address="from@example.com",
        to_addresses=("to@example.com",),
        subject="hello",
        body_text="hi",
        headers=(("X-Loop-Trace", "abc"),),
    )

    try:
        result = await sender.send(msg)
        if not result.message_id:
            failures.append(ParityFailure("send_returns_id", "empty message_id"))
        if not result.backend:
            failures.append(ParityFailure("send_returns_id", "empty backend"))
    except EmailSenderError as exc:
        failures.append(ParityFailure("send_returns_id", f"send raised: {exc}"))

    bad_to = OutboundEmail(
        from_address="x@example.com",
        to_addresses=(),
        subject="x",
        body_text="x",
    )
    try:
        await sender.send(bad_to)
        failures.append(ParityFailure("rejects_empty_to", "send accepted empty to"))
    except EmailSenderError:
        pass
    except Exception as exc:
        failures.append(
            ParityFailure("rejects_empty_to", f"raised non-EmailSenderError: {exc!r}")
        )

    bad_from = OutboundEmail(
        from_address="",
        to_addresses=("x@example.com",),
        subject="x",
        body_text="x",
    )
    try:
        await sender.send(bad_from)
        failures.append(ParityFailure("rejects_empty_from", "send accepted empty from"))
    except EmailSenderError:
        pass
    except Exception as exc:
        failures.append(
            ParityFailure("rejects_empty_from", f"raised non-EmailSenderError: {exc!r}")
        )

    return failures


__all__ = [
    "PARITY_CHECKS",
    "EmailSender",
    "EmailSenderError",
    "InMemoryEmailSender",
    "OutboundEmail",
    "ParityCheck",
    "ParityFailure",
    "SendResult",
    "SenderFactory",
    "run_parity",
]
