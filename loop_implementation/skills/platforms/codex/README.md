# OpenAI Codex / Agents SDK / ChatGPT custom GPTs adapter

OpenAI's family of agent tools (Codex CLI, OpenAI Agents SDK, ChatGPT custom GPTs, the Agents Builder) accepts a single instruction string. Loop's skills are exposed via a single composite system prompt that points at the canonical files.

## Install — OpenAI Agents SDK

```python
from openai import OpenAI
from openai_agents import Agent

client = OpenAI()

with open("loop_implementation/skills/platforms/codex/system_prompt.md") as f:
    system_prompt = f.read()

agent = Agent(
    name="loop-engineer",
    model="gpt-5",
    instructions=system_prompt,
    tools=[...],   # whatever tool set fits
)
```

## Install — Codex CLI

```bash
codex --instructions=loop_implementation/skills/platforms/codex/system_prompt.md
```

## Install — ChatGPT custom GPT

Paste the contents of `system_prompt.md` into the GPT's "Instructions" field. Upload the canonical skill files (`skills/`) as Knowledge.

## How it works

The single system prompt below tells the agent:
1. The product context.
2. Where the canonical docs live (`loop_implementation/`).
3. How to use the skills (read `_base/SKILL_ROUTER.md` first).
4. The hard rules every skill assumes.

The agent then reads the actual skill files at runtime via tool calls (file read, repo grep). The system prompt is the *router*; the skills themselves are the *knowledge*.

See `system_prompt.md` for the full prompt.
