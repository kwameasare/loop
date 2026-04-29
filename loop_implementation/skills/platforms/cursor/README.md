# Cursor adapter

Cursor uses two formats:
- **Legacy**: `.cursorrules` at repo root (single rules file).
- **Modern**: `.cursor/rules/<name>.mdc` (per-rule files with frontmatter; Cursor 0.45+).

Loop ships both. The modern path mirrors the canonical skills 1-to-1.

## Install — legacy

```bash
cp loop_implementation/skills/platforms/cursor/.cursorrules .cursorrules
```

## Install — modern (recommended)

```bash
mkdir -p .cursor/rules
cp -r loop_implementation/skills/platforms/cursor/rules/*.mdc .cursor/rules/
```

Restart Cursor. The rules apply to chat, inline edits, and the Composer.

## Format — `.mdc` files

Each `.mdc` file has a Cursor-specific frontmatter:

```markdown
---
description: <when to apply this rule>
globs:
  - "packages/runtime/**"
  - "packages/sdk-py/**"
alwaysApply: false
---

# <Skill name>

<copy of canonical skill body>
```

`globs` tell Cursor which files to apply the rule to. `alwaysApply: true` makes it apply globally (used for the SKILL_ROUTER).

## Generated from

The `.mdc` files mirror `loop_implementation/skills/<category>/<name>.md` 1-to-1. Re-run:

```bash
python tools/build_platform_adapters.py --target=cursor
```

## Skills mapping

The base router (`_base/SKILL_ROUTER.md`) becomes `_base.mdc` with `alwaysApply: true`. Every other skill becomes a `.mdc` with `globs` derived from the skill's likely path coverage:

| Skill | Globs |
|-------|-------|
| `coding/implement-runtime-feature.md` | `packages/runtime/**`, `packages/sdk-py/**` |
| `coding/implement-llm-gateway-change.md` | `packages/gateway/**` |
| `coding/implement-mcp-tool.md` | `packages/runtime/**`, `examples/**`, `tools/mcp/**` |
| `coding/implement-channel-adapter.md` | `packages/channels/**` |
| `coding/implement-kb-feature.md` | `packages/kb-engine/**` |
| `coding/implement-eval-scorer.md` | `packages/eval-harness/**` |
| `coding/implement-studio-screen.md` | `apps/studio/**` |
| `coding/implement-cli-command.md` | `cli/**` |
| `data/add-postgres-migration.md` | `**/migrations/**`, `**/alembic/**` |
| `data/add-pydantic-type.md` | `packages/sdk-py/loop/types.py` |
| `api/add-rest-endpoint.md` | `apps/control-plane/**`, `api/openapi.yaml` |
| `ux/*` | `apps/studio/**` |
| `testing/*` | `**/_tests/**`, `**/tests/**` |
| `security/*` | `apps/control-plane/**`, `packages/observability/**` |

This means Cursor only surfaces relevant skills based on the file you're editing, reducing noise.
