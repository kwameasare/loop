# Loop scripted demos

Five copy-pasteable shell demos that exercise the canonical Loop
golden examples (G7 — `examples/support_agent/`) and produce
predictable transcripts. Designed for screen recordings,
walkthroughs, and design-partner calls.

## Quickstart

```bash
# Real LLM run -- requires a provider key:
export OPENAI_API_KEY=sk-...   # or ANTHROPIC_API_KEY=sk-ant-...
./scripts/demo/1_chat.sh
./scripts/demo/2_tool.sh
./scripts/demo/3_kb.sh
./scripts/demo/4_multiagent.sh
./scripts/demo/5_hitl.sh

# Hermetic CI run -- prints recorded transcripts, no provider needed:
LOOP_DEMO_DRY_RUN=1 ./scripts/demo/1_chat.sh
```

## Prerequisites

- `uv` (Python 3.14 toolchain) on `PATH`.
- A live tree with `examples/support_agent/run_local.py` (G7).
- For non-dry-run executions: either `OPENAI_API_KEY` or
  `ANTHROPIC_API_KEY` exported in the environment. The runner will
  pick whichever it finds first; set `LOOP_SUPPORT_PROVIDER` to force
  one when both are present.

## The demos

| # | Script | Tests | Source agent |
| --- | --- | --- | --- |
| 1 | `1_chat.sh` | Streaming chat without tools | G7 |
| 2 | `2_tool.sh` | Tool calling (`lookup_order`) | G7 |
| 3 | `3_kb.sh` | Knowledge-base grounding (currently dry-run; KB lands in S916) | G7 + KB fixture |
| 4 | `4_multiagent.sh` | Supervisor → specialist hand-off | G7 (twice) |
| 5 | `5_hitl.sh` | Human-in-the-loop takeover (currently dry-run; takeover lands in S917) | G7 + operator |

## Expected output

Each demo has a recorded "expected" transcript at
`scripts/demo/expected/<n>_<name>.txt`. The dry-run mode prints these
verbatim; the live mode produces output that is structurally
equivalent but with model-dependent wording. The
`tests/test_demo_scripts.py` harness asserts dry-run output matches
the expected transcripts exactly so we can detect drift before a
recording.

## Adding a new demo

1. Create `scripts/demo/N_<name>.sh`, sourcing `_lib.sh` for the
   helpers.
2. Write a recorded transcript at
   `scripts/demo/expected/N_<name>.txt` — the dry-run helper streams
   it to stdout when `LOOP_DEMO_DRY_RUN=1`.
3. Extend `tests/test_demo_scripts.py` with the new entry.
4. Bump the table in this README.

## Story trail

- **S907** — G7 support agent + run_local.py.
- **S914** — *(this story)* the five scripted demos and their
  recorded transcripts.
- **S916** — live KB binding for demo 3.
- **S917** — HITL takeover handshake for demo 5.
