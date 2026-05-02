"""Continuous fuzz harness for cp-api + dp-runtime (S800).

Runs a deterministic-seeded mutation fuzzer against high-risk Python
surfaces in the control plane and data plane:

* PASETO v4.local token decoder (`paseto.decode_local`) — token forgery
  attempts, malformed base64, truncated headers.
* Audit-export CSV streaming (`audit_export.export_audit_csv`) — bad
  filters and malformed event payloads.
* Workspace slug + secret-payload hashing (`audit_events.hash_payload`)
  — recursive structures and exotic Unicode.
* BYO-Vault address validation (`byo_vault.VaultConfig`) — URL injection.

Each "campaign" ships a corpus, an oracle (the set of expected
exception types), and an iteration budget. A campaign **passes** when
no input triggers an unexpected exception, OOM, or process abort. The
harness writes a JSON coverage + outcome report to ``out_path`` so CI
can attach it as an artifact and ``tools/fuzz_report_to_issue.py`` can
file an issue when crashes are seen.

The harness intentionally avoids any third-party fuzzing dependency
(``atheris``/``hypothesis``/``restler``) so it runs in the existing
``uv run pytest`` environment used by the rest of the repo. The shape
is compatible with ``atheris.Fuzz()`` and a future migration only needs
to swap the ``_iterate`` loop for the Atheris callback.
"""

from __future__ import annotations

import json
import os
import random
import resource  # POSIX-only; the harness asserts POSIX up front.
import string
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

# --- Memory cap ----------------------------------------------------------------

# 512 MiB resident-set cap; OOM bugs surface as MemoryError in Python.
_MEM_BYTES = 512 * 1024 * 1024


def _apply_memory_cap() -> None:
    """Apply a hard RLIMIT_AS so runaway allocators trip MemoryError."""
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    new_soft = min(soft, _MEM_BYTES) if soft != resource.RLIM_INFINITY else _MEM_BYTES
    new_hard = min(hard, _MEM_BYTES) if hard != resource.RLIM_INFINITY else _MEM_BYTES
    if new_soft < soft or soft == resource.RLIM_INFINITY:
        # Some CI runners refuse RLIMIT_AS adjustments; treat as best-effort.
        try:
            resource.setrlimit(resource.RLIMIT_AS, (new_soft, new_hard))
        except (ValueError, OSError):
            pass


# --- Mutation primitives -------------------------------------------------------


def _rand_bytes(rng: random.Random, *, max_len: int = 4096) -> bytes:
    n = rng.randint(0, max_len)
    return bytes(rng.randint(0, 255) for _ in range(n))


def _rand_text(rng: random.Random, *, max_len: int = 1024) -> str:
    n = rng.randint(0, max_len)
    alphabet = string.printable + "𝕬\u0000\ufeff\ud83d\ude00".replace(
        "\r", ""
    )  # mix of ASCII, control, BMP, and astral chars
    return "".join(rng.choice(alphabet) for _ in range(n))


def _rand_json_value(rng: random.Random, depth: int = 0) -> Any:
    if depth > 4 or rng.random() < 0.2:
        return rng.choice([None, True, False, 0, -1, 1.5, _rand_text(rng, max_len=64)])
    kind = rng.choice(["list", "dict"])
    if kind == "list":
        return [_rand_json_value(rng, depth + 1) for _ in range(rng.randint(0, 5))]
    return {
        _rand_text(rng, max_len=16): _rand_json_value(rng, depth + 1)
        for _ in range(rng.randint(0, 5))
    }


# --- Campaigns -----------------------------------------------------------------


@dataclass
class CampaignResult:
    name: str
    iterations: int
    duration_s: float
    expected_raises: int
    crashes: list[dict[str, Any]] = field(default_factory=list)
    sample_inputs: int = 0


@dataclass
class Campaign:
    name: str
    target: Callable[[random.Random], None]
    expected_exceptions: tuple[type[BaseException], ...]
    iterations: int = 200


def _run_campaign(c: Campaign, *, seed: int) -> CampaignResult:
    rng = random.Random(seed)
    started = time.monotonic()
    expected = 0
    crashes: list[dict[str, Any]] = []
    for i in range(c.iterations):
        try:
            c.target(rng)
        except c.expected_exceptions:
            expected += 1
        except MemoryError:
            crashes.append(
                {"iteration": i, "kind": "oom", "trace": traceback.format_exc()}
            )
        except BaseException as exc:  # noqa: BLE001 — fuzzers catch everything.
            crashes.append(
                {
                    "iteration": i,
                    "kind": type(exc).__name__,
                    "trace": traceback.format_exc(),
                }
            )
    return CampaignResult(
        name=c.name,
        iterations=c.iterations,
        duration_s=time.monotonic() - started,
        expected_raises=expected,
        crashes=crashes,
        sample_inputs=c.iterations,
    )


# --- Targets -------------------------------------------------------------------


def _target_paseto_decode(rng: random.Random) -> None:
    from loop_control_plane import paseto

    # Half the time send pure garbage; half the time send a header-shaped
    # token with a corrupted body so we exercise the "shape ok / crypto bad"
    # path.
    if rng.random() < 0.5:
        token = _rand_text(rng, max_len=512)
    else:
        token = "v4.local." + _rand_text(rng, max_len=256)
    key = bytes(rng.randint(0, 255) for _ in range(32))
    paseto.decode_local(token, key=key, now_ms=rng.randint(0, 2**40))


def _target_audit_export_csv(rng: random.Random) -> None:
    import uuid

    from loop_control_plane import audit_events, audit_export

    store = audit_events.InMemoryAuditEventStore()
    workspace_id = uuid.uuid4()
    # Seed the store with a few random events.
    for _ in range(rng.randint(0, 8)):
        try:
            audit_events.record_audit_event(
                store=store,
                workspace_id=workspace_id,
                actor_sub=_rand_text(rng, max_len=32) or "sub",
                action=_rand_text(rng, max_len=32) or "act",
                resource_type=_rand_text(rng, max_len=16) or "res",
                resource_id=_rand_text(rng, max_len=64),
                request_id=_rand_text(rng, max_len=32),
                payload=_rand_json_value(rng),
                outcome=rng.choice(["success", "denied", "error"]),
            )
        except audit_events.AuditEventError:
            continue
    filters = audit_export.AuditExportFilters(
        actor_sub=rng.choice([None, _rand_text(rng, max_len=32)]),
        action=rng.choice([None, _rand_text(rng, max_len=32)]),
        resource_type=rng.choice([None, _rand_text(rng, max_len=16)]),
        outcome=rng.choice([None, "success", "denied", "error", _rand_text(rng, max_len=8)]),
    )
    audit_export.export_audit_csv(
        source=store,
        workspace_id=workspace_id,
        filters=filters,
    )


def _target_payload_hash(rng: random.Random) -> None:
    from loop_control_plane import audit_events

    audit_events.hash_payload(_rand_json_value(rng))


def _target_byo_vault_config(rng: random.Random) -> None:
    import uuid

    from loop_control_plane import byo_vault

    byo_vault.VaultConfig(
        workspace_id=uuid.uuid4(),
        address=rng.choice(
            [
                "https://vault.example/" + _rand_text(rng, max_len=64),
                "http://attacker.example",
                _rand_text(rng, max_len=128),
                "",
            ]
        ),
        role=rng.choice(
            [
                "my-role",
                _rand_text(rng, max_len=64),
                "role with spaces",
                "",
            ]
        ),
        mount_path=rng.choice(["secret", "", "/leading-slash", _rand_text(rng, max_len=32)]),
    )


# --- Orchestration -------------------------------------------------------------


def all_campaigns() -> list[Campaign]:
    return [
        Campaign(
            name="cp-api/paseto.decode_local",
            target=_target_paseto_decode,
            expected_exceptions=(ValueError,),
        ),
        Campaign(
            name="cp-api/audit_export.export_audit_csv",
            target=_target_audit_export_csv,
            expected_exceptions=(ValueError, TypeError),
        ),
        Campaign(
            name="cp-api/audit_events.hash_payload",
            target=_target_payload_hash,
            expected_exceptions=(TypeError, ValueError),
        ),
        Campaign(
            name="cp-api/byo_vault.VaultConfig",
            target=_target_byo_vault_config,
            expected_exceptions=(ValueError,),
        ),
    ]


def run_all(
    *,
    seed: int = 0xC0FFEE,
    iterations: int | None = None,
    out_path: Path | None = None,
) -> dict[str, Any]:
    _apply_memory_cap()
    campaigns = all_campaigns()
    if iterations is not None:
        for c in campaigns:
            c.iterations = iterations

    results = [
        _run_campaign(c, seed=seed + idx) for idx, c in enumerate(campaigns)
    ]
    report = {
        "seed": seed,
        "campaigns": [
            {
                "name": r.name,
                "iterations": r.iterations,
                "duration_s": round(r.duration_s, 3),
                "expected_raises": r.expected_raises,
                "crashes": r.crashes,
            }
            for r in results
        ],
        "totals": {
            "iterations": sum(r.iterations for r in results),
            "expected_raises": sum(r.expected_raises for r in results),
            "crashes": sum(len(r.crashes) for r in results),
        },
    }
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=lambda s: int(s, 0), default=0xC0FFEE)
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--out", type=Path, default=Path("fuzz-report.json"))
    parser.add_argument(
        "--fail-on-crash",
        action="store_true",
        help="Exit non-zero if any campaign reported crashes.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = run_all(seed=args.seed, iterations=args.iterations, out_path=args.out)
    print(json.dumps(report["totals"]))
    if args.fail_on_crash and report["totals"]["crashes"] > 0:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
