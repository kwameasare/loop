#!/usr/bin/env python3
"""
recalc.py — xlsx formula recalc stub.

The full recalc workflow (open ``IMPLEMENTATION_TRACKER.xlsx``, force formula
recomputation, save) requires ``openpyxl`` plus a headless Excel/LibreOffice
pass. Deferred per S001 PR; this stub is a placeholder so existing skill text
("python scripts/recalc.py tracker/IMPLEMENTATION_TRACKER.xlsx") doesn't fail.

Replace with the real implementation when the xlsx companion is reactivated.
"""
from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    target = argv[1] if len(argv) > 1 else "<unspecified>"
    print(
        f"recalc.py: xlsx recalc deferred for {target} — see S001 PR. No-op.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
