"""Governance primitives for MCP tool execution.

This module contains the pieces that should run before and after a tool call:
policy authorization, egress decisions, secret materialization, quota shape,
signature checks, span hashing, and kill-switch state.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from fnmatch import fnmatchcase
from typing import Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ToolPolicyDecision(_StrictModel):
    allowed: bool
    code: str | None = None
    reason: str
    missing_scopes: tuple[str, ...] = ()


class ToolPolicy(_StrictModel):
    allowed_tools: tuple[str, ...] = ("*",)
    denied_tools: tuple[str, ...] = ()
    required_scopes: dict[str, tuple[str, ...]] = Field(default_factory=dict)

    def authorize(self, *, tool: str, scopes: tuple[str, ...]) -> ToolPolicyDecision:
        if _matches_any(tool, self.denied_tools):
            return ToolPolicyDecision(
                allowed=False,
                code="LOOP-TH-101",
                reason=f"tool {tool!r} denied by policy",
            )
        if not _matches_any(tool, self.allowed_tools):
            return ToolPolicyDecision(
                allowed=False,
                code="LOOP-TH-101",
                reason=f"tool {tool!r} is not allow-listed",
            )
        required = self.required_scopes.get(tool, ())
        missing = tuple(scope for scope in required if scope not in scopes)
        if missing:
            return ToolPolicyDecision(
                allowed=False,
                code="LOOP-TH-101",
                reason=f"tool {tool!r} missing required scopes",
                missing_scopes=missing,
            )
        return ToolPolicyDecision(allowed=True, reason="allowed")


class EgressRule(_StrictModel):
    host: str
    ports: tuple[int, ...] = Field(default=(443,), min_length=1)
    allow_subdomains: bool = False

    def matches(self, *, host: str, port: int) -> bool:
        host_l = host.lower()
        rule_host = self.host.lower()
        host_match = host_l == rule_host or fnmatchcase(host_l, rule_host)
        if self.allow_subdomains and host_l.endswith(f".{rule_host}"):
            host_match = True
        return host_match and port in self.ports


class EgressDecision(_StrictModel):
    allowed: bool
    code: str | None = None
    reason: str
    host: str
    port: int


class EgressPolicy(_StrictModel):
    rules: tuple[EgressRule, ...]
    block_private_hosts: bool = True

    def authorize_url(self, *, tool: str, url: str) -> EgressDecision:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return EgressDecision(
                allowed=False,
                code="LOOP-TH-201",
                reason=f"tool {tool!r} requested an invalid URL",
                host=host,
                port=port,
            )
        if self.block_private_hosts and _is_private_host(host):
            return EgressDecision(
                allowed=False,
                code="LOOP-TH-201",
                reason=f"tool {tool!r} attempted private-host egress",
                host=host,
                port=port,
            )
        if any(rule.matches(host=host, port=port) for rule in self.rules):
            return EgressDecision(allowed=True, reason="allowed", host=host, port=port)
        return EgressDecision(
            allowed=False,
            code="LOOP-TH-201",
            reason=f"tool {tool!r} attempted egress outside its allowlist",
            host=host,
            port=port,
        )


class ToolQuota(_StrictModel):
    cpu_millis: int = Field(ge=50, le=8_000)
    memory_mb: int = Field(ge=64, le=16_384)
    disk_mb: int = Field(ge=16, le=102_400)
    timeout_ms: int = Field(ge=100, le=600_000)

    def as_cgroup_limits(self) -> dict[str, str]:
        return {
            "cpu.max": f"{self.cpu_millis} 1000",
            "memory.max": f"{self.memory_mb}M",
            "disk.max": f"{self.disk_mb}M",
        }


class SecretReference(_StrictModel):
    name: str
    env_name: str
    ciphertext: str


class ResolvedSecretEnv(_StrictModel):
    env: dict[str, str]
    redacted: dict[str, str]


class KmsDecryptor(Protocol):
    def decrypt(self, ciphertext: str) -> str: ...


class SecretInjector:
    """Decrypt references into boot-time env without returning raw logs."""

    def __init__(self, kms: KmsDecryptor) -> None:
        self._kms = kms

    def inject(self, references: tuple[SecretReference, ...]) -> ResolvedSecretEnv:
        env: dict[str, str] = {}
        redacted: dict[str, str] = {}
        for ref in references:
            env[ref.env_name] = self._kms.decrypt(ref.ciphertext)
            redacted[ref.env_name] = "***"
        return ResolvedSecretEnv(env=env, redacted=redacted)


class ToolSignature(_StrictModel):
    publisher: str
    image_digest: str
    manifest_digest: str
    signature: str


class SignatureVerifier(Protocol):
    def verify(self, signature: ToolSignature) -> bool: ...


class SignedToolVerification(_StrictModel):
    allowed: bool
    code: str | None = None
    reason: str


class SignedToolVerifier:
    def __init__(
        self,
        verifier: SignatureVerifier,
        *,
        allow_unsigned_tools: tuple[str, ...] = (),
    ) -> None:
        self._verifier = verifier
        self._allow_unsigned_tools = allow_unsigned_tools

    def verify(
        self,
        *,
        tool: str,
        signature: ToolSignature | None,
    ) -> SignedToolVerification:
        if signature is None:
            if tool in self._allow_unsigned_tools:
                return SignedToolVerification(allowed=True, reason="unsigned allow-listed")
            return SignedToolVerification(
                allowed=False,
                code="LOOP-TH-501",
                reason=f"tool {tool!r} is unsigned",
            )
        if self._verifier.verify(signature):
            return SignedToolVerification(allowed=True, reason="signature valid")
        return SignedToolVerification(
            allowed=False,
            code="LOOP-TH-501",
            reason=f"tool {tool!r} failed signature verification",
        )


class ToolRevokeEvent(_StrictModel):
    tool: str
    reason: str
    issued_ms: int = Field(ge=0)
    drain_deadline_ms: int = Field(ge=0)


class ToolKillSwitchRegistry:
    def __init__(self) -> None:
        self._events: dict[str, ToolRevokeEvent] = {}

    def revoke(self, event: ToolRevokeEvent) -> None:
        if event.drain_deadline_ms < event.issued_ms:
            raise ValueError("drain deadline must be after issue time")
        self._events[event.tool] = event

    def is_revoked(self, tool: str) -> bool:
        return tool in self._events

    def revoke_event(self, tool: str) -> ToolRevokeEvent | None:
        return self._events.get(tool)

    def should_terminate(self, *, tool: str, now_ms: int) -> bool:
        event = self._events.get(tool)
        return event is not None and now_ms >= event.drain_deadline_ms


class ToolSpan(_StrictModel):
    trace_id: str
    workspace_id: str
    agent_id: str
    tool: str
    args_hash: str
    result_hash: str
    redacted: bool
    duration_ms: int = Field(ge=0)


class ToolObserver:
    def __init__(self) -> None:
        self._spans: list[ToolSpan] = []

    @property
    def spans(self) -> tuple[ToolSpan, ...]:
        return tuple(self._spans)

    def record(
        self,
        *,
        trace_id: str,
        workspace_id: str,
        agent_id: str,
        tool: str,
        args: Mapping[str, object],
        result: Mapping[str, object],
        duration_ms: int,
    ) -> ToolSpan:
        redacted_args, args_redacted = _redact(args)
        redacted_result, result_redacted = _redact(result)
        span = ToolSpan(
            trace_id=trace_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            tool=tool,
            args_hash=_hash_json(redacted_args),
            result_hash=_hash_json(redacted_result),
            redacted=args_redacted or result_redacted,
            duration_ms=duration_ms,
        )
        self._spans.append(span)
        return span


def _matches_any(tool: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern == "*" or fnmatchcase(tool, pattern) for pattern in patterns)


def _is_private_host(host: str) -> bool:
    return (
        host == "localhost"
        or host.startswith("127.")
        or host.startswith("10.")
        or host.startswith("192.168.")
        or host.startswith("169.254.")
        or re.match(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.", host) is not None
    )


def _redact(value: object) -> tuple[object, bool]:
    if isinstance(value, Mapping):
        redacted = False
        out: dict[str, object] = {}
        for key, item in value.items():
            child, was_redacted = _redact(item)
            out[str(key)] = child
            redacted = redacted or was_redacted
        return out, redacted
    if isinstance(value, tuple | list):
        redacted_items: list[object] = []
        redacted = False
        for item in value:
            child, was_redacted = _redact(item)
            redacted_items.append(child)
            redacted = redacted or was_redacted
        return redacted_items, redacted
    if isinstance(value, str) and (_EMAIL_RE.search(value) or _PHONE_RE.search(value)):
        return "[REDACTED]", True
    return value, False


def _hash_json(value: object) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


__all__ = [
    "EgressDecision",
    "EgressPolicy",
    "EgressRule",
    "KmsDecryptor",
    "ResolvedSecretEnv",
    "SecretInjector",
    "SecretReference",
    "SignatureVerifier",
    "SignedToolVerification",
    "SignedToolVerifier",
    "ToolKillSwitchRegistry",
    "ToolObserver",
    "ToolPolicy",
    "ToolPolicyDecision",
    "ToolQuota",
    "ToolRevokeEvent",
    "ToolSignature",
    "ToolSpan",
]
