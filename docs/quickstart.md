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

## 3. Run the support example

```sh
cp examples/support_agent/.env.example examples/support_agent/.env
# edit .env to set ANTHROPIC_API_KEY (or leave it blank to use the stub gateway)
uv run loop dev examples/support_agent
```

## 4. Send a message

In another shell:

```sh
uv run loop chat examples/support_agent "Where is order 4172?"
```

You should see a streamed response that includes a tool call to
`lookup_order` and a final answer.

## 5. Run the eval suite

```sh
uv run python examples/support_agent/run_eval.py
```

## Next steps

- Read [concepts/agents.md](./concepts/agents.md) to understand what just
  happened.
- Read [cookbook/support_agent.md](./cookbook/support_agent.md) to see how
  the example is wired together end-to-end.
