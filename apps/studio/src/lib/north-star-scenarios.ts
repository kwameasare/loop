/**
 * UX408 — North-star scenario harness.
 *
 * The eight canonical scenarios from §36 of the UX standard, expressed as a
 * deterministic, machine-readable list. Powers:
 *   • `/scenarios` demo route used by sales engineering and onboarding
 *   • `e2e/north-star-scenarios.spec.ts` Playwright harness
 *   • `scripts/demo/ux/run.sh` CLI demo printer
 *   • `docs/ux-scenarios/*.md` reference docs
 */

export const NORTH_STAR_SCENARIO_IDS = [
  "maya-migrates-botpress",
  "diego-ships-voice",
  "priya-wrong-tool",
  "acme-four-eyes",
  "operator-escalation",
  "support-kb-gap",
  "sam-replay-tomorrow",
  "nadia-xray-cleanup",
] as const;
export type NorthStarScenarioId = (typeof NORTH_STAR_SCENARIO_IDS)[number];

export interface NorthStarScenario {
  id: NorthStarScenarioId;
  /** Section anchor inside the canonical UX standard. */
  anchor: string;
  /** Short headline used in card titles and Playwright assertions. */
  title: string;
  /** Single-line problem statement. */
  premise: string;
  /** What this scenario validates end-to-end. */
  validates: string;
  /** Ordered, action-oriented steps. Each one references a Studio surface. */
  steps: string[];
  /** Routes the user crosses during the scenario. */
  routes: string[];
  /** Hard proofs the run should produce. */
  proofs: string[];
}

export const NORTH_STAR_SCENARIOS: Record<NorthStarScenarioId, NorthStarScenario> = {
  "maya-migrates-botpress": {
    id: "maya-migrates-botpress",
    anchor: "§36.1",
    title: "Maya migrates from Botpress in an afternoon",
    premise: "Migrate an existing Botpress workspace with parity and rollback ready.",
    validates: "Migration import, parity, source lineage, cutover, deploy safety.",
    steps: [
      "Open the migration wizard and import the Botpress workspace.",
      "Review intent / flow / KB mappings and reconnect secrets.",
      "Run parity against 200 production conversations.",
      "Fix four divergences identified by the parity report.",
      "Stage Loop and shadow traffic for one hour.",
      "Canary to 10%, watch the deploy-watch board, then promote to 100%.",
    ],
    routes: ["/migrations", "/parity", "/deploys"],
    proofs: ["migration.cutover.id", "parity.report_id", "deploy.production.changeset_id"],
  },
  "diego-ships-voice": {
    id: "diego-ships-voice",
    anchor: "§36.2",
    title: "Diego ships a voice phone agent in 25 minutes",
    premise: "Voice receptionist live on a real phone number with eval coverage.",
    validates: "Voice as a channel, not a separate product.",
    steps: [
      "Pick the voice receptionist template from the gallery.",
      "Connect a phone number and run voice preview with ASR / TTS spans visible.",
      "Run the voice eval suite (latency + grounded-answer + barge-in).",
      "Deploy to staging, canary 10% of inbound calls, then promote.",
    ],
    routes: ["/templates", "/agents", "/voice", "/evals", "/deploys"],
    proofs: ["voice.eval.run_id", "deploy.staging.changeset_id"],
  },
  "priya-wrong-tool": {
    id: "priya-wrong-tool",
    anchor: "§36.3",
    title: "Priya investigates the wrong tool",
    premise: "A failed production turn invoked the wrong tool. Fix it without regressing.",
    validates: "Trace → fork → fix → eval.",
    steps: [
      "Open the failed production turn from the inbox.",
      "Inspect the tool span and read the policy mismatch.",
      "Fork the turn into a draft branch.",
      "Update the tool selection behaviour.",
      "Save the original turn as a new eval case.",
      "Run the regression suite and confirm pass.",
    ],
    routes: ["/inbox", "/traces", "/forks", "/evals"],
    proofs: ["fork.eval.run_id", "eval.run_id"],
  },
  "acme-four-eyes": {
    id: "acme-four-eyes",
    anchor: "§36.4",
    title: "Acme rolls out with four-eyes review",
    premise: "Bank platform team updates a loan FAQ agent under enterprise governance.",
    validates: "Required approvers, audit evidence, eval/cost/latency delta gates.",
    steps: [
      "Open preflight for the loan FAQ changeset.",
      "Review graph diff, code diff, eval delta, cost delta, latency delta.",
      "Two reviewers approve via the changeset review surface.",
      "Canary the changeset and observe deploy-watch.",
      "Export audit evidence (approvals + diffs + parity).",
    ],
    routes: ["/changesets", "/deploys", "/audit"],
    proofs: ["changeset.approvals", "audit.export_id", "deploy.canary.percent"],
  },
  "operator-escalation": {
    id: "operator-escalation",
    anchor: "§36.5",
    title: "Operator handles a real-time escalation",
    premise: "Operator takes over a voice call, resolves the issue, saves the lesson.",
    validates: "HITL as production learning.",
    steps: [
      "Take over the live voice escalation from the inbox.",
      "Read the conversation trace and memory inspector side-by-side.",
      "Resolve the customer issue and end the call.",
      "Save the resolution as an eval case under the right suite.",
      "Release the conversation back to the agent.",
    ],
    routes: ["/inbox", "/traces", "/evals"],
    proofs: ["operator.handoff.id", "eval.run_id"],
  },
  "support-kb-gap": {
    id: "support-kb-gap",
    anchor: "§36.6",
    title: "Support lead finds a KB gap",
    premise: "Zero-result retrievals point to a missing knowledge source.",
    validates: "Knowledge as a measurable system.",
    steps: [
      "Open the knowledge dashboard and sort by zero-result retrieval count.",
      "Open the Knowledge Atelier and review missed candidates.",
      "Add a new source and reindex.",
      "Run retrieval evals against the new corpus.",
      "Watch grounded-answer quality climb on the dashboard.",
    ],
    routes: ["/knowledge", "/knowledge/atelier", "/evals"],
    proofs: ["kb.source_id", "eval.retrieval.run_id"],
  },
  "sam-replay-tomorrow": {
    id: "sam-replay-tomorrow",
    anchor: "§36.7",
    title: "Sam replays tomorrow before shipping",
    premise: "Edit a refund behaviour and replay the production conversations most likely to change.",
    validates: "Production replay, What Could Break, behaviour review, deploy confidence.",
    steps: [
      "Edit the refund behaviour section in the agent draft.",
      "Open Preflight and read the five production conversations most likely to diverge.",
      "Replay them against the draft and find one Spanish refund regression.",
      "Ask Second Pair Of Eyes to review the regression.",
      "Add a missing eval case and rerun the suite.",
      "Promote only after the replay diff clears.",
    ],
    routes: ["/agents", "/preflight", "/evals", "/deploys"],
    proofs: ["preflight.report_id", "eval.run_id", "deploy.production.changeset_id"],
  },
  "nadia-xray-cleanup": {
    id: "nadia-xray-cleanup",
    anchor: "§36.8",
    title: "Nadia uses X-Ray to remove dead context",
    premise: "Five prompt sections are never invoked; one rare branch drives most cost.",
    validates: "Observed behaviour, sentence telemetry, cost control, evidence-backed simplification.",
    steps: [
      "Open Agent X-Ray and sort prompt sections by observed invocations.",
      "Open representative traces for the rare branch.",
      "Trim dead context from the prompt.",
      "Add a targeted eval for the rare branch.",
      "Confirm faster latency without losing quality on the budget visualizer.",
    ],
    routes: ["/xray", "/traces", "/evals", "/cost"],
    proofs: ["xray.report_id", "eval.run_id", "cost.dashboard_id"],
  },
};

export interface ScenarioCoverageGap {
  id: NorthStarScenarioId;
  missingRoutes: string[];
}

/**
 * Returns the scenarios whose canonical routes are not covered by the provided
 * known-route allowlist. Used by Playwright to assert that Studio reaches
 * every scenario from the canonical IA.
 */
export function findScenarioCoverageGaps(
  knownRoutes: ReadonlySet<string>,
): ScenarioCoverageGap[] {
  const gaps: ScenarioCoverageGap[] = [];
  for (const id of NORTH_STAR_SCENARIO_IDS) {
    const scenario = NORTH_STAR_SCENARIOS[id];
    const missing = scenario.routes.filter((route) => !knownRoutes.has(route));
    if (missing.length > 0) gaps.push({ id, missingRoutes: missing });
  }
  return gaps;
}
