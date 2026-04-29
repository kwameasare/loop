# Windsurf adapter

## Install

Copy `.windsurfrules` to repo root:

```bash
cp loop_implementation/skills/platforms/windsurf/.windsurfrules .windsurfrules
```

Restart Windsurf. The rules apply to Cascade (chat), inline edits, and the Tab autocomplete model.

## Behavior

Windsurf reads `.windsurfrules` and applies it to every interaction. The rules:
- Tell Cascade to read AGENTS.md + SKILL_ROUTER first.
- List the hard rules every change follows.
- Reference the canonical skills folder.

For more granular per-folder rules, Windsurf 0.10+ supports `.windsurfrules.<glob>` files. The Loop convention does not yet use those — the central skills folder + the canonical SKILL_ROUTER suffice.

## Skills location

`loop_implementation/skills/` — same folder Cursor/Claude/Copilot use. Single source of truth.
