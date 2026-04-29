# tools/

Repo-level Python scripts. No dependencies beyond the stdlib.

| Script | Purpose |
|---|---|
| `build_tracker.py` | **Source of truth** for the implementation tracker. Renders `loop_implementation/tracker/TRACKER.md`, `tracker.json`, and `csv/*.csv`. Run with `--check` to fail CI on drift. |
| `tracker_to_machine.py` | xlsx companion regenerator — currently a no-op stub. Will be replaced when the xlsx workflow is reactivated. |

See `loop_implementation/skills/meta/update-tracker.md` for the tracker lifecycle protocol.
