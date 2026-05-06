# North-star scenarios

The eight canonical end-to-end stories from §36 of the UX standard. Each
scenario links to the relevant Studio surfaces and produces verifiable proof
artifacts that the run actually happened.

| ID | Anchor | Title |
|---|---|---|
| `maya-migrates-botpress` | §36.1 | Maya migrates from Botpress in an afternoon |
| `diego-ships-voice` | §36.2 | Diego ships a voice phone agent in 25 minutes |
| `priya-wrong-tool` | §36.3 | Priya investigates the wrong tool |
| `acme-four-eyes` | §36.4 | Acme rolls out with four-eyes review |
| `operator-escalation` | §36.5 | Operator handles a real-time escalation |
| `support-kb-gap` | §36.6 | Support lead finds a KB gap |
| `sam-replay-tomorrow` | §36.7 | Sam replays tomorrow before shipping |
| `nadia-xray-cleanup` | §36.8 | Nadia uses X-Ray to remove dead context |

## Where the harness lives

* Studio demo route: `/scenarios` (apps/studio/src/app/scenarios/page.tsx)
* Source of truth: [apps/studio/src/lib/north-star-scenarios.ts](../../apps/studio/src/lib/north-star-scenarios.ts)
* Playwright spec: [apps/studio/e2e/north-star-scenarios.spec.ts](../../apps/studio/e2e/north-star-scenarios.spec.ts)
* CLI demo printer: [scripts/demo/ux/run.sh](../../scripts/demo/ux/run.sh)
* Per-scenario detail: see the markdown files in this folder.

## Acceptance criteria

The harness must, for every scenario, surface:

1. The canonical §36 anchor.
2. The premise and what the scenario validates.
3. The ordered, action-oriented steps.
4. The Studio routes the user crosses.
5. The hard proofs the run produces.

`findScenarioCoverageGaps()` is exported from the scenario library so
integration tests can assert that every route is reachable from the
canonical IA.
