# Quickstart

Five minutes from clone to first turn.

## Prerequisites

- macOS or Linux
- `uv` 0.5+
- Docker (for the local stack)
- Anthropic API key

## 1. Clone and bootstrap

```sh
git clone https://github.com/loop-ai/loop.git
cd loop
uv sync
```

## 2. Start the local stack

```sh
make up
```

This brings up Postgres, Redis, the OTel collector, and a tiny stub
gateway that fakes Claude responses so you can iterate offline.

## 3. Run the support example against a real LLM

The reference example streams a real OpenAI or Anthropic response and
executes the `lookup_order` tool when the model asks for it.

```sh
# pick whichever provider you have a key for; OpenAI is preferred when both are set
export OPENAI_API_KEY=sk-...
# or
export ANTHROPIC_API_KEY=...

uv run python examples/support_agent/run_local.py "where is order 4172?"
```

You should see a streamed response that includes a tool call to
`lookup_order` and a final answer that quotes the (fixture) order
status. Force a specific provider with `LOOP_SUPPORT_PROVIDER=openai`
or `LOOP_SUPPORT_PROVIDER=anthropic`.

## 4. Run the eval suite

```sh
uv run python examples/support_agent/run_eval.py
```

## Next steps

- Read [concepts/agents.md](./concepts/agents.md) to understand what just
  happened.
- Read [cookbook/support_agent.md](./cookbook/support_agent.md) to see how
  the example is wired together end-to-end.
