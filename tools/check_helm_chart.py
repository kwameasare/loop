"""Structural validator for the Loop self-host Helm chart.

CI runs this in lieu of `helm lint` so we don't depend on the helm
binary in the build image. It parses Chart.yaml + values.yaml as YAML
and confirms the templates directory has every file the README claims.
Helm template directives ({{ ... }}) are stripped before YAML parsing
so each template can be syntax-checked in isolation.

Exit code 0 if the chart is structurally sound, 1 otherwise. Run:

    uv run python tools/check_helm_chart.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = REPO_ROOT / "infra" / "helm" / "loop"

REQUIRED_TEMPLATES = {
    "_helpers.tpl",
    "configmap.yaml",
    "secret.yaml",
    "serviceaccount.yaml",
    "control-plane.yaml",
    "runtime.yaml",
    "gateway.yaml",
    "ingress.yaml",
    "NOTES.txt",
}

REQUIRED_VALUE_PATHS: tuple[tuple[str, ...], ...] = (
    ("global", "imageRegistry"),
    ("global", "imagePullPolicy"),
    ("controlPlane", "enabled"),
    ("controlPlane", "image", "repository"),
    ("controlPlane", "image", "tag"),
    ("controlPlane", "replicaCount"),
    ("controlPlane", "service", "port"),
    ("controlPlane", "resources"),
    ("runtime", "enabled"),
    ("runtime", "image", "repository"),
    ("runtime", "service", "port"),
    ("gateway", "enabled"),
    ("gateway", "image", "repository"),
    ("gateway", "service", "port"),
    ("externals", "postgresUrl"),
    ("externals", "redisUrl"),
    ("externals", "qdrantUrl"),
    ("externals", "natsUrl"),
    ("externals", "s3Endpoint"),
    ("externals", "otelEndpoint"),
    ("secrets", "llmApiKey"),
    ("secrets", "jwtSigningKey"),
    ("ingress", "enabled"),
    ("serviceAccount", "create"),
)

REQUIRED_CHART_KEYS = ("apiVersion", "name", "version", "appVersion", "type")

# Strip {{ ... }} blocks (single-line) and full-line {{- if/end -}} so PyYAML
# can parse what's left. We cannot evaluate the template; structural
# parseability after stripping is a useful proxy.
_DIRECTIVE_RE = re.compile(r"\{\{[\s\S]*?\}\}")
_BLANK_LINE_RE = re.compile(r"^\s*$\n", re.MULTILINE)


class HelmChartError(RuntimeError):
    """Raised on structural problems."""


def _resolve(d: Any, path: tuple[str, ...]) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            raise HelmChartError(f"missing values key: {'.'.join(path)}")
        cur = cur[key]
    return cur


def _strip_directives(text: str) -> str:
    return _DIRECTIVE_RE.sub("", text)


def check_chart(chart_dir: Path = CHART_DIR) -> list[str]:
    """Run all structural checks. Returns a list of error strings."""

    errors: list[str] = []

    chart_yaml = chart_dir / "Chart.yaml"
    values_yaml = chart_dir / "values.yaml"
    templates_dir = chart_dir / "templates"

    if not chart_yaml.is_file():
        errors.append(f"missing {chart_yaml}")
        return errors
    if not values_yaml.is_file():
        errors.append(f"missing {values_yaml}")
        return errors
    if not templates_dir.is_dir():
        errors.append(f"missing {templates_dir}")
        return errors

    try:
        chart = yaml.safe_load(chart_yaml.read_text())
    except yaml.YAMLError as exc:
        errors.append(f"Chart.yaml not valid yaml: {exc}")
        return errors
    if not isinstance(chart, dict):
        errors.append("Chart.yaml must be a mapping")
        return errors
    for key in REQUIRED_CHART_KEYS:
        if key not in chart:
            errors.append(f"Chart.yaml missing key: {key}")

    try:
        values = yaml.safe_load(values_yaml.read_text())
    except yaml.YAMLError as exc:
        errors.append(f"values.yaml not valid yaml: {exc}")
        return errors
    if not isinstance(values, dict):
        errors.append("values.yaml must be a mapping")
        return errors
    for path in REQUIRED_VALUE_PATHS:
        try:
            _resolve(values, path)
        except HelmChartError as exc:
            errors.append(str(exc))

    present = {p.name for p in templates_dir.iterdir() if p.is_file()}
    missing = REQUIRED_TEMPLATES - present
    for m in sorted(missing):
        errors.append(f"missing template: templates/{m}")

    for tpl in sorted(present):
        path = templates_dir / tpl
        if not tpl.endswith((".yaml", ".yml")):
            continue
        stripped = _strip_directives(path.read_text())
        stripped = _BLANK_LINE_RE.sub("", stripped)
        if not stripped.strip():
            continue
        try:
            list(yaml.safe_load_all(stripped))
        except yaml.YAMLError as exc:
            errors.append(f"{tpl}: yaml parse failed after stripping directives: {exc}")

    return errors


def main() -> int:
    errors = check_chart()
    if errors:
        for e in errors:
            print(f"helm-chart: {e}")
        print("helm-chart: FAILED")
        return 1
    print("helm-chart: chart at infra/helm/loop is structurally sound.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
