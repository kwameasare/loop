# Claude Skills adapter

Loop's canonical skills are **already** Claude Skills. The frontmatter format (`name`, `description`, `when_to_use`) and the file structure (`SKILL.md` per folder) match Anthropic's Claude Skills spec out of the box.

## Install (Claude Code, Claude Desktop, Claude Agent SDK)

### Project-scoped install

Drop the `skills/` folder into your project. Claude Code auto-discovers any folder named `skills/` containing `SKILL.md` files.

```bash
# in your loop monorepo root
mkdir -p .claude
ln -s ../loop_implementation/skills .claude/skills
```

### Workspace-scoped install

```bash
# Claude Code config
mkdir -p ~/.claude/skills/loop
ln -s /path/to/loop_implementation/skills ~/.claude/skills/loop
```

### Claude Agent SDK (programmatic)

Pass the skills folder as `skills_dir` when constructing the Agent:

```python
from claude_agent_sdk import Agent

agent = Agent(
    instructions=open("AGENTS.md").read(),
    skills_dir="loop_implementation/skills",
)
```

## Notes

- Each `SKILL.md`'s frontmatter is parsed by Claude. `when_to_use` is the trigger; the body is the body.
- `_base/SKILL_ROUTER.md` should be loaded first; configure it as a "primary skill" or include it explicitly in the system prompt:
  ```
  Always read loop_implementation/skills/_base/SKILL_ROUTER.md first
  before consulting any other skill.
  ```
- Sub-folders (`coding/`, `data/`, etc.) are organizational — Claude Code finds `SKILL.md` files at any depth.

## Skill list

The skills are listed in `skills/README.md` §"Skill catalog".
