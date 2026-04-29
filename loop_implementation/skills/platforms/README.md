# Per-platform adapters

The canonical skills live in `loop_implementation/skills/<category>/<name>.md`. Each `<category>/<name>.md` is a portable Markdown file with frontmatter that natively works as a Claude Skill.

For other AI tools that expect a specific layout, the `platforms/` subfolders host adapter files. **Do not edit adapters directly** — re-generate them from the canonical skills via `tools/build_platform_adapters.py`.

## Supported platforms

| Platform | Adapter folder | Format | Install |
|----------|----------------|--------|---------|
| **Anthropic Claude** (Code, Desktop, Agent SDK) | `platforms/claude/` | Native — every `<skill>.md` is already a Claude Skill | symlink `.claude/skills/` to `loop_implementation/skills/` |
| **OpenAI Codex / Agents SDK / ChatGPT** | `platforms/codex/` | Single `system_prompt.md` | pass via `--instructions` or paste into the GPT |
| **GitHub Copilot** (Chat + Coding Agent) | `platforms/github-copilot/` | `copilot-instructions.md` + `prompts/*.prompt.md` | place at `.github/copilot-instructions.md` and `.github/prompts/` |
| **Cursor** | `platforms/cursor/` | `.cursorrules` (legacy) + `.cursor/rules/*.mdc` (modern) | copy to repo root |
| **Aider** | `platforms/aider/` | `CONVENTIONS.md` | `aider --read CONVENTIONS.md` or in `.aider.conf.yml` |
| **Windsurf / Codeium** | `platforms/windsurf/` | `.windsurfrules` | copy to repo root |
| **Continue.dev** | `platforms/continue/` | `.continue/rules/*.md` | copy to `.continue/rules/` |
| **Generic AGENTS.md spec** | `loop_implementation/AGENTS.md` | Standard `AGENTS.md` (root) | already at root; every modern tool reads it |

Other tools (Sourcegraph Cody, JetBrains AI Assistant, Tabnine, Amazon Q, Google Gemini Code Assist, Replit Agent, …) typically ingest one of:
- the standard `AGENTS.md` at the repo root, or
- a custom-instructions string they expect to be small.

For all of those, point them at:

1. `loop_implementation/AGENTS.md`
2. `loop_implementation/skills/_base/SKILL_ROUTER.md`

That covers the universal cases. If a tool has a more specific format that's worth supporting natively, add a new folder under `platforms/` and a generation target in `tools/build_platform_adapters.py`.

## Generation

The `tools/build_platform_adapters.py` script (TODO: implement during Sprint 1) takes the canonical skills and emits each platform's expected files. Behavior:

```bash
# regenerate all platforms
python tools/build_platform_adapters.py

# regenerate one platform
python tools/build_platform_adapters.py --target=cursor
```

Until that script exists, the adapter files are hand-maintained from the canonical skills. Keep them in sync.

## Versioning

Each platform's adapter files include the canonical-skill `last_reviewed` date. If the canonical skill is newer than the adapter, regenerate.
