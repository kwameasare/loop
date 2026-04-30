"""Pass9 tests for whatsapp template registry."""

from __future__ import annotations

import pytest
from loop_channels_whatsapp.templates import (
    TemplateCategory,
    TemplateError,
    TemplateRegistry,
    TemplateSpec,
    TemplateStatus,
    parse_parameter_count,
    render_template,
)


def _spec(**overrides) -> TemplateSpec:
    base = dict(
        name="order_update",
        language="en_US",
        category=TemplateCategory.UTILITY,
        status=TemplateStatus.APPROVED,
        body="Hi {{1}}, your order {{2}} is on the way.",
        parameter_count=2,
    )
    base.update(overrides)
    return TemplateSpec(**base)


def test_parse_parameter_count_counts_distinct():
    assert parse_parameter_count("hi {{1}} {{2}} {{1}}") == 2
    assert parse_parameter_count("plain text") == 0


def test_parse_parameter_count_rejects_gap():
    with pytest.raises(TemplateError):
        parse_parameter_count("hi {{1}} {{3}}")


def test_render_substitutes_parameters():
    spec = _spec()
    out = render_template(spec, ["Alex", "#42"])
    assert out == "Hi Alex, your order #42 is on the way."


def test_render_rejects_wrong_count():
    spec = _spec()
    with pytest.raises(TemplateError):
        render_template(spec, ["only-one"])


def test_render_rejects_empty_param():
    spec = _spec()
    with pytest.raises(TemplateError):
        render_template(spec, ["Alex", "  "])


def test_registry_register_validates_body_against_count():
    reg = TemplateRegistry()
    bad = _spec(parameter_count=5)
    with pytest.raises(TemplateError):
        reg.register(bad)


def test_registry_render_blocks_pending():
    reg = TemplateRegistry()
    reg.register(_spec(status=TemplateStatus.PENDING))
    with pytest.raises(TemplateError):
        reg.render("order_update", "en_US", ["Alex", "#1"])


def test_registry_list_approved_filters_and_sorts():
    reg = TemplateRegistry()
    reg.register(_spec())
    reg.register(_spec(name="alpha", body="x", parameter_count=0))
    reg.register(_spec(name="rejected", status=TemplateStatus.REJECTED, body="x", parameter_count=0))
    out = reg.list_approved()
    names = [s.name for s in out]
    assert names == ["alpha", "order_update"]


def test_registry_get_unknown_raises():
    reg = TemplateRegistry()
    with pytest.raises(TemplateError):
        reg.get("missing", "en_US")


def test_template_spec_extra_forbid():
    with pytest.raises(Exception):  # noqa: B017
        TemplateSpec(
            name="x",
            language="en_US",
            category=TemplateCategory.UTILITY,
            status=TemplateStatus.APPROVED,
            body="x",
            parameter_count=0,
            extra_field=1,  # type: ignore[call-arg]
        )
