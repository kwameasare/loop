"""Tests for object-store replication integrity check (S574 / RB-023)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNBOOKS = ROOT / "loop_implementation" / "engineering" / "RUNBOOKS.md"
DR_DOC = ROOT / "loop_implementation" / "engineering" / "DR.md"
DRIVER = ROOT / "scripts" / "objstore_integrity_check.sh"


def test_rb023_index_row_present() -> None:
    text = RUNBOOKS.read_text()
    assert "| RB-023 | Object-store replication integrity failure |" in text


def test_rb023_section_present() -> None:
    text = RUNBOOKS.read_text()
    assert "## RB-023 — Object-store replication integrity failure" in text
    # The runbook must reference the daily integrity driver script.
    assert "objstore_integrity_check.sh" in text


def test_dr_doc_links_to_rb023() -> None:
    text = DR_DOC.read_text()
    assert "objstore-integrity-check" in text
    assert "RB-023" in text


def test_driver_dry_run_produces_canonical_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            str(DRIVER),
            "--bucket=src-bucket",
            "--prefix=audit-log/",
            "--dest=dst-bucket",
            f"--out={out}",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "checked=3 failures=2" in proc.stderr
    summary = json.loads((out / "summary.json").read_text())
    assert summary["checked"] == 3
    assert summary["ok"] == 1
    assert summary["missing"] == 1
    assert summary["mismatch"] == 1
    assert summary["failures"] == 2
    # Integrity TSV has header + 3 data rows.
    rows = (out / "integrity.tsv").read_text().strip().splitlines()
    assert rows[0] == "bucket\tkey\tsource_etag\tdest_etag\tstatus"
    assert len(rows) == 4
    statuses = [r.split("\t")[4] for r in rows[1:]]
    assert sorted(statuses) == ["etag-mismatch", "missing", "ok"]
    # Prom snippet exposes the gauge that the alert binds to.
    prom = (out / "prom.txt").read_text()
    assert "loop_objstore_replication_integrity_failures" in prom
    assert 'bucket="src-bucket"' in prom


def test_driver_repair_mode_walks_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "integrity.tsv"
    manifest.write_text(
        "bucket\tkey\tsource_etag\tdest_etag\tstatus\n"
        "b1\tk1\tetag1\tetag1\tok\n"
        "b1\tk2\tetag2\t\tmissing\n"
        "b1\tk3\tetag3\tetagX\tetag-mismatch\n"
    )
    proc = subprocess.run(
        [str(DRIVER), "repair", "--manifest", str(manifest), "--dry-run"],
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    # Repair touches non-ok rows only; header row is skipped.
    assert out == {"mode": "repair", "repaired": 2, "dry_run": True}


def test_driver_refuses_missing_required_args() -> None:
    proc = subprocess.run([str(DRIVER), "--dry-run"], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "missing --bucket" in proc.stderr
