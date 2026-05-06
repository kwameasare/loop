# tools/

Repo-level Python scripts. No dependencies beyond the stdlib.

| Script | Purpose |
|---|---|
| `build_tracker.py` | **Source of truth** for the implementation tracker. Renders `loop_implementation/tracker/TRACKER.md`, `tracker.json`, and `csv/*.csv`. Run with `--check` to fail CI on drift. |
| `tracker_to_machine.py` | xlsx companion regenerator — currently a no-op stub. Will be replaced when the xlsx workflow is reactivated. |
| `_stories_ux.py` | Planning source for the canonical target UX/UI implementation cycle. Not wired into the production tracker until explicitly activated. |
| `_agent_assignments_ux.py` | Four-agent partition for the UX/UI cycle, including start-first foundation stories and dependency gates. |

See `loop_implementation/skills/meta/update-tracker.md` for the tracker lifecycle protocol.
