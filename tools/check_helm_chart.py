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
from typing import cast

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = REPO_ROOT / "infra" / "helm" / "loop"

REQUIRED_TEMPLATES = {
    "_helpers.tpl",
    "configmap.yaml",
    "secret.yaml",
    "serviceaccount.yaml",
    "control-plane.yaml",
    "control-plane-hpa.yaml",
    "control-plane-pdb.yaml",
    "runtime.yaml",
    "runtime-hpa.yaml",
    "runtime-pdb.yaml",
    "gateway.yaml",
    "gateway-hpa.yaml",
    "gateway-pdb.yaml",
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
    ("controlPlane", "autoscaling", "enabled"),
    ("controlPlane", "autoscaling", "minReplicas"),
    ("controlPlane", "autoscaling", "maxReplicas"),
    ("controlPlane", "autoscaling", "targetCPUUtilizationPercentage"),
    ("controlPlane", "pdb", "enabled"),
    ("runtime", "enabled"),
    ("runtime", "image", "repository"),
    ("runtime", "service", "port"),
    ("runtime", "autoscaling", "enabled"),
    ("runtime", "autoscaling", "minReplicas"),
    ("runtime", "autoscaling", "maxReplicas"),
    ("runtime", "autoscaling", "targetCPUUtilizationPercentage"),
    ("runtime", "pdb", "enabled"),
    ("gateway", "enabled"),
    ("gateway", "image", "repository"),
    ("gateway", "service", "port"),
    ("gateway", "autoscaling", "enabled"),
    ("gateway", "autoscaling", "minReplicas"),
    ("gateway", "autoscaling", "maxReplicas"),
    ("gateway", "autoscaling", "targetCPUUtilizationPercentage"),
    ("gateway", "pdb", "enabled"),
    ("toolHost", "enabled"),
    ("toolHost", "image", "repository"),
    ("toolHost", "image", "tag"),
    ("toolHost", "replicaCount"),
    ("toolHost", "service", "port"),
    ("toolHost", "sandboxRuntimeClassName"),
    ("toolHost", "kata", "required"),
    ("toolHost", "kata", "runtimeClassHandler"),
    ("toolHost", "preInstallCheck", "enabled"),
    ("toolHost", "preInstallCheck", "image"),
    ("toolHost", "preInstallCheck", "pullPolicy"),
    ("toolHost", "serviceAccount", "create"),
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


def _resolve(d: object, path: tuple[str, ...]) -> object:
    cur: object = d
    for key in path:
        if not isinstance(cur, dict):
            raise HelmChartError(f"missing values key: {'.'.join(path)}")
        cur_map = cast(dict[str, object], cur)
        if key not in cur_map:
            raise HelmChartError(f"missing values key: {'.'.join(path)}")
        cur = cur_map[key]
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
        chart_obj: object = yaml.safe_load(chart_yaml.read_text())
    except yaml.YAMLError as exc:
        errors.append(f"Chart.yaml not valid yaml: {exc}")
        return errors
    if not isinstance(chart_obj, dict):
        errors.append("Chart.yaml must be a mapping")
        return errors
    chart = cast(dict[str, object], chart_obj)
    for key in REQUIRED_CHART_KEYS:
        if key not in chart:
            errors.append(f"Chart.yaml missing key: {key}")

    # Bundled dependencies must be pinned to exact semver and have a
    # condition flag so operators can swap in managed services.
    raw_deps_obj = chart.get("dependencies", [])
    if not isinstance(raw_deps_obj, list):
        errors.append("Chart.yaml dependencies must be a list")
        raw_deps_obj = []
    raw_deps = cast(list[object], raw_deps_obj)
    for entry in raw_deps:
        if not isinstance(entry, dict):
            errors.append("Chart.yaml dependency entries must be mappings")
            continue
        dep = cast(dict[str, object], entry)
        name_any = dep.get("name", "<unnamed>")
        version_any = dep.get("version")
        name = str(name_any) if not isinstance(name_any, str) else name_any
        if not isinstance(version_any, str) or not re.match(r"^\d+\.\d+\.\d+$", version_any):
            errors.append(f"dependency {name}: version must be exact semver (got {version_any!r})")
        if "condition" not in dep:
            errors.append(f"dependency {name}: must declare a condition flag")
        if "repository" not in dep:
            errors.append(f"dependency {name}: must declare a repository URL")
        repo_any = dep.get("repository")
        if isinstance(repo_any, str) and repo_any.startswith("file://"):
            local_chart = chart_dir / repo_any.removeprefix("file://")
            if not (local_chart / "Chart.yaml").is_file():
                errors.append(f"dependency {name}: missing local chart at {repo_any}")

    try:
        values_obj: object = yaml.safe_load(values_yaml.read_text())
    except yaml.YAMLError as exc:
        errors.append(f"values.yaml not valid yaml: {exc}")
        return errors
    if not isinstance(values_obj, dict):
        errors.append("values.yaml must be a mapping")
        return errors
    values = cast(dict[str, object], values_obj)
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
