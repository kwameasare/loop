"""Typed errors for loop-tool-host. All carry LOOP-TH-NNN codes."""

from __future__ import annotations


class ToolHostError(Exception):
    """Base for every tool-host failure."""

    code: str = "LOOP-TH-000"


class SandboxStartupError(ToolHostError):
    """A sandbox could not be created (image pull failure, kata-runtime
    unavailable, image hash mismatch, ...)."""

    code = "LOOP-TH-001"


class SandboxBusyError(ToolHostError):
    """The pool is at ``max_size`` and no idle sandbox is available
    within the caller's wait budget."""

    code = "LOOP-TH-002"


__all__ = [
    "SandboxBusyError",
    "SandboxStartupError",
    "ToolHostError",
]
