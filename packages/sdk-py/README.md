# loop (SDK)

Public Python SDK for Loop. Distributed as `pip install loop`.

Surface (Sprint 0):

- `loop.types` — `AgentEvent`, `AgentResponse`, `TurnEvent`, content parts.
- `loop.agents.Agent` — base class for user-authored agents.

Stable API surface lands gradually through Sprint 0 stories. Breaking
changes prior to GA must use the `feat(sdk)!:` Conventional Commit prefix.

Owner: Founding Eng #1 (Runtime) + DevRel. Companion spec:
`loop_implementation/api/openapi.yaml` and the SDK section of
`loop_implementation/architecture/ARCHITECTURE.md`.
