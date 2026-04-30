"""Eval suite YAML loader (S248).

Loads ``tests/evals/*.yml`` files into ``loop_eval.Sample`` rows. Schema:

```yaml
suite: smoke           # optional; default = file stem
samples:
  - id: greet-1
    input: "hi"
    expected: "hello"
    expected_tool_calls:
      - name: search
        args: {q: "hello"}
    metadata:
      lang: en
```

We do not import ``yaml`` at module import time -- the dependency is added
to ``packaging/eval-harness/pyproject.toml``; using ``PyYAML`` keeps us in
the same ballpark of deps already pulled by the rest of the workspace.

Validation errors include the file path and (where derivable from PyYAML)
the line number so editors can jump straight to the offending field.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from loop_eval.models import Sample, ToolInvocation


@dataclass(frozen=True)
class LoadedSuite:
    """One YAML suite and its parsed samples."""

    name: str
    path: Path
    samples: tuple[Sample, ...]


class SuiteLoadError(ValueError):
    """Raised when a YAML suite cannot be parsed or validated."""


def _load_yaml(path: Path) -> object:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - exercised by CI install
        raise SuiteLoadError(
            "PyYAML is required to load eval suites; install it via "
            "`uv add pyyaml` or equivalent"
        ) from exc
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise SuiteLoadError(f"{path}: invalid yaml: {exc}") from exc


def _parse_tool_calls(
    raw: object, *, path: Path, sample_idx: int
) -> tuple[ToolInvocation, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise SuiteLoadError(
            f"{path}: sample[{sample_idx}].expected_tool_calls must be a list"
        )
    out: list[ToolInvocation] = []
    for j, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SuiteLoadError(
                f"{path}: sample[{sample_idx}].expected_tool_calls[{j}] "
                "must be a mapping"
            )
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise SuiteLoadError(
                f"{path}: sample[{sample_idx}].expected_tool_calls[{j}].name "
                "must be a non-empty string"
            )
        args = item.get("args", {})
        if args is None:
            args = {}
        if not isinstance(args, dict):
            raise SuiteLoadError(
                f"{path}: sample[{sample_idx}].expected_tool_calls[{j}].args "
                "must be a mapping"
            )
        out.append(
            ToolInvocation(
                name=name,
                args_json=json.dumps(args, sort_keys=True),
            )
        )
    return tuple(out)


def _parse_metadata(
    raw: object, *, path: Path, sample_idx: int
) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise SuiteLoadError(
            f"{path}: sample[{sample_idx}].metadata must be a mapping"
        )
    out: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            raise SuiteLoadError(
                f"{path}: sample[{sample_idx}].metadata keys must be strings"
            )
        out[k] = str(v)
    return out


def load_suite(path: str | Path) -> LoadedSuite:
    p = Path(path)
    if not p.is_file():
        raise SuiteLoadError(f"{p}: not a file")
    data = _load_yaml(p)
    if not isinstance(data, dict):
        raise SuiteLoadError(f"{p}: top-level must be a mapping")
    name_raw = data.get("suite", p.stem)
    if not isinstance(name_raw, str) or not name_raw.strip():
        raise SuiteLoadError(f"{p}: 'suite' must be a non-empty string")
    samples_raw = data.get("samples")
    if not isinstance(samples_raw, list) or not samples_raw:
        raise SuiteLoadError(f"{p}: 'samples' must be a non-empty list")
    samples: list[Sample] = []
    for i, item in enumerate(samples_raw):
        if not isinstance(item, dict):
            raise SuiteLoadError(f"{p}: sample[{i}] must be a mapping")
        sid = item.get("id")
        if not isinstance(sid, str) or not sid:
            raise SuiteLoadError(
                f"{p}: sample[{i}].id must be a non-empty string"
            )
        inp = item.get("input")
        if not isinstance(inp, str):
            raise SuiteLoadError(
                f"{p}: sample[{i}].input must be a string"
            )
        expected = item.get("expected")
        if expected is not None and not isinstance(expected, str):
            raise SuiteLoadError(
                f"{p}: sample[{i}].expected must be a string or null"
            )
        try:
            samples.append(
                Sample(
                    id=sid,
                    input=inp,
                    expected=expected,
                    expected_tool_calls=_parse_tool_calls(
                        item.get("expected_tool_calls"), path=p, sample_idx=i
                    ),
                    metadata=_parse_metadata(
                        item.get("metadata"), path=p, sample_idx=i
                    ),
                )
            )
        except Exception as exc:  # pydantic ValidationError + extras
            raise SuiteLoadError(
                f"{p}: sample[{i}] failed validation: {exc}"
            ) from exc
    return LoadedSuite(name=name_raw, path=p, samples=tuple(samples))


def load_suites(directory: str | Path) -> list[LoadedSuite]:
    """Load every ``*.yml`` / ``*.yaml`` file under ``directory`` (sorted)."""

    root = Path(directory)
    if not root.is_dir():
        raise SuiteLoadError(f"{root}: not a directory")
    paths: Iterable[Path] = sorted(
        list(root.glob("*.yml")) + list(root.glob("*.yaml"))
    )
    return [load_suite(p) for p in paths]


__all__ = [
    "LoadedSuite",
    "SuiteLoadError",
    "load_suite",
    "load_suites",
]
