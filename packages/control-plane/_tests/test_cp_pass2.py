"""Tests for S101, S260, S264, S290."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
import yaml
from loop_control_plane.alerts import (
    Alert,
    AlertRule,
    AlertRuleError,
    evaluate,
    load_rules,
)
from loop_control_plane.config import Settings
from loop_control_plane.deploy_bundler import (
    BundlerError,
    bundle,
    bundle_to_path,
)
from loop_control_plane.k8s_manifest import (
    ManifestError,
    ManifestSpec,
    render,
    render_documents,
)
from pydantic import ValidationError

# --------------------------------------------------------------------------- #
# S101 -- pydantic-settings
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("LOOP_CP_"):
            monkeypatch.delenv(key, raising=False)


def test_settings_requires_db_and_redis(tmp_path: Path) -> None:
    # Use an absolute env_file path that doesn't exist to avoid picking
    # up the workspace .env file during the test.
    with pytest.raises(ValidationError):
        Settings(_env_file=str(tmp_path / "missing.env"))  # type: ignore[call-arg]


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOP_CP_DB_URL", "postgresql://x")
    monkeypatch.setenv("LOOP_CP_REDIS_URL", "redis://r:6379")
    monkeypatch.setenv("LOOP_CP_LOG_LEVEL", "DEBUG")
    s = Settings(_env_file=str(tmp_path / "missing.env"))  # type: ignore[call-arg]
    assert s.db_url == "postgresql://x"
    assert s.redis_url == "redis://r:6379"
    assert s.log_level == "DEBUG"
    # Frozen.
    with pytest.raises(ValidationError):
        s.db_url = "other"  # type: ignore[misc]


def test_settings_rejects_unknown_extra(tmp_path: Path) -> None:
    # Unknown LOOP_CP_* env vars are simply ignored by pydantic-settings
    # (they don't map to a field). The forbid extra still kicks in for
    # explicit kwargs / dict-style construction, which is the public API.
    with pytest.raises(ValidationError):
        Settings(  # type: ignore[call-arg]
            db_url="postgresql://x",
            redis_url="redis://r",
            totally_bogus="1",
            _env_file=str(tmp_path / "missing.env"),
        )


def test_settings_loads_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "LOOP_CP_DB_URL=postgresql://from-dotenv\n"
        "LOOP_CP_REDIS_URL=redis://r\n",
        encoding="utf-8",
    )
    s = Settings(_env_file=str(env))  # type: ignore[call-arg]
    assert s.db_url == "postgresql://from-dotenv"


# --------------------------------------------------------------------------- #
# S260 -- deterministic bundler
# --------------------------------------------------------------------------- #


def _seed_tree(root: Path) -> None:
    (root / "a.txt").write_text("alpha\n", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "b.txt").write_text("beta\n", encoding="utf-8")
    (root / "sub" / "c.bin").write_bytes(b"\x00\x01\x02")


def test_bundle_is_deterministic(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _seed_tree(a)
    _seed_tree(b)
    # Touch files in different order on b to perturb mtimes.
    (b / "a.txt").touch()
    (b / "sub" / "b.txt").touch()
    res_a = bundle(a)
    res_b = bundle(b)
    assert res_a.sha256 == res_b.sha256
    assert res_a.entry_count == 3
    # Verify hash matches recomputation.
    assert hashlib.sha256(res_a.data).hexdigest() == res_a.sha256


def test_bundle_excludes_pycache(tmp_path: Path) -> None:
    root = tmp_path / "src"
    root.mkdir()
    (root / "x.py").write_text("print(1)\n", encoding="utf-8")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "x.cpython-312.pyc").write_bytes(b"junk")
    res = bundle(root)
    assert res.entry_count == 1


def test_bundle_rejects_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "src"
    root.mkdir()
    real = tmp_path / "real.txt"
    real.write_text("x", encoding="utf-8")
    (root / "link.txt").symlink_to(real)
    with pytest.raises(BundlerError):
        bundle(root)


def test_bundle_rejects_empty_tree(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(BundlerError):
        bundle(root)


def test_bundle_to_path_writes(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _seed_tree(src)
    out = tmp_path / "dist" / "bundle.zip"
    res = bundle_to_path(src, out)
    assert out.read_bytes() == res.data


# --------------------------------------------------------------------------- #
# S264 -- k8s manifest renderer
# --------------------------------------------------------------------------- #


def _spec(**overrides: object) -> ManifestSpec:
    base: dict[str, object] = {
        "name": "loop-cp-api",
        "namespace": "loop",
        "image": "ghcr.io/loop/cp-api:1.2.3",
        "env": {"LOG_LEVEL": "INFO"},
    }
    base.update(overrides)
    return ManifestSpec(**base)  # type: ignore[arg-type]


def test_render_round_trips_through_yaml() -> None:
    text = render(_spec())
    docs = list(yaml.safe_load_all(text))
    kinds = [d["kind"] for d in docs]
    assert kinds == ["Deployment", "Service", "HorizontalPodAutoscaler"]
    deploy = docs[0]
    assert deploy["spec"]["replicas"] == 1
    assert deploy["spec"]["template"]["spec"]["containers"][0]["image"].endswith(
        ":1.2.3"
    )


def test_render_documents_contains_env() -> None:
    deploy, _, _ = render_documents(_spec(env={"A": "1", "B": "2"}))
    env = deploy["spec"]["template"]["spec"]["containers"][0]["env"]  # type: ignore[index]
    assert env == [{"name": "A", "value": "1"}, {"name": "B", "value": "2"}]


def test_render_rejects_invalid_name() -> None:
    with pytest.raises(ManifestError):
        _spec(name="Loop_CP_API")


def test_render_rejects_image_without_tag() -> None:
    with pytest.raises(ManifestError):
        _spec(image="ghcr.io/loop/cp-api")


def test_render_rejects_bad_replicas() -> None:
    with pytest.raises(ManifestError):
        _spec(replicas=0)
    with pytest.raises(ManifestError):
        _spec(min_replicas=2, max_replicas=1)


# --------------------------------------------------------------------------- #
# S290 -- alert rules engine
# --------------------------------------------------------------------------- #


_RULES_YAML = """
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
"""


def test_load_rules_parses_valid_yaml(tmp_path: Path) -> None:
    p = tmp_path / "alerts.yml"
    p.write_text(_RULES_YAML, encoding="utf-8")
    rules = load_rules(p)
    assert [r.name for r in rules] == [
        "budget-breach",
        "error-spike",
        "latency-p95",
    ]
    assert rules[2].severity == "warning"  # default applied


def test_load_rules_rejects_unknown_op(tmp_path: Path) -> None:
    p = tmp_path / "alerts.yml"
    p.write_text(
        "rules:\n  - name: x\n    metric: m\n    op: '~'\n    threshold: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(AlertRuleError) as excinfo:
        load_rules(p)
    assert "rules[0].op" in str(excinfo.value)


def test_load_rules_rejects_duplicate_names(tmp_path: Path) -> None:
    p = tmp_path / "dup.yml"
    p.write_text(
        "rules:\n"
        "  - {name: x, metric: m, op: '>', threshold: 1}\n"
        "  - {name: x, metric: m2, op: '<', threshold: 0}\n",
        encoding="utf-8",
    )
    with pytest.raises(AlertRuleError) as excinfo:
        load_rules(p)
    assert "duplicate" in str(excinfo.value)


def test_load_rules_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AlertRuleError):
        load_rules(tmp_path / "nope.yml")


def test_evaluate_fires_only_when_threshold_crossed() -> None:
    rules = (
        AlertRule(
            name="budget",
            metric="cost",
            op=">=",
            threshold=100.0,
            severity="critical",
        ),
        AlertRule(
            name="errors",
            metric="err",
            op=">",
            threshold=0.05,
            severity="warning",
        ),
    )
    fired = evaluate(rules, {"cost": 150.0, "err": 0.01})
    assert [a.rule.name for a in fired] == ["budget"]
    assert isinstance(fired[0], Alert)
    assert fired[0].observed == 150.0


def test_evaluate_skips_unknown_metrics() -> None:
    rules = (
        AlertRule(
            name="x", metric="absent", op=">", threshold=0.0, severity="info"
        ),
    )
    assert evaluate(rules, {}) == ()
