"""SMS opt-in and opt-out compliance handling."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ComplianceAction(StrEnum):
    ALLOW = "allow"
    BLOCKED = "blocked"
    HELP = "help"
    OPT_IN = "opt_in"
    OPT_OUT = "opt_out"


class ComplianceDecision(_StrictModel):
    action: ComplianceAction
    allowed: bool
    response_text: str | None = None


class SmsConsentStore(Protocol):
    def is_opted_out(self, *, msisdn: str) -> bool: ...

    def opt_out(self, *, msisdn: str) -> None: ...

    def opt_in(self, *, msisdn: str) -> None: ...


class InMemorySmsConsentStore:
    def __init__(self) -> None:
        self._opted_out: set[str] = set()

    def is_opted_out(self, *, msisdn: str) -> bool:
        return msisdn in self._opted_out

    def opt_out(self, *, msisdn: str) -> None:
        self._opted_out.add(msisdn)

    def opt_in(self, *, msisdn: str) -> None:
        self._opted_out.discard(msisdn)


class ComplianceKeywordHandler:
    def __init__(
        self,
        store: SmsConsentStore,
        *,
        stop_text: str = "You are opted out. Reply START to resume.",
        start_text: str = "You are opted in. Reply STOP to opt out.",
        help_text: str = "Reply STOP to opt out, START to opt in, or ask your question.",
    ) -> None:
        self._store = store
        self._stop_text = stop_text
        self._start_text = start_text
        self._help_text = help_text

    def decide(self, *, msisdn: str, text: str) -> ComplianceDecision:
        keyword = text.strip().upper()
        if keyword in {"STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"}:
            self._store.opt_out(msisdn=msisdn)
            return ComplianceDecision(
                action=ComplianceAction.OPT_OUT,
                allowed=False,
                response_text=self._stop_text,
            )
        if keyword in {"START", "YES", "UNSTOP"}:
            self._store.opt_in(msisdn=msisdn)
            return ComplianceDecision(
                action=ComplianceAction.OPT_IN,
                allowed=False,
                response_text=self._start_text,
            )
        if keyword == "HELP":
            return ComplianceDecision(
                action=ComplianceAction.HELP,
                allowed=False,
                response_text=self._help_text,
            )
        if self._store.is_opted_out(msisdn=msisdn):
            return ComplianceDecision(
                action=ComplianceAction.BLOCKED,
                allowed=False,
                response_text=self._stop_text,
            )
        return ComplianceDecision(action=ComplianceAction.ALLOW, allowed=True)


__all__ = [
    "ComplianceAction",
    "ComplianceDecision",
    "ComplianceKeywordHandler",
    "InMemorySmsConsentStore",
    "SmsConsentStore",
]
