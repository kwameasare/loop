"""S639 on-prem parity matrix evidence checks."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "loop_implementation" / "engineering" / "PARITY.md"
EVIDENCE = ROOT / "loop_implementation" / "engineering" / "parity_evidence.tsv"
VALUES = ROOT / "infra" / "helm" / "loop" / "values.yaml"


def _rows() -> list[dict[str, str]]:
    with EVIDENCE.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="|"))


def _parts(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def _values() -> dict[str, object]:
    return cast(dict[str, object], yaml.safe_load(VALUES.read_text()))


def _value_at(data: object, dotted: str) -> object | None:
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = cast(dict[str, object], node)[part]
    return node


def test_parity_matrix_covers_every_checked_evidence_row() -> None:
    rows = _rows()
    text = PARITY.read_text()
    seen: set[str] = set()
    assert rows
    assert "No silent gaps" in text
    for row in rows:
        seen.add(row["id"])
        assert f"| `{row['id']}` |" in text
        assert row["status"] in {"parity", "accepted_gap"}
        if row["status"] == "accepted_gap":
            assert row["accepted_gap"].startswith("Accepted:")
        else:
            assert row["accepted_gap"] == ""
    assert len(seen) == len(rows)


def test_parity_evidence_paths_and_feature_gates_are_real() -> None:
    values = _values()
    for row in _rows():
        for path in _parts(row["evidence_paths"]):
            assert (ROOT / path).exists(), path
        gates = _parts(row["feature_gates"])
        assert gates, row["id"]
        if row["status"] == "parity":
            for gate in gates:
                assert _value_at(values, gate) is not None, gate
        else:
            assert all(gate.startswith("accepted:") for gate in gates)


def test_enterprise_ga_points_at_authoritative_parity_matrix() -> None:
    enterprise_ga = ROOT / "loop_implementation" / "engineering" / "ENTERPRISE_GA.md"
    text = enterprise_ga.read_text()
    assert "[PARITY.md](PARITY.md)" in text
    assert "evidence committed beside it" in text
