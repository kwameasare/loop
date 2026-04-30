"""docs-with-code CI gate.

Fails if a PR touches code that requires a paired doc edit and the doc edit is
missing. The rules are intentionally narrow: only paths that produce schema /
public-type / error-code / env-var / endpoint drift are checked. See
`loop_implementation/skills/meta/docs-with-code-check.md` for the policy.

Usage:
    python tools/check_docs_with_code.py [--base BASE] [--head HEAD]

Defaults: base = origin/main, head = HEAD.

Exit code 0 if all pairings are satisfied or no rule-relevant files changed.
Exit code 1 with a human-readable diagnostic otherwise.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    """A code-path → required-doc rule."""

    name: str
    code_pattern: re.Pattern[str]
    required_doc: str
    extra_check: str = ""  # human-readable hint shown on failure


RULES: tuple[Rule, ...] = (
    Rule(
        name="postgres-migration → SCHEMA.md",
        code_pattern=re.compile(r"^packages/[^/]+/migrations/versions/.*\.py$"),
        required_doc="loop_implementation/data/SCHEMA.md",
        extra_check="Apply skills/data/update-schema.md.",
    ),
    Rule(
        name="public Pydantic type → SCHEMA.md §9 + openapi.yaml",
        code_pattern=re.compile(r"^packages/sdk-py/loop/(types\.py|_types\.py)$"),
        required_doc="loop_implementation/data/SCHEMA.md",
        extra_check="Also touch api/openapi.yaml. Apply skills/data/add-pydantic-type.md.",
    ),
    Rule(
        name="error class → ERROR_CODES.md",
        code_pattern=re.compile(r"^packages/[^/]+/.*errors\.py$"),
        required_doc="loop_implementation/engineering/ERROR_CODES.md",
        extra_check="Apply skills/security/add-error-code.md.",
    ),
    Rule(
        name="REST route → openapi.yaml",
        code_pattern=re.compile(r"^apps/control-plane/.*/routes/.*\.py$"),
        required_doc="loop_implementation/api/openapi.yaml",
        extra_check="Apply skills/api/update-openapi.md.",
    ),
    Rule(
        name="new package or top-level service → ARCHITECTURE.md",
        code_pattern=re.compile(r"^(packages|apps)/[^/]+/pyproject\.toml$"),
        required_doc="loop_implementation/architecture/ARCHITECTURE.md",
        extra_check="Apply skills/architecture/update-architecture.md (only on first add).",
    ),
)

# Env var rule is content-based, not path-based; checked separately.
ENV_VAR_DECL_RE = re.compile(r"\bLOOP_[A-Z][A-Z0-9_]+\b")
ENV_DOC = "loop_implementation/engineering/ENV_REFERENCE.md"

# Files that should never block this gate even if they match a rule pattern
# (test fixtures, migration helpers that touch but don't define new schema, etc.).
EXEMPT_PATHS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^.*/_tests/"),
    re.compile(r"^tests/"),
    re.compile(r".*/_runner\.py$"),
    re.compile(r".*/env\.py$"),
)


def run(cmd: list[str]) -> str:
    """Run a command, return stdout. Empty string on error."""
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return out
    except subprocess.CalledProcessError as exc:
        print(f"warning: `{' '.join(cmd)}` failed: {exc.output}", file=sys.stderr)
        return ""


def changed_files(base: str, head: str) -> list[str]:
    raw = run(["git", "diff", "--name-only", f"{base}...{head}"])
    return [f.strip() for f in raw.splitlines() if f.strip()]


def changed_diff_for(path: str, base: str, head: str) -> str:
    return run(["git", "diff", f"{base}...{head}", "--", path])


def is_exempt(path: str) -> bool:
    return any(p.search(path) for p in EXEMPT_PATHS)


def diff_introduces_new_env_var(diff_text: str, already_documented: set[str]) -> set[str]:
    """Return env vars added in `diff_text` that aren't yet in ENV_REFERENCE.md."""
    introduced: set[str] = set()
    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for match in ENV_VAR_DECL_RE.finditer(line):
            introduced.add(match.group(0))
    return introduced - already_documented


def documented_env_vars() -> set[str]:
    try:
        with open(ENV_DOC, encoding="utf-8") as f:
            return set(ENV_VAR_DECL_RE.findall(f.read()))
    except FileNotFoundError:
        return set()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args(argv)

    files = changed_files(args.base, args.head)
    if not files:
        print("docs-with-code: no changes between base and head — pass.")
        return 0

    failures: list[str] = []

    # Path-based rules.
    for rule in RULES:
        offending = [
            f for f in files
            if rule.code_pattern.match(f) and not is_exempt(f)
        ]
        if not offending:
            continue
        if rule.required_doc in files:
            continue
        failures.append(
            f"\n  ✗ {rule.name}\n"
            f"      Code touched (sample):\n"
            f"        - {offending[0]}\n"
            f"      Required doc edit (missing):\n"
            f"        - {rule.required_doc}\n"
            f"      Hint: {rule.extra_check}"
        )

    # Content-based env-var rule.
    documented = documented_env_vars()
    new_envs: set[str] = set()
    for f in files:
        if not f.endswith(".py") or is_exempt(f):
            continue
        if f.startswith("loop_implementation/") or f.startswith("tools/"):
            continue
        diff = changed_diff_for(f, args.base, args.head)
        new_envs |= diff_introduces_new_env_var(diff, documented)
    if new_envs and ENV_DOC not in files:
        failures.append(
            f"\n  ✗ env vars added but ENV_REFERENCE.md not updated\n"
            f"      Vars: {sorted(new_envs)}\n"
            f"      Required doc edit (missing):\n"
            f"        - {ENV_DOC}"
        )

    if not failures:
        print("docs-with-code: all rules satisfied — pass.")
        return 0

    print("docs-with-code: PR is missing required doc edit(s).\n", file=sys.stderr)
    for failure in failures:
        print(failure, file=sys.stderr)
    print(
        "\nFix: add the doc edits to this PR. "
        "See skills/meta/docs-with-code-check.md for the policy and the "
        "matching skill for each rule.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
