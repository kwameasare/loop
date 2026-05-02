#!/usr/bin/env python3
"""tools/agent_lifecycle.py — full self-managed agent lifecycle.

ONE command per phase. Agents run these instead of crafting bespoke git +
edit-file + commit + gh-pr-create dances. Every subcommand is idempotent
where safe and refuses-loudly when state is wrong.

Subcommands:

    init        Create the agent's own git worktree at ../bot-<owner>/.
                Refuses if the main repo has uncommitted changes. Prints
                the absolute worktree path for the agent's tools to
                operate on. (Wraps scripts/spawn_agent_worktree.sh.)

    status      Print the agent's current state: worktree path, current
                branch, currently-claimed story (if any), last heartbeat,
                gate-readiness (uncommitted? unpushed?). Read-only.

    pick        Recommend the next story for this agent to claim.
                (Wraps tools/pick_next_story.py.) Prints the id (and AC
                with --json). Does NOT reserve the story — that happens
                only when `claim` merges.

    claim <SID> Execute the full claim flow:
                  1. Fetch origin and rebase the worktree's scratch
                     branch on origin/main.
                  2. Create branch <owner>/<sid>-<slug>.
                  3. Rewrite the StoryV2 line for SID:
                       owner=<owner>, status="In progress",
                       notes_override=<canonical structured block>.
                  4. Regenerate tracker + run check_tracker_notes.
                  5. Commit "chore(tracker): claim SID".
                  6. Push.
                  7. (Optional, with --pr) open a claim PR via gh CLI.
                Refuses if the agent already has an open claim.

    checkpoint <SID> --step N/M --note "..."
                Append a heartbeat. Updates StoryV2 notes_override to
                bump Heartbeat (current UTC) and Last step (N/M), records
                the one-line note. Commits "chore(tracker): checkpoint
                SID step N/M — <note>". Pushes. Required ≤30 min apart
                during active work.

    close <SID> [--pr-url URL]
                Execute the close flow:
                  1. Run all local gates (ruff, format, pyright, pytest,
                     check_tracker_notes, check_docs_with_code,
                     check_checkpoint_discipline, check_no_bulk_close).
                  2. Rewrite the StoryV2 line for SID:
                       status="Done",
                       notes_override=<canonical Done block> with
                       PR-url, final heartbeat, tests, docs touched,
                       follow-ups.
                  3. Regenerate tracker + run check_tracker_notes.
                  4. Commit "chore(tracker): close SID".
                  5. Push.
                  6. (Optional, with --pr) open the close PR.
                Refuses if any gate fails.

    teardown    Remove this agent's worktree (wraps scripts/cleanup_-
                agent_worktree.sh). Refuses if any uncommitted changes
                or unpushed commits remain.

The agent's identity (`<owner>`) is read from the LOOP_AGENT_ID env var
or from --owner. Set it once in the start prompt.

Exit codes:
    0  success
    1  gate failed / preconditions not met / runtime error
    2  usage error
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# Paths and helpers
# ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = SCRIPT_DIR.parent  # …/bot or …/bot-<owner>
STORIES_V2 = SCRIPT_DIR / "_stories_v2.py"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(
    cmd: list[str], *, cwd: Path | None = None, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess:
    """Run a command, surface output. Raise on failure unless check=False."""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=capture,
    )


def _git(args: list[str], cwd: Path, *, capture: bool = False) -> str:
    cp = _run(["git", *args], cwd=cwd, capture=capture)
    return cp.stdout if capture else ""


def _slug(text: str, max_len: int = 32) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len].rstrip("-") or "story"


def _resolve_owner(args_owner: str | None) -> str:
    owner = args_owner or os.environ.get("LOOP_AGENT_ID")
    if not owner:
        print(
            "agent_lifecycle: --owner is required (or set LOOP_AGENT_ID).\n"
            "  Use a stable lowercase identifier, e.g. claude-a, copilot-b.",
            file=sys.stderr,
        )
        sys.exit(2)
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,30}", owner):
        print(
            f"agent_lifecycle: owner must match ^[a-z][a-z0-9-]{{1,30}}$ "
            f"(got: {owner!r})",
            file=sys.stderr,
        )
        sys.exit(2)
    return owner


def _worktree_path(owner: str) -> Path:
    """Where this agent's worktree lives, relative to the main repo's parent."""
    return DEFAULT_REPO_ROOT.parent / f"bot-{owner}"


def _resolve_repo_root() -> Path:
    """Use git to resolve the working repo root — works whether we're in
    the main checkout or a worktree."""
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    return Path(out)


# ─────────────────────────────────────────────────────────────────────
# StoryV2 line surgery
# ─────────────────────────────────────────────────────────────────────
#
# Each story is exactly one line of the form:
#   StoryV2("S119", "title", "S2", "E12", 2, "P0", "AC: ...", owner="x",
#           status="...", notes_override="..."),
#
# We rewrite the line as a whole — find by id, replace by full
# reconstruction. This keeps two parallel agents claiming DIFFERENT
# stories on different lines, so they never conflict.

_STORY_LINE_RE = re.compile(
    r"""^(?P<indent>\s*)StoryV2\(\s*
        "(?P<id>S\d{3})"\s*,\s*
        "(?P<title>(?:\\.|[^"\\])*)"\s*,\s*
        "(?P<sprint>S\d+)"\s*,\s*
        "(?P<epic>E\d+|—)"\s*,\s*
        (?P<points>\d+)\s*,\s*
        "(?P<priority>P\d)"\s*,\s*
        "(?P<ac>(?:\\.|[^"\\])*)"\s*
        (?P<rest>.*)$""",
    re.VERBOSE,
)


def _quote(s: str) -> str:
    """Python-source-safe double-quote of an arbitrary string."""
    return (
        '"'
        + s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        + '"'
    )


def _rewrite_story_line(
    repo_root: Path,
    sid: str,
    *,
    owner: str | None,
    status: str | None,
    notes_override: str | None,
) -> None:
    """Find the StoryV2 line for `sid` and rewrite it preserving fields.

    Any of owner/status/notes_override that is None is removed (treated
    as 'go back to default'). Pass empty string explicitly to set blank.
    """
    path = repo_root / "tools" / "_stories_v2.py"
    if not path.exists():
        sys.exit(f"agent_lifecycle: cannot find {path}")
    text = path.read_text()
    new_lines: list[str] = []
    found = False
    for line in text.splitlines(keepends=True):
        m = _STORY_LINE_RE.match(line.rstrip("\n"))
        if not m or m.group("id") != sid:
            new_lines.append(line)
            continue
        found = True
        indent = m.group("indent")
        head = (
            f'{indent}StoryV2('
            f'"{m.group("id")}", '
            f'{_quote(m.group("title"))}, '
            f'"{m.group("sprint")}", '
            f'"{m.group("epic")}", '
            f'{m.group("points")}, '
            f'"{m.group("priority")}", '
            f'{_quote(m.group("ac"))}'
        )
        kwargs: list[str] = []
        if owner is not None:
            kwargs.append(f"owner={_quote(owner)}")
        if status is not None:
            kwargs.append(f"status={_quote(status)}")
        if notes_override is not None:
            kwargs.append(f"notes_override={_quote(notes_override)}")
        kw_part = (", " + ", ".join(kwargs)) if kwargs else ""
        # Trailing comma matches the original list style.
        ending = "),\n" if line.endswith(",\n") else "),\n"
        new_lines.append(f"{head}{kw_part}{ending}")
    if not found:
        sys.exit(f"agent_lifecycle: story id {sid!r} not found in {path}")
    path.write_text("".join(new_lines))


# ─────────────────────────────────────────────────────────────────────
# Notes-block templates
# ─────────────────────────────────────────────────────────────────────


def _claim_notes(
    *, owner: str, branch: str, skill: str, total_steps: int
) -> str:
    return (
        "**Active.**\n"
        f"Branch: {branch}\n"
        f"Skill: {skill}\n"
        f"Last step: 0/{total_steps} (just claimed)\n"
        f"Heartbeat: {_now_utc_iso()} ({owner})\n"
        "Open questions: none\n"
        "Blockers: none\n"
        "Commits: (will accumulate)"
    )


def _checkpoint_notes(*, current: str, owner: str, step: str, note: str) -> str:
    """Bump Heartbeat + Last step on top of an existing notes block."""
    out = re.sub(
        r"Last step:[^\n]*",
        f"Last step: {step}",
        current,
        count=1,
    )
    out = re.sub(
        r"Heartbeat:[^\n]*",
        f"Heartbeat: {_now_utc_iso()} ({owner})",
        out,
        count=1,
    )
    if note:
        # Prepend the latest checkpoint note to "Commits:" line.
        out = re.sub(
            r"(Commits:[^\n]*)",
            rf"\1\nLatest checkpoint: {note}",
            out,
            count=1,
        )
    return out


def _close_notes(
    *,
    owner: str,
    branch: str,
    skill: str,
    pr_url: str,
    tests_summary: str,
    docs_touched: str,
    follow_ups: str,
) -> str:
    return (
        "**Done.**\n"
        f"PR: {pr_url}\n"
        f"Branch: {branch} (merged + deletable)\n"
        f"Skill: {skill}\n"
        f"Final heartbeat: {_now_utc_iso()} ({owner})\n"
        f"Tests: {tests_summary}\n"
        f"Docs touched: {docs_touched}\n"
        f"Follow-ups: {follow_ups or 'none'}"
    )


# ─────────────────────────────────────────────────────────────────────
# Subcommands
# ─────────────────────────────────────────────────────────────────────


def cmd_init(args: argparse.Namespace) -> int:
    owner = _resolve_owner(args.owner)
    spawn = SCRIPT_DIR.parent / "scripts" / "spawn_agent_worktree.sh"
    if not spawn.exists():
        sys.exit(f"agent_lifecycle: missing {spawn}")
    return subprocess.call(["bash", str(spawn), owner])


def cmd_status(args: argparse.Namespace) -> int:
    owner = _resolve_owner(args.owner)
    repo = _resolve_repo_root()
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo, capture=True).strip()
    dirty = _git(["status", "--porcelain"], repo, capture=True).strip()
    # Upstream may not be configured (fresh local branches). Don't crash.
    cp = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        cwd=str(repo),
        text=True,
        capture_output=True,
    )
    upstream = cp.stdout.strip() if cp.returncode == 0 else "(none)"
    unpushed = ""
    if upstream != "(none)":
        cp = subprocess.run(
            ["git", "log", "--oneline", "@{u}..HEAD"],
            cwd=str(repo),
            text=True,
            capture_output=True,
        )
        unpushed = cp.stdout.strip() if cp.returncode == 0 else ""
    print(f"Owner:      {owner}")
    print(f"Repo root:  {repo}")
    print(f"Branch:     {branch}")
    print(f"Upstream:   {upstream or '(none)'}")
    print(f"Dirty:      {'yes' if dirty else 'no'}")
    print(f"Unpushed:   {unpushed.count(chr(10)) + 1 if unpushed else 0} commits")
    # Active claim — find a story whose owner matches and status is open.
    open_claims = _open_claims(repo, owner)
    if open_claims:
        for sid, status, notes in open_claims:
            print(f"\nOpen claim: {sid}  status={status}")
            for ln in notes.splitlines()[:5]:
                print(f"  {ln}")
    else:
        print("Open claim: none")
    return 0


def _open_claims(repo: Path, owner: str) -> list[tuple[str, str, str]]:
    """Parse _stories_v2.py for stories where this owner has a non-Done open claim."""
    text = (repo / "tools" / "_stories_v2.py").read_text()
    out: list[tuple[str, str, str]] = []
    for m in re.finditer(
        r'StoryV2\(\s*"(?P<id>S\d{3})".*?'
        r'(?:owner="(?P<owner>[^"]*)")?.*?'
        r'(?:status="(?P<status>[^"]*)")?.*?'
        r'(?:notes_override="(?P<notes>(?:\\.|[^"\\])*)")?',
        text,
        re.DOTALL,
    ):
        if (
            m.group("owner") == owner
            and m.group("status") in {"In progress", "Handing off", "Blocked"}
        ):
            out.append(
                (m.group("id"), m.group("status"), (m.group("notes") or "").replace("\\n", "\n"))
            )
    return out


def cmd_pick(args: argparse.Namespace) -> int:
    owner = _resolve_owner(args.owner)
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "pick_next_story.py"),
        "--owner",
        owner,
        "--assigned-to",
        owner,
    ]
    if args.json:
        cmd.append("--json")
    if args.avoid_hot_files:
        cmd.append("--avoid-hot-files")
    return subprocess.call(cmd)


def cmd_claim(args: argparse.Namespace) -> int:
    owner = _resolve_owner(args.owner)
    sid = args.sid.upper()
    repo = _resolve_repo_root()

    # Refuse double-claim: one open claim per agent.
    open_now = _open_claims(repo, owner)
    if open_now:
        prev = ", ".join(s for s, _, _ in open_now)
        print(
            f"agent_lifecycle: refusing — {owner} already has an open "
            f"claim: {prev}. Close or hand off first.",
            file=sys.stderr,
        )
        return 1

    # Get title for the slug; verify the story exists.
    text = (repo / "tools" / "_stories_v2.py").read_text()
    m = re.search(
        rf'StoryV2\(\s*"{sid}"\s*,\s*"((?:\\.|[^"\\])*)"\s*,\s*"(S\d+)"',
        text,
    )
    if not m:
        print(f"agent_lifecycle: story {sid} not found in _stories_v2.py", file=sys.stderr)
        return 1
    title = m.group(1).encode().decode("unicode_escape")
    branch = f"{owner}/{sid.lower()}-{_slug(title)}"

    print(f"agent_lifecycle: claiming {sid} on branch {branch}")
    _git(["fetch", "origin"], repo)
    _git(["checkout", "-B", branch, "origin/main"], repo)
    notes = _claim_notes(
        owner=owner, branch=branch, skill=args.skill, total_steps=args.steps
    )
    _rewrite_story_line(
        repo, sid, owner=owner, status="In progress", notes_override=notes
    )
    _run([sys.executable, "tools/build_tracker.py"], cwd=repo)
    _run([sys.executable, "tools/check_tracker_notes.py"], cwd=repo)
    _git(["add", "tools/_stories_v2.py", "loop_implementation/tracker/"], repo)
    _git(["commit", "-m", f"chore(tracker): claim {sid}"], repo)
    if not args.no_push:
        _git(["push", "-u", "origin", branch], repo)
    if args.pr:
        _open_pr(
            repo,
            title=f"chore(tracker): claim {sid}",
            body=f"Claim {sid}: {title}\n\nSkill: {args.skill}\nOwner: {owner}",
        )
    print(f"agent_lifecycle: claimed {sid}.")
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    owner = _resolve_owner(args.owner)
    sid = args.sid.upper()
    repo = _resolve_repo_root()
    text = (repo / "tools" / "_stories_v2.py").read_text()
    m = re.search(
        rf'StoryV2\(\s*"{sid}".*?notes_override="(?P<notes>(?:\\.|[^"\\])*)"',
        text,
        re.DOTALL,
    )
    if not m:
        print(
            f"agent_lifecycle: {sid} has no claim notes — claim first.",
            file=sys.stderr,
        )
        return 1
    current = m.group("notes").encode().decode("unicode_escape")
    new_notes = _checkpoint_notes(
        current=current, owner=owner, step=args.step, note=args.note
    )
    _rewrite_story_line(repo, sid, owner=owner, status="In progress", notes_override=new_notes)
    _run([sys.executable, "tools/build_tracker.py"], cwd=repo)
    _run([sys.executable, "tools/check_tracker_notes.py"], cwd=repo)
    _git(["add", "tools/_stories_v2.py", "loop_implementation/tracker/"], repo)
    _git(
        ["commit", "-m", f"chore(tracker): checkpoint {sid} step {args.step} — {args.note}"],
        repo,
    )
    if not args.no_push:
        _git(["push"], repo)
    print(f"agent_lifecycle: checkpoint {sid} step {args.step} recorded.")
    return 0


def _run_gate(label: str, cmd: list[str], repo: Path) -> bool:
    print(f"  → {label} …", end=" ", flush=True)
    cp = subprocess.run(cmd, cwd=str(repo), text=True, capture_output=True)
    if cp.returncode == 0:
        print("ok")
        return True
    print("FAIL")
    print(cp.stdout)
    print(cp.stderr, file=sys.stderr)
    return False


def cmd_close(args: argparse.Namespace) -> int:
    owner = _resolve_owner(args.owner)
    sid = args.sid.upper()
    repo = _resolve_repo_root()

    # 1) Gates.
    print(f"agent_lifecycle: running close gates for {sid}")
    gates: list[tuple[str, list[str]]] = [
        ("ruff check", ["uv", "run", "ruff", "check", "."]),
        ("ruff format", ["uv", "run", "ruff", "format", "--check", "."]),
        ("pyright", ["uv", "run", "pyright"]),
        ("pytest (unit)", ["uv", "run", "pytest", "-q", "-m", "not integration and not e2e"]),
        ("tracker-notes", [sys.executable, "tools/check_tracker_notes.py"]),
        (
            "docs-with-code",
            [sys.executable, "tools/check_docs_with_code.py", "--base", "origin/main", "--head", "HEAD"],
        ),
        (
            "checkpoint-discipline",
            [sys.executable, "tools/check_checkpoint_discipline.py", "--base", "origin/main", "--head", "HEAD"],
        ),
        (
            "no-bulk-close",
            [sys.executable, "tools/check_no_bulk_close.py", "--base", "origin/main", "--head", "HEAD"],
        ),
    ]
    if args.skip_gates:
        print("agent_lifecycle: --skip-gates set; bypassing local gates (NOT recommended).")
    else:
        for label, cmd in gates:
            if not _run_gate(label, cmd, repo):
                print(f"agent_lifecycle: gate {label!r} failed; not closing.", file=sys.stderr)
                return 1

    # 2) Branch + repo state.
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo, capture=True).strip()
    skill = args.skill or "(unspecified)"
    notes = _close_notes(
        owner=owner,
        branch=branch,
        skill=skill,
        pr_url=args.pr_url or "(opened by squash-merge)",
        tests_summary=args.tests or "ruff+format+pyright+pytest -q + 4 tracker gates",
        docs_touched=args.docs or "(none)",
        follow_ups=args.follow_ups or "none",
    )
    _rewrite_story_line(repo, sid, owner=owner, status="Done", notes_override=notes)
    _run([sys.executable, "tools/build_tracker.py"], cwd=repo)
    _run([sys.executable, "tools/check_tracker_notes.py"], cwd=repo)
    _git(["add", "tools/_stories_v2.py", "loop_implementation/tracker/"], repo)
    _git(["commit", "-m", f"chore(tracker): close {sid}"], repo)
    if not args.no_push:
        _git(["push"], repo)
    if args.pr:
        title_line = f"feat(tracker): close {sid}"
        if args.story_title:
            title_line = f"feat({_slug(args.story_title)[:24]}): {args.story_title} ({sid})"
        _open_pr(
            repo,
            title=title_line,
            body=f"Closes {sid}.\n\nSkill: {skill}\nTests: {args.tests or 'all gates green'}\nDocs touched: {args.docs or 'none'}\nFollow-ups: {args.follow_ups or 'none'}",
        )
    print(f"agent_lifecycle: closed {sid}.")
    return 0


def cmd_teardown(args: argparse.Namespace) -> int:
    owner = _resolve_owner(args.owner)
    cleanup = SCRIPT_DIR.parent / "scripts" / "cleanup_agent_worktree.sh"
    if not cleanup.exists():
        sys.exit(f"agent_lifecycle: missing {cleanup}")
    cmd = ["bash", str(cleanup), owner]
    if args.force:
        cmd.append("--force")
    return subprocess.call(cmd)


def _open_pr(repo: Path, *, title: str, body: str) -> None:
    """Open a PR via gh CLI. Best effort — don't fail the lifecycle step if gh isn't configured."""
    cp = subprocess.run(
        ["gh", "pr", "create", "--title", title, "--body", body, "--fill-first"],
        cwd=str(repo),
        text=True,
        capture_output=True,
    )
    if cp.returncode == 0:
        print(cp.stdout.strip())
    else:
        print(
            f"agent_lifecycle: gh pr create failed ({cp.returncode}). "
            f"Open the PR manually:\n  title: {title}",
            file=sys.stderr,
        )
        print(cp.stderr, file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="agent_lifecycle",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--owner",
        help="Agent identity (e.g. claude-a). Falls back to $LOOP_AGENT_ID.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create the agent's git worktree.")
    sub.add_parser("status", help="Show current state.")

    p_pick = sub.add_parser("pick", help="Recommend the next story to claim.")
    p_pick.add_argument("--json", action="store_true")
    p_pick.add_argument("--avoid-hot-files", action="store_true")

    p_claim = sub.add_parser("claim", help="Claim a story.")
    p_claim.add_argument("sid", help="Story id (e.g. S119)")
    p_claim.add_argument(
        "--skill",
        required=True,
        help="Skill file you'll apply, e.g. skills/api/add-rest-endpoint.md",
    )
    p_claim.add_argument(
        "--steps", type=int, default=5, help="Total number of steps planned (default 5)"
    )
    p_claim.add_argument("--no-push", action="store_true")
    p_claim.add_argument("--pr", action="store_true", help="Open claim PR via gh")

    p_chk = sub.add_parser("checkpoint", help="Record a heartbeat / step bump.")
    p_chk.add_argument("sid", help="Story id (e.g. S119)")
    p_chk.add_argument("--step", required=True, help='Like "2/5"')
    p_chk.add_argument("--note", required=True, help="One-line summary of what just landed")
    p_chk.add_argument("--no-push", action="store_true")

    p_close = sub.add_parser("close", help="Close a story (run gates, mark Done, push).")
    p_close.add_argument("sid", help="Story id (e.g. S119)")
    p_close.add_argument("--skill", help="Skill file applied")
    p_close.add_argument("--pr-url", help="URL of the close PR (if already opened)")
    p_close.add_argument("--tests", help="One-line test summary")
    p_close.add_argument("--docs", help="Comma-separated paths of docs you touched")
    p_close.add_argument("--follow-ups", help="Comma-separated SXXX ids of follow-up stories")
    p_close.add_argument("--story-title", help="Used to render PR title")
    p_close.add_argument("--no-push", action="store_true")
    p_close.add_argument("--pr", action="store_true", help="Open close PR via gh")
    p_close.add_argument("--skip-gates", action="store_true", help="Bypass local gates (NOT recommended)")

    p_td = sub.add_parser("teardown", help="Remove the agent's worktree.")
    p_td.add_argument("--force", action="store_true")

    args = ap.parse_args()
    return {
        "init": cmd_init,
        "status": cmd_status,
        "pick": cmd_pick,
        "claim": cmd_claim,
        "checkpoint": cmd_checkpoint,
        "close": cmd_close,
        "teardown": cmd_teardown,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
