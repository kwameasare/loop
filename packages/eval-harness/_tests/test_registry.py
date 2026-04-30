"""Tests for the public eval registry (S043)."""

from __future__ import annotations

import pytest
from loop_eval import (
    DuplicateSuiteError,
    EvalRegistry,
    EvalSuite,
    InMemoryEvalRegistry,
    Sample,
    SuiteNotFoundError,
    builtin_suites,
    default_registry,
)
from pydantic import ValidationError


def _suite(slug: str = "demo", version: str = "1.0.0", **kw) -> EvalSuite:
    return EvalSuite(
        slug=slug,
        version=version,
        title=kw.get("title", "Demo"),
        description=kw.get("description", ""),
        author=kw.get("author", "loop"),
        tags=kw.get("tags", ("starter",)),
        scorer_ids=kw.get("scorer_ids", ("exact_match",)),
        samples=kw.get(
            "samples",
            (Sample(id="d1", input="hi", expected="hi"),),
        ),
    )


def test_in_memory_registry_implements_protocol() -> None:
    reg = InMemoryEvalRegistry()
    assert isinstance(reg, EvalRegistry)


def test_register_and_get_latest_by_slug() -> None:
    reg = InMemoryEvalRegistry()
    reg.register(_suite(version="1.0.0"))
    reg.register(_suite(version="1.2.0"))
    reg.register(_suite(version="1.1.5"))
    latest = reg.get("demo")
    assert latest.version == "1.2.0"


def test_get_specific_version() -> None:
    reg = InMemoryEvalRegistry([_suite(version="1.0.0"), _suite(version="2.0.0")])
    assert reg.get("demo", version="1.0.0").version == "1.0.0"


def test_register_duplicate_raises() -> None:
    reg = InMemoryEvalRegistry([_suite()])
    with pytest.raises(DuplicateSuiteError):
        reg.register(_suite())


def test_get_unknown_slug_raises() -> None:
    reg = InMemoryEvalRegistry()
    with pytest.raises(SuiteNotFoundError):
        reg.get("ghost")


def test_get_unknown_version_raises() -> None:
    reg = InMemoryEvalRegistry([_suite(version="1.0.0")])
    with pytest.raises(SuiteNotFoundError):
        reg.get("demo", version="9.9.9")


def test_list_filters_by_tag() -> None:
    reg = InMemoryEvalRegistry(
        [
            _suite(slug="a", tags=("starter",)),
            _suite(slug="b", tags=("advanced",)),
            _suite(slug="c", tags=("starter", "advanced")),
        ]
    )
    starters = {s.slug for s in reg.list(tag="starter")}
    assert starters == {"a", "c"}


def test_list_is_sorted_deterministically() -> None:
    reg = InMemoryEvalRegistry()
    reg.register(_suite(slug="b", version="1.0.0"))
    reg.register(_suite(slug="a", version="2.0.0"))
    reg.register(_suite(slug="a", version="1.0.0"))
    listed = [(s.slug, s.version) for s in reg.list()]
    assert listed == [("a", "1.0.0"), ("a", "2.0.0"), ("b", "1.0.0")]


def test_slug_validation_rejects_uppercase() -> None:
    with pytest.raises(ValidationError):
        EvalSuite(
            slug="BadSlug",
            version="1.0.0",
            title="t",
            author="loop",
            samples=(Sample(id="x", input="y"),),
        )


def test_version_must_be_semver_three_part() -> None:
    with pytest.raises(ValidationError):
        EvalSuite(
            slug="ok",
            version="1.0",
            title="t",
            author="loop",
            samples=(Sample(id="x", input="y"),),
        )


def test_default_registry_includes_builtins() -> None:
    reg = default_registry()
    slugs = set(reg.slugs())
    assert "customer-support-v1" in slugs
    assert "faq-routing-v1" in slugs
    # builtin_suites() and default_registry() are consistent.
    assert {s.slug for s in builtin_suites()} == slugs


def test_evalsuite_is_frozen() -> None:
    suite = _suite()
    with pytest.raises(ValidationError):
        suite.title = "mutated"
