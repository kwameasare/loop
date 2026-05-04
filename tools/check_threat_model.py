"""STRIDE threat-model gate (S801).

Fails when a PR touches a security-protected code path without also
updating ``docs/THREAT_MODEL.md`` (or providing an explicit
``threat-model: skip`` opt-out token in the PR body, which is logged in
the gate output for auditors).

Inputs (any of, checked in order):

1. ``--changed-files`` flag with a path to a newline-delimited file of
   changed paths (used by GitHub Actions where the workflow gathers the
   diff via ``gh pr diff --name-only``).
2. ``LOOP_GATE_CHANGED_FILES`` env var with the same shape.
3. ``LOOP_GATE_CHANGED_FILES_INLINE`` env var with newline-separated
   paths (handy for tests).
4. Stdin (one path per line).

The PR body (when given via ``--pr-body`` / ``LOOP_GATE_PR_BODY``) is
scanned for the literal token ``threat-model: skip`` to permit a
documented bypass for changes that genuinely don't affect the threat
model (e.g. a test-only edit on an auth file).

Exit codes:

* ``0`` — no protected paths touched, or all required updates present.
* ``2`` — protected paths touched but ``docs/THREAT_MODEL.md`` not
  updated and no skip token present.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

# Globs MUST mirror the table in docs/THREAT_MODEL.md §STRIDE-protected paths.
PROTECTED_GLOBS: tuple[str, ...] = (
    "**/paseto*.py",
    "**/saml*.py",
    "**/auth*.py",
    "**/api_keys*.py",
    "**/jwks*.py",
    "**/scim*.py",
    "**/authorize*.py",
    "**/rate_limit*.py",
    "**/migrations/*rls*.py",
    "**/migrations/*audit*.py",
    "**/byo_vault*.py",
    "**/kms*.py",
    "**/secrets*.py",
    "**/workspace_encryption*.py",
    "**/audit_events*.py",
    "**/audit_export*.py",
)

THREAT_MODEL_DOC = "docs/THREAT_MODEL.md"
SKIP_TOKEN = "threat-model: skip"
MUTATING_DECORATOR_RE = re.compile(r"^\+\s*@router\.(post|put|patch|delete)\(")
AUDIT_ACTION_RE = re.compile(r"action\s*=\s*[\"']([^\"']+)[\"']")


def _matches_protected(path: str) -> str | None:
    """Return the matching glob, or ``None``."""
    # fnmatch handles ** only loosely; check both the full path and the
    # basename so '**/paseto*.py' matches 'packages/x/y/paseto_v4.py'.
    for glob in PROTECTED_GLOBS:
        if fnmatch.fnmatch(path, glob):
            return glob
        # fnmatch's '**' is just '*'; emulate recursion by also matching
        # the basename against the bare suffix.
        bare = glob.split("/")[-1]
        if fnmatch.fnmatch(Path(path).name, bare) and "/" not in glob.split("**/")[-1]:
            return glob
    return None


def _gather_paths(args: argparse.Namespace) -> list[str]:
    if args.changed_files and Path(args.changed_files).is_file():
        return [
            line.strip()
            for line in Path(args.changed_files).read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]
    env_path = os.environ.get("LOOP_GATE_CHANGED_FILES")
    if env_path and Path(env_path).is_file():
        return [
            line.strip()
            for line in Path(env_path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    inline = os.environ.get("LOOP_GATE_CHANGED_FILES_INLINE")
    if inline:
        return [line.strip() for line in inline.splitlines() if line.strip()]
    if not sys.stdin.isatty():
        return [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
    return []


def _is_route_module(path: str) -> bool:
    if not path.endswith(".py"):
        return False
    if "_tests/" in path:
        return False
    return "_routes_" in Path(path).name


def _new_mutating_route_files(
    changed: Iterable[str], *, base: str, head: str
) -> list[str]:
    hits: list[str] = []
    for path in changed:
        if not _is_route_module(path):
            continue

        diff = ""
        try:
            proc = subprocess.run(
                ["git", "diff", "--unified=0", f"{base}...{head}", "--", path],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                diff = proc.stdout
        except OSError:
            diff = ""

        if MUTATING_DECORATOR_RE.search(diff):
            hits.append(path)
    return hits


def _audit_action_namespaces(route_files: Iterable[str]) -> set[str]:
    namespaces: set[str] = set()
    for route_file in route_files:
        file_path = Path(route_file)
        if not file_path.is_file():
            continue
        text = file_path.read_text(encoding="utf-8")
        for action in AUDIT_ACTION_RE.findall(text):
            parts = action.split(":")
            if len(parts) >= 2:
                namespaces.add(":".join(parts[:2]))
            else:
                namespaces.add(action)
    return namespaces


def evaluate(
    *,
    changed: Iterable[str],
    pr_body: str = "",
    base: str = "origin/main",
    head: str = "HEAD",
    mutating_route_files: Iterable[str] | None = None,
) -> tuple[int, list[str]]:
    """Pure helper used by the CLI and by tests."""
    changed_list = list(changed)
    protected_hits: list[tuple[str, str]] = []
    for path in changed_list:
        glob = _matches_protected(path)
        if glob is not None and path != THREAT_MODEL_DOC:
            protected_hits.append((path, glob))

    route_hits = (
        list(mutating_route_files)
        if mutating_route_files is not None
        else _new_mutating_route_files(changed_list, base=base, head=head)
    )
    route_namespaces = _audit_action_namespaces(route_hits)

    log: list[str] = []
    if protected_hits:
        log.append(
            f"threat-model gate: {len(protected_hits)} protected path(s) touched:"
        )
        for path, glob in protected_hits:
            log.append(f"  - {path} (matches {glob})")

    if route_hits:
        log.append(
            "threat-model gate: detected newly added mutating route decorator(s) in:"
        )
        for route_file in route_hits:
            log.append(f"  - {route_file}")

    if not protected_hits and not route_hits:
        log.append("threat-model gate: no protected paths touched; passing.")
        return 0, log

    doc_updated = THREAT_MODEL_DOC in changed_list
    skip_present = SKIP_TOKEN in (pr_body or "")
    doc_text = ""
    if Path(THREAT_MODEL_DOC).is_file():
        doc_text = Path(THREAT_MODEL_DOC).read_text(encoding="utf-8")

    missing_namespaces = sorted(ns for ns in route_namespaces if ns not in doc_text)

    if route_namespaces:
        log.append(
            "threat-model gate: mutating route audit-action namespaces in scope: "
            + ", ".join(sorted(route_namespaces))
        )

    if skip_present:
        log.append(
            "threat-model gate: PR body contains "
            f"'{SKIP_TOKEN}'; passing with logged bypass."
        )
        return 0, log

    errors: list[str] = []
    if protected_hits and not doc_updated:
        errors.append(
            "update docs/THREAT_MODEL.md when STRIDE-protected paths are touched"
        )
    if missing_namespaces:
        errors.append(
            "missing STRIDE coverage for audit-action namespaces: "
            + ", ".join(missing_namespaces)
        )

    if not errors:
        if protected_hits and doc_updated:
            log.append(
                f"threat-model gate: {THREAT_MODEL_DOC} updated in this PR; passing."
            )
        log.append("threat-model gate: required STRIDE coverage present; passing.")
        return 0, log

    log.append("threat-model gate: FAIL — " + "; ".join(errors) + ".")
    return 2, log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--changed-files",
        help="Path to a file with one changed path per line.",
    )
    parser.add_argument(
        "--pr-body",
        default=os.environ.get("LOOP_GATE_PR_BODY", ""),
        help="PR body text (used to look for the skip token).",
    )
    parser.add_argument(
        "--base",
        default=os.environ.get("LOOP_GATE_BASE_REF", "origin/main"),
        help="Git base ref used to detect newly added mutating decorators.",
    )
    parser.add_argument(
        "--head",
        default=os.environ.get("LOOP_GATE_HEAD_REF", "HEAD"),
        help="Git head ref used to detect newly added mutating decorators.",
    )
    args = parser.parse_args(argv)
    paths = _gather_paths(args)
    code, log = evaluate(
        changed=paths,
        pr_body=args.pr_body,
        base=args.base,
        head=args.head,
    )
    for line in log:
        print(line)
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
