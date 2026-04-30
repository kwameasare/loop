"""Alert rules engine (S290).

Loads a small YAML rules file:

```yaml
rules:
  - name: budget-breach
    metric: cost_usd_mtd
    op: ">="
    threshold: 1000
    severity: critical
  - name: error-spike
    metric: error_rate_5m
    op: ">"
    threshold: 0.05
    severity: warning
  - name: latency-p95
    metric: latency_p95_ms
    op: ">"
    threshold: 2000
    severity: warning
```

`evaluate(rules, metrics)` returns a tuple of ``Alert`` objects, one per rule
that fired. Delivery (Slack/email/PagerDuty) is intentionally out of scope
here; this module only decides *what* fired so it stays trivially testable.
"""

from __future__ import annotations

import operator as _op
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

Severity = Literal["info", "warning", "critical"]
ComparisonOp = Literal[">", ">=", "<", "<=", "==", "!="]

_OPS: Mapping[str, Callable[[float, float], bool]] = {
    ">": _op.gt,
    ">=": _op.ge,
    "<": _op.lt,
    "<=": _op.le,
    "==": _op.eq,
    "!=": _op.ne,
}

_SEVERITIES: frozenset[str] = frozenset({"info", "warning", "critical"})


class AlertRuleError(ValueError):
    """Raised when a rules file is malformed."""


@dataclass(frozen=True)
class AlertRule:
    name: str
    metric: str
    op: ComparisonOp
    threshold: float
    severity: Severity
    description: str = ""


@dataclass(frozen=True)
class Alert:
    rule: AlertRule
    observed: float
    message: str


def _coerce_rule(raw: object, *, idx: int, source: str) -> AlertRule:
    if not isinstance(raw, dict):
        raise AlertRuleError(f"{source}: rules[{idx}] must be a mapping")
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise AlertRuleError(f"{source}: rules[{idx}].name required")
    metric = raw.get("metric")
    if not isinstance(metric, str) or not metric.strip():
        raise AlertRuleError(f"{source}: rules[{idx}].metric required")
    op_raw = raw.get("op")
    if op_raw not in _OPS:
        raise AlertRuleError(
            f"{source}: rules[{idx}].op must be one of {sorted(_OPS)}"
        )
    threshold_raw = raw.get("threshold")
    if not isinstance(threshold_raw, (int, float)) or isinstance(
        threshold_raw, bool
    ):
        raise AlertRuleError(
            f"{source}: rules[{idx}].threshold must be a number"
        )
    severity_raw = raw.get("severity", "warning")
    if severity_raw not in _SEVERITIES:
        raise AlertRuleError(
            f"{source}: rules[{idx}].severity must be one of {sorted(_SEVERITIES)}"
        )
    description = raw.get("description", "")
    if not isinstance(description, str):
        raise AlertRuleError(
            f"{source}: rules[{idx}].description must be a string"
        )
    return AlertRule(
        name=name,
        metric=metric,
        op=op_raw,  # type: ignore[arg-type]
        threshold=float(threshold_raw),
        severity=severity_raw,  # type: ignore[arg-type]
        description=description,
    )


def load_rules(path: str | Path) -> tuple[AlertRule, ...]:
    p = Path(path)
    if not p.is_file():
        raise AlertRuleError(f"{p}: not a file")
    with p.open("r", encoding="utf-8") as fh:
        try:
            doc = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise AlertRuleError(f"{p}: invalid yaml: {exc}") from exc
    if not isinstance(doc, dict):
        raise AlertRuleError(f"{p}: top-level must be a mapping")
    raw_rules = doc.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise AlertRuleError(f"{p}: 'rules' must be a non-empty list")
    out = tuple(
        _coerce_rule(item, idx=i, source=str(p))
        for i, item in enumerate(raw_rules)
    )
    seen: set[str] = set()
    for r in out:
        if r.name in seen:
            raise AlertRuleError(f"{p}: duplicate rule name {r.name!r}")
        seen.add(r.name)
    return out


def evaluate(
    rules: Iterable[AlertRule],
    metrics: Mapping[str, float],
) -> tuple[Alert, ...]:
    """Return the rules that fire against ``metrics``.

    A rule whose ``metric`` key is absent from ``metrics`` is silently
    skipped: missing telemetry is not the alerting layer's call to make.
    """

    fired: list[Alert] = []
    for rule in rules:
        if rule.metric not in metrics:
            continue
        observed = float(metrics[rule.metric])
        if _OPS[rule.op](observed, rule.threshold):
            fired.append(
                Alert(
                    rule=rule,
                    observed=observed,
                    message=(
                        f"{rule.name}: {rule.metric}={observed} "
                        f"{rule.op} {rule.threshold} ({rule.severity})"
                    ),
                )
            )
    return tuple(fired)


__all__ = [
    "Alert",
    "AlertRule",
    "AlertRuleError",
    "ComparisonOp",
    "Severity",
    "evaluate",
    "load_rules",
]
