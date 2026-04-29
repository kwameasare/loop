# GitHub Copilot Prompt Files

GitHub Copilot Chat supports `.prompt.md` files for reusable prompts. Each Loop skill has a corresponding prompt file here that wraps the canonical skill body with Copilot's expected frontmatter.

## Install

Copy or symlink this folder into `.github/prompts/` at your repo root. Copilot Chat picks them up automatically.

```bash
mkdir -p .github/prompts
ln -s ../../loop_implementation/skills/platforms/github-copilot/prompts/*.prompt.md .github/prompts/
```

## Usage

In Copilot Chat:

```
/implement-runtime-feature

Make TurnExecutor support a new "trace" event type for retrieval.
```

Copilot reads the prompt file, follows the steps, and emits suggestions consistent with Loop's conventions.

## Generated from

Each prompt file is auto-generated from the canonical skill at `loop_implementation/skills/<category>/<name>.md`. Re-run:

```bash
python tools/build_platform_adapters.py --target=github-copilot
```

(This script lives at `loop_implementation/scaffolding/tools/build_platform_adapters.py` once written.)

## Available prompt files

The full list mirrors the skill catalog (40 skills). Examples:
- `implement-runtime-feature.prompt.md`
- `add-postgres-migration.prompt.md`
- `add-rest-endpoint.prompt.md`
- `write-eval-suite.prompt.md`
- `triage-incident.prompt.md`
- … (see `loop_implementation/skills/README.md` for the full list)

## Format

Each `.prompt.md` file:

```markdown
---
mode: agent
description: <one-line description>
---

# <Skill name>

<copy of the canonical skill body — Trigger, Required reading, Steps, Definition of done, Anti-patterns, References>

When invoked, follow the steps above for the user's task.
```

The frontmatter `mode: agent` lets Copilot's Coding Agent run the prompt as a multi-step workflow. `mode: ask` is also supported for chat-only prompts.
