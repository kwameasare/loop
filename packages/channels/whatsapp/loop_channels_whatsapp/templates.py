"""WhatsApp Business template messages (S346).

Outside the 24-hour customer-care window WA only allows pre-approved
*template* messages. The studio's template browser reads from this
registry; the send-template tool validates parameters against it.

A template has a fixed body with ``{{1}}``, ``{{2}}`` placeholders. We
validate parameter count + type (str only) at registration *and* at send
time so a malformed agent action fails fast with a typed error rather
than producing a 400 from Meta's API at the worst possible moment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

_PLACEHOLDER_RE = re.compile(r"\{\{(\d+)\}\}")


class TemplateStatus(StrEnum):
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


class TemplateCategory(StrEnum):
    MARKETING = "marketing"
    UTILITY = "utility"
    AUTHENTICATION = "authentication"


class TemplateError(RuntimeError):
    """Template registration or rendering failed."""


class TemplateSpec(BaseModel):
    """A registered WhatsApp template."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1, max_length=512)
    language: str = Field(min_length=2, max_length=8)  # e.g. en_US
    category: TemplateCategory
    status: TemplateStatus
    body: str = Field(min_length=1)
    parameter_count: int = Field(ge=0)


def _placeholder_indices(body: str) -> list[int]:
    return [int(m.group(1)) for m in _PLACEHOLDER_RE.finditer(body)]


def parse_parameter_count(body: str) -> int:
    """Return the number of distinct ``{{N}}`` placeholders in ``body``.

    Indices must be 1..N contiguous (matches Meta's WA validation rules);
    any gap raises ``TemplateError``.
    """
    indices = _placeholder_indices(body)
    if not indices:
        return 0
    distinct = sorted(set(indices))
    if distinct != list(range(1, len(distinct) + 1)):
        raise TemplateError(
            f"placeholder indices must be 1..N contiguous; got {distinct}"
        )
    return len(distinct)


def render_template(spec: TemplateSpec, parameters: list[str]) -> str:
    """Substitute ``parameters`` into ``spec.body``.

    Parameters are positional, 1-indexed. Count must match
    ``spec.parameter_count`` exactly; values must be non-empty strings.
    """
    if len(parameters) != spec.parameter_count:
        raise TemplateError(
            f"template {spec.name!r} expects {spec.parameter_count} parameters, "
            f"got {len(parameters)}"
        )
    for i, p in enumerate(parameters, start=1):
        if not isinstance(p, str):
            raise TemplateError(f"parameter {i} must be a str, got {type(p).__name__}")
        if not p.strip():
            raise TemplateError(f"parameter {i} must be non-empty")

    def _sub(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        return parameters[idx - 1]

    return _PLACEHOLDER_RE.sub(_sub, spec.body)


@dataclass(slots=True)
class TemplateRegistry:
    """In-memory store of WA template specs, keyed by ``(name, language)``."""

    _specs: dict[tuple[str, str], TemplateSpec]

    def __init__(self) -> None:
        self._specs = {}

    def register(self, spec: TemplateSpec) -> TemplateSpec:
        declared = parse_parameter_count(spec.body)
        if declared != spec.parameter_count:
            raise TemplateError(
                f"template {spec.name!r}: body has {declared} placeholders but "
                f"spec.parameter_count={spec.parameter_count}"
            )
        key = (spec.name, spec.language)
        self._specs[key] = spec
        return spec

    def get(self, name: str, language: str) -> TemplateSpec:
        try:
            return self._specs[(name, language)]
        except KeyError as exc:
            raise TemplateError(
                f"no template registered for ({name!r}, {language!r})"
            ) from exc

    def list_approved(self) -> list[TemplateSpec]:
        out = [s for s in self._specs.values() if s.status is TemplateStatus.APPROVED]
        out.sort(key=lambda s: (s.name, s.language))
        return out

    def render(self, name: str, language: str, parameters: list[str]) -> str:
        spec = self.get(name, language)
        if spec.status is not TemplateStatus.APPROVED:
            raise TemplateError(
                f"template {name!r} is not approved (status={spec.status.value})"
            )
        return render_template(spec, parameters)


__all__ = [
    "TemplateCategory",
    "TemplateError",
    "TemplateRegistry",
    "TemplateSpec",
    "TemplateStatus",
    "parse_parameter_count",
    "render_template",
]
