#!/usr/bin/env python3
"""
tracker_to_machine.py — xlsx companion regenerator (currently a no-op stub).

The IMPLEMENTATION_TRACKER.xlsx file is the human-facing companion to
``tools/build_tracker.py``. Regenerating it requires ``openpyxl`` and a recalc
pass; both are deliberately deferred (see S001 PR notes). For now the .xlsx is
treated as a stale artifact — humans should consult ``tracker/TRACKER.md``,
``tracker/tracker.json``, or ``tracker/csv/*.csv`` instead.

This stub exits 0 so the documented invocation chain
``python tools/build_tracker.py && python tools/tracker_to_machine.py`` keeps
working in CI and skill instructions.

When the xlsx work is picked up, replace this body with the real renderer.
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "tracker_to_machine.py: xlsx regen deferred — see S001 PR. "
        "tracker/TRACKER.md / tracker.json / csv/*.csv are the live outputs.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
