"""Public eval registry: community-contributed eval suites.

A *suite* bundles a versioned dataset (a tuple of :class:`Sample`)
with a list of scorer ids and metadata so it can be discovered,
attributed, and compared. Registries are the lookup interface.

Why split this out from :class:`EvalRunner`? Runners execute one
agent against one dataset. A registry lets the studio / CLI
*discover* available datasets without binding to a particular
runner. This is the public API that ``loop eval list`` and the
docs site will consume.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from loop_eval.models import Sample


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EvalSuite(_StrictModel):
    """A versioned, attributable bundle of samples + scorer ids.

    ``slug`` is the URL-safe identifier (``"customer-support-v1"``).
    ``version`` follows semver; multiple versions of the same slug
    are allowed in a registry, but ``(slug, version)`` is unique.
    ``scorer_ids`` references built-in scorers by name (e.g.
    ``"exact_match"``, ``"llm_judge"``); resolution to callables is
    handled by the runner, not the registry.
    """

    slug: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    version: str = Field(min_length=1, pattern=r"^\d+\.\d+\.\d+$")
    title: str = Field(min_length=1)
    description: str = ""
    author: str = Field(min_length=1)
    license: str = "Apache-2.0"
    tags: tuple[str, ...] = ()
    scorer_ids: tuple[str, ...] = ()
    samples: tuple[Sample, ...]
    homepage: str | None = None


class DuplicateSuiteError(ValueError):
    """Raised when ``(slug, version)`` is already registered."""


class SuiteNotFoundError(LookupError):
    """Raised when a lookup misses."""


@runtime_checkable
class EvalRegistry(Protocol):
    """Lookup surface implemented by :class:`InMemoryEvalRegistry`."""

    def register(self, suite: EvalSuite) -> None: ...

    def get(self, slug: str, *, version: str | None = None) -> EvalSuite: ...

    def list(self, *, tag: str | None = None) -> tuple[EvalSuite, ...]: ...

    def slugs(self) -> tuple[str, ...]: ...


def _semver_key(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


class InMemoryEvalRegistry:
    """Process-local registry. Suitable for tests and the CLI."""

    def __init__(self, suites: Iterable[EvalSuite] | None = None) -> None:
        self._suites: dict[tuple[str, str], EvalSuite] = {}
        for suite in suites or ():
            self.register(suite)

    def register(self, suite: EvalSuite) -> None:
        key = (suite.slug, suite.version)
        if key in self._suites:
            raise DuplicateSuiteError(
                f"suite {suite.slug!r} version {suite.version!r} already registered"
            )
        self._suites[key] = suite

    def get(self, slug: str, *, version: str | None = None) -> EvalSuite:
        candidates = [s for s in self._suites.values() if s.slug == slug]
        if not candidates:
            raise SuiteNotFoundError(f"no suite with slug {slug!r}")
        if version is None:
            # Latest semver.
            return max(candidates, key=lambda s: _semver_key(s.version))
        for suite in candidates:
            if suite.version == version:
                return suite
        raise SuiteNotFoundError(
            f"suite {slug!r} has no version {version!r}; "
            f"available: {sorted(s.version for s in candidates)}"
        )

    def list(self, *, tag: str | None = None) -> tuple[EvalSuite, ...]:
        suites = sorted(
            self._suites.values(), key=lambda s: (s.slug, _semver_key(s.version))
        )
        if tag is None:
            return tuple(suites)
        return tuple(s for s in suites if tag in s.tags)

    def slugs(self) -> tuple[str, ...]:
        return tuple(sorted({s.slug for s in self._suites.values()}))


# ---------------------------------------------------------------- Built-ins


def _customer_support_v1() -> EvalSuite:
    return EvalSuite(
        slug="customer-support-v1",
        version="1.0.0",
        title="Customer Support v1",
        description=(
            "Smoke-test suite for a generic order-tracking support "
            "agent: order status, refund eligibility, and escalation "
            "fallbacks."
        ),
        author="loop",
        tags=("support", "starter"),
        scorer_ids=("exact_match", "llm_judge", "latency_scorer"),
        samples=(
            Sample(id="cs_001", input="Where's my order #1234?",
                   expected="shipped"),
            Sample(id="cs_002", input="Cancel my subscription",
                   expected="escalate"),
            Sample(id="cs_003", input="Refund for order #9999",
                   expected="not_eligible"),
        ),
    )


def _faq_routing_v1() -> EvalSuite:
    return EvalSuite(
        slug="faq-routing-v1",
        version="1.0.0",
        title="FAQ Routing v1",
        description=(
            "Tests whether the agent routes ambiguous questions to "
            "the right knowledge base shard."
        ),
        author="loop",
        tags=("routing", "starter"),
        scorer_ids=("exact_match",),
        samples=(
            Sample(id="fr_001", input="What are your hours?",
                   expected="kb:hours"),
            Sample(id="fr_002", input="How do I reset my password?",
                   expected="kb:auth"),
        ),
    )


def builtin_suites() -> tuple[EvalSuite, ...]:
    """Return the curated baseline suites shipped with the harness."""
    return (_customer_support_v1(), _faq_routing_v1())


def default_registry() -> InMemoryEvalRegistry:
    """A pre-populated registry with the built-in suites."""
    return InMemoryEvalRegistry(builtin_suites())


__all__ = [
    "DuplicateSuiteError",
    "EvalRegistry",
    "EvalSuite",
    "InMemoryEvalRegistry",
    "SuiteNotFoundError",
    "builtin_suites",
    "default_registry",
]
