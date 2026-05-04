"""Checks for env-driven Uvicorn worker configuration in cp-api and dp-runtime."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CP_DOCKERFILE = ROOT / "packages" / "control-plane" / "Dockerfile"
DP_DOCKERFILE = ROOT / "packages" / "data-plane" / "Dockerfile"
CP_RUNNER = ROOT / "packages" / "control-plane" / "loop_control_plane" / "run_uvicorn.py"
DP_RUNNER = ROOT / "packages" / "data-plane" / "loop_data_plane" / "run_uvicorn.py"
HELPERS = ROOT / "infra" / "helm" / "loop" / "templates" / "_helpers.tpl"
CP_TEMPLATE = ROOT / "infra" / "helm" / "loop" / "templates" / "control-plane.yaml"
DP_TEMPLATE = ROOT / "infra" / "helm" / "loop" / "templates" / "runtime.yaml"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dockerfiles_use_env_driven_runner_modules() -> None:
    assert "loop_control_plane.run_uvicorn" in CP_DOCKERFILE.read_text()
    assert "loop_data_plane.run_uvicorn" in DP_DOCKERFILE.read_text()


def test_control_plane_runner_worker_count_parsing(monkeypatch) -> None:
    module = _load_module(CP_RUNNER, "cp_runner")

    monkeypatch.delenv("UVICORN_WORKERS", raising=False)
    assert module._worker_count() == 4

    monkeypatch.setenv("UVICORN_WORKERS", "7")
    assert module._worker_count() == 7

    monkeypatch.setenv("UVICORN_WORKERS", "0")
    assert module._worker_count() == 1

    monkeypatch.setenv("UVICORN_WORKERS", "bad")
    assert module._worker_count() == 4


def test_runtime_runner_worker_count_parsing(monkeypatch) -> None:
    module = _load_module(DP_RUNNER, "dp_runner")

    monkeypatch.delenv("UVICORN_WORKERS", raising=False)
    assert module._worker_count() == 4

    monkeypatch.setenv("UVICORN_WORKERS", "6")
    assert module._worker_count() == 6


def test_helm_templates_set_uvicorn_workers_from_helper() -> None:
    helpers = HELPERS.read_text()
    cp_template = CP_TEMPLATE.read_text()
    dp_template = DP_TEMPLATE.read_text()

    assert "define \"loop.recommendedWorkers\"" in helpers
    assert "define \"loop.cpuMillicores\"" in helpers
    assert "UVICORN_WORKERS" in cp_template
    assert "loop.recommendedWorkers" in cp_template
    assert "UVICORN_WORKERS" in dp_template
    assert "loop.recommendedWorkers" in dp_template
