"""Drift guard for OpenAPI-derived TypeScript declarations."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GEN_PATH = REPO_ROOT / "tools" / "gen_openapi_ts.py"
TS_OUT_PATH = REPO_ROOT / "apps" / "studio" / "src" / "lib" / "openapi-types.ts"


def _load_gen():
    spec = importlib.util.spec_from_file_location("gen_openapi_ts", GEN_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["gen_openapi_ts"] = module
    spec.loader.exec_module(module)
    return module


def test_committed_openapi_ts_matches_generator() -> None:
    gen = _load_gen()
    assert TS_OUT_PATH.read_text(encoding="utf-8") == gen.render_ts()


def test_openapi_ts_contains_core_operations() -> None:
    gen = _load_gen()
    rendered = gen.render_ts()
    assert "export interface Operations" in rendered
    assert "PostAgentsByAgentIdInvoke" in rendered
    assert "GetEvalRunsByRunId" in rendered
    assert "AgentResponse" in rendered


def test_check_mode_detects_drift(tmp_path: Path, monkeypatch) -> None:
    gen = _load_gen()
    fake = tmp_path / "openapi-types.ts"
    fake.write_text("// stale\n", encoding="utf-8")
    monkeypatch.setattr(gen, "TS_OUT_PATH", fake)
    assert gen.main(["--check"]) == 1
