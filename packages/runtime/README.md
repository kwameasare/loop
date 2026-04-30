# loop-runtime

Internal runtime hot-path for Loop. Owns:

- `TurnExecutor` — the reasoning loop that executes one inbound turn.
- LLM streaming + tool dispatch + budget enforcement.
- Idempotency and observability hooks.

Owner: Founding Eng #1 (Runtime). Companion spec:
`loop_implementation/architecture/ARCHITECTURE.md` §3.

> Sprint 0: only `loop/runtime/turn_executor.py` is present. Supporting
> modules (`loop.runtime.context`, `loop.gateway`, `loop.tools`,
> `loop.memory`, `loop.prompt_builder`, `loop.trace`, `loop.clock`) land
> in stories S007/S008/S011/S013.
