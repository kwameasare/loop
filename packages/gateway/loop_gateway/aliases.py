"""Model-alias resolution: ``fast`` / ``cheap`` / ``best`` -> concrete model.

Default mapping lives in ``aliases.yaml`` next to this file; workspace-level
overrides (BYOK customers) layer on top -- here we accept them as a dict
parameter so the resolver stays pure for tests.
"""

from __future__ import annotations

from importlib.resources import files

import yaml

_DEFAULTS: dict[str, str] | None = None


def _load_defaults() -> dict[str, str]:
    global _DEFAULTS
    if _DEFAULTS is None:
        raw = files("loop_gateway").joinpath("aliases.yaml").read_text()
        loaded = yaml.safe_load(raw) or {}
        if not isinstance(loaded, dict):
            raise RuntimeError("aliases.yaml must be a mapping")
        _DEFAULTS = {str(k): str(v) for k, v in loaded.items()}
    return _DEFAULTS


def resolve(
    model_or_alias: str,
    workspace_overrides: dict[str, str] | None = None,
) -> str:
    """Return a concrete provider model id.

    Accepts either an alias (``fast``/``cheap``/``best``) or a concrete model
    id; concrete ids round-trip unchanged so callers don't need to know
    whether what they got was already resolved.
    """
    overrides = workspace_overrides or {}
    if model_or_alias in overrides:
        return overrides[model_or_alias]
    defaults = _load_defaults()
    return defaults.get(model_or_alias, model_or_alias)
