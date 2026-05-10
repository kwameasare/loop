/**
 * Acceptance journeys from `PROPOSED_AGENT_FLOW_MERGED.md`.
 *
 * These are implementation pressure tests, not marketing demos. They make the
 * merged agent lifecycle spec machine-readable so Studio can verify that the
 * support-agent lifecycle, Botpress migration, incident repair, high-risk tool,
 * and voice-as-a-channel journeys remain routed through real product surfaces.
 */

export const AGENT_FLOW_JOURNEY_IDS = [
  "flow-a-create-billing-support-agent",
  "flow-b-migrate-from-botpress",
  "flow-c-fix-production-issue",
  "flow-d-add-high-risk-tool",
  "flow-e-add-voice-after-web-whatsapp",
] as const;

export type AgentFlowJourneyId = (typeof AGENT_FLOW_JOURNEY_IDS)[number];

export interface AgentFlowJourney {
  id: AgentFlowJourneyId;
  anchor: string;
  title: string;
  purpose: string;
  result: string;
  steps: string[];
  routes: string[];
  proofs: string[];
  acceptance: string[];
}

export const AGENT_FLOW_JOURNEYS: Record<
  AgentFlowJourneyId,
  AgentFlowJourney
> = {
  "flow-a-create-billing-support-agent": {
    id: "flow-a-create-billing-support-agent",
    anchor: "Flow A",
    title: "Create a new billing support agent",
    purpose:
      "Proves a builder can move from intent to a governed, testable draft without starting from a blank bot.",
    result:
      "Draft agent created, not production-ready, with next steps and evidence already attached.",
    steps: [
      "Create or import an agent from the estate home.",
      "Enter the billing-support mission and generate an Agent Contract.",
      "Select capabilities and connect billing documents plus a mock invoice API.",
      "Generate starter evals and run multi-channel simulations.",
      "Add a web sandbox channel and invite the Billing Owner to review refund policy.",
    ],
    routes: [
      "/",
      "/agents",
      "/agents/[agent_id]/contract",
      "/agents/[agent_id]/tools",
      "/agents/[agent_id]/kb",
      "/agents/[agent_id]/evals",
      "/agents/[agent_id]/simulator",
      "/agents/[agent_id]/channels",
      "/collaborate/review",
    ],
    proofs: [
      "agent.id",
      "commitment_document.id",
      "tool_contract.id",
      "eval.suite_id",
      "channel_binding.id",
      "review.request_id",
    ],
    acceptance: [
      "Business intent creates an Agent and Commitment Document.",
      "Uploaded artifacts create analysis jobs and visible progress.",
      "Missing owner or worst-case failure asks for clarification.",
      "Draft generation failure supports retry or manual continuation.",
    ],
  },
  "flow-b-migrate-from-botpress": {
    id: "flow-b-migrate-from-botpress",
    anchor: "Flow B",
    title: "Migrate from Botpress",
    purpose:
      "Proves legacy flow complexity becomes Loop capabilities, policies, tools, knowledge, channels, evals, parity, and lineage.",
    result:
      "Botpress behavior is imported, mapped, replayed for parity, staged, and preserved as lineage.",
    steps: [
      "Upload a Botpress `.bpz` export.",
      "Inventory intents, workflows, knowledge, tables, hooks, variables, integrations, and channels.",
      "Map workflows to capabilities and policies while flagging hooks and missing credentials.",
      "Generate parity tests from intents and transcripts.",
      "Resolve migration gaps, create a migration branch, run parity, and stage a candidate.",
    ],
    routes: [
      "/migrate",
      "/migrate/parity",
      "/agents/[agent_id]/workflow",
      "/agents/[agent_id]/deploys",
      "/enterprise/audit",
    ],
    proofs: [
      "migration.run_id",
      "migration.inventory_id",
      "parity.report_id",
      "migration.branch_id",
      "lineage.evidence_ref",
    ],
    acceptance: [
      "Botpress export maps intents, variables, tools, and fallback behavior.",
      "Unmapped items are listed with severity.",
      "Historical conversations replay old and new behavior for parity.",
      "Cutover records lineage and rollback evidence.",
    ],
  },
  "flow-c-fix-production-issue": {
    id: "flow-c-fix-production-issue",
    anchor: "Flow C",
    title: "Fix a production issue",
    purpose:
      "Proves production improvement is trace-linked, tested, approved, deployed, observable, reversible, and auditable.",
    result:
      "Escalation-rate regression is traced to a behavior rule, repaired, approved, canaried, observed, and rolled forward.",
    steps: [
      "Estate home shows escalation rate up after the latest version.",
      "Open the trace cluster and inspect the suggested root cause.",
      "Create a Change Set from affected traces and edit the escalation policy.",
      "Save generated evals, run regression, and collect compliance approval.",
      "Start canary for web chat, confirm metrics recover, and roll forward.",
    ],
    routes: [
      "/",
      "/observe",
      "/traces",
      "/agents/[agent_id]/behavior",
      "/agents/[agent_id]/evals",
      "/deploy/safety",
      "/collaborate/review",
      "/agents/[agent_id]/deploys",
      "/agents/[agent_id]/observe",
      "/enterprise/audit",
    ],
    proofs: [
      "trace.cluster_id",
      "change_package.id",
      "eval.case_id",
      "approval.content_hash",
      "deploy.canary_id",
      "audit.event_id",
    ],
    acceptance: [
      "A bad production trace can become a focused behavior repair.",
      "The repair creates or updates eval coverage before deploy.",
      "Compliance approval is required when escalation policy changes.",
      "Canary recovery and rollout completion are audit-linked.",
    ],
  },
  "flow-d-add-high-risk-tool": {
    id: "flow-d-add-high-risk-tool",
    anchor: "Flow D",
    title: "Add a high-risk tool",
    purpose:
      "Proves powerful capabilities can be added without hiding financial, permission, or audit risk.",
    result:
      "Refund tool enters sandbox with caps, approval thresholds, human confirmation, evals, and staged-only enablement.",
    steps: [
      "Paste or import the `Issue refund` API into Tools Room.",
      "Studio classifies the tool as high risk and requires side-effect metadata.",
      "Configure sandbox test, approval threshold, audit logging, caps, and human confirmation.",
      "Generate tool-use evals and request compliance review of the permission diff.",
      "Deploy only to staging; production enablement requires a separate approval.",
    ],
    routes: [
      "/agents/[agent_id]/tools",
      "/agents/[agent_id]/secrets",
      "/agents/[agent_id]/evals",
      "/agents/[agent_id]/workflow",
      "/collaborate/review",
      "/agents/[agent_id]/deploys",
      "/enterprise/audit",
    ],
    proofs: [
      "tool_contract.id",
      "tool_risk.classification",
      "secret_ref.id",
      "eval.tool_suite_id",
      "approval.content_hash",
      "staging.deploy_id",
    ],
    acceptance: [
      "A cURL command drafts a typed tool.",
      "Mutating tools require side-effect classification.",
      "Money-moving tools require caps and approvals.",
      "Live tool contract changes require review before production.",
    ],
  },
  "flow-e-add-voice-after-web-whatsapp": {
    id: "flow-e-add-voice-after-web-whatsapp",
    anchor: "Flow E",
    title: "Add voice after web and WhatsApp",
    purpose:
      "Proves voice is a first-class channel adapter, not a separate bot or roadmap distortion.",
    result:
      "Existing behavior is previewed as spoken turns, voice-specific risks are fixed, voice evals pass, and staging deploy begins.",
    steps: [
      "Open Channels and add a voice binding alongside web and WhatsApp.",
      "Configure ASR, TTS, recording disclosure, escalation number, and latency budget.",
      "Preview existing behavior as spoken turns with queued-speech evidence.",
      "Fix answers that are too long for voice and add presentation rules.",
      "Run voice evals and deploy voice to staging.",
    ],
    routes: [
      "/channels",
      "/agents/[agent_id]/channels",
      "/voice",
      "/voice/config",
      "/agents/[agent_id]/simulator",
      "/agents/[agent_id]/evals",
      "/agents/[agent_id]/deploys",
    ],
    proofs: [
      "channel_binding.voice.id",
      "voice.config_id",
      "voice.preview.trace_id",
      "voice.eval.run_id",
      "staging.deploy_id",
    ],
    acceptance: [
      "Channels lists every supported channel type.",
      "No voice setup blocks neither web nor WhatsApp.",
      "Incomplete WhatsApp blocks WhatsApp production scope only.",
      "Live channel traces include channel binding ID.",
    ],
  },
};

export interface AgentFlowJourneyRouteGap {
  journeyId: AgentFlowJourneyId;
  missingRoutes: string[];
}

export function findAgentFlowJourneyRouteGaps(
  knownRoutes: ReadonlySet<string>,
): AgentFlowJourneyRouteGap[] {
  return AGENT_FLOW_JOURNEY_IDS.flatMap((id) => {
    const missingRoutes = AGENT_FLOW_JOURNEYS[id].routes.filter(
      (route) => !knownRoutes.has(route),
    );
    return missingRoutes.length > 0 ? [{ journeyId: id, missingRoutes }] : [];
  });
}
