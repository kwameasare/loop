import type {
  ConfidenceLevel,
  ObjectState,
  TrustState,
} from "@/lib/design-tokens";

import { targetUxFixtures } from "./fixtures";
import type { TargetUXFixture } from "./types";

export type BuildFlowOrigin = "agent" | "behavior";
export type BuildFlowActionId = "preview" | "fork" | "save-eval";

export interface BuildFlowAction {
  id: BuildFlowActionId;
  label: string;
  description: string;
  evidence: string;
  result: string;
}

export interface BuildFlowDiff {
  label: string;
  before: string;
  after: string;
  impact: string;
}

export interface BuildFlowData {
  agentId: string;
  agentName: string;
  origin: BuildFlowOrigin;
  branch: string;
  ephemeralBranch: string;
  objectState: ObjectState;
  trust: TrustState;
  sourceTraceId: string;
  sourceTurn: string;
  sourceSnapshot: string;
  memorySnapshot: string;
  evalSuiteId: string;
  evalCaseId: string;
  productionGuard: string;
  blockedProductionReason: string;
  previewEvidence: string;
  forkEvidence: string;
  saveEvalEvidence: string;
  confidence: ConfidenceLevel;
  diff: BuildFlowDiff;
  diffs: string[];
  actions: BuildFlowAction[];
  degradedReason?: string | undefined;
}

export function createBuildToTestFlowData(
  agentId: string,
  origin: BuildFlowOrigin,
  fixture: TargetUXFixture = targetUxFixtures,
): BuildFlowData {
  const agent =
    fixture.agents.find((candidate) => candidate.id === agentId) ??
    fixture.agents[0]!;
  const workspace = fixture.workspace;
  const trace = fixture.traces[0]!;
  const evalSuite = fixture.evals[0]!;
  const snapshot = fixture.snapshots[0]!;
  const memory = fixture.memory[0]!;
  const cost = fixture.costs[0]!;
  const sourceTurn = "turn 3";
  const evalCaseId = `${evalSuite.id}_fork_${trace.id}_${sourceTurn.replace(
    /\s+/g,
    "_",
  )}`;
  const originLabel = origin === "behavior" ? "behavior edit" : "agent draft";

  return {
    agentId,
    agentName: agent.name,
    origin,
    branch: workspace.branch,
    ephemeralBranch: `fork/${trace.id}-${sourceTurn.replace(/\s+/g, "-")}`,
    objectState: workspace.objectState,
    trust: workspace.trust,
    sourceTraceId: trace.id,
    sourceTurn,
    sourceSnapshot: snapshot.id,
    memorySnapshot: `${memory.id}: ${memory.after}`,
    evalSuiteId: evalSuite.id,
    evalCaseId,
    productionGuard:
      "Preview, fork, and eval creation run against draft branch state only; production traffic continues on the deployed version.",
    blockedProductionReason:
      "Production mutation is locked. Save the preview as an eval or stage a deploy after gates pass.",
    previewEvidence: `${trace.id}; ${trace.spans.length} spans; ${snapshot.id}`,
    forkEvidence: `${snapshot.id}; conversation restored through ${sourceTurn}; memory ${memory.id}`,
    saveEvalEvidence: `${evalSuite.id}; scorer threshold ${evalSuite.passRate}%; trace ${trace.id}`,
    confidence: evalSuite.confidence,
    diff: {
      label:
        origin === "behavior"
          ? "Behavior preview vs production"
          : "Agent draft vs production",
      before:
        "Production can retrieve the archived refund policy before the May 2026 policy.",
      after:
        "Draft cites the May 2026 policy, uses order lookup, and keeps refund issue in approval.",
      impact:
        "The builder can test the next turn and save the regression case without changing production.",
    },
    diffs: [
      `Token diff: cancellation answer adds May 2026 policy citation from ${trace.id}.`,
      "Tool diff: lookup_order remains mock/read-only; issue_refund remains staged.",
      `Retrieval diff: ${snapshot.id} ranks refund_policy_2026 above the archive.`,
      `Memory diff: ${memory.key} stays read-only for the fork; no durable write on preview.`,
      `Cost diff: ${cost.label} stays within ${cost.recommendation}`,
      `Latency diff: ${trace.spans[1]?.label ?? "tool call"} stays under ${
        trace.spans[1]?.durationMs ?? 0
      } ms in replay evidence.`,
    ],
    actions: [
      {
        id: "preview",
        label: "Preview draft",
        description: `Run the next turn against this ${originLabel}.`,
        evidence: `${trace.id} replay command; draft branch ${workspace.branch}`,
        result:
          "Preview queued in dev with mock tools, memory snapshot, and branch-local state.",
      },
      {
        id: "fork",
        label: "Fork from turn",
        description:
          "Create an ephemeral branch from the selected trace turn and restore conversation state.",
        evidence: `${snapshot.id}; ${trace.id}; ${sourceTurn}`,
        result:
          "Fork branch created with exact agent, tool, KB, model, and memory state from the turn.",
      },
      {
        id: "save-eval",
        label: "Save run as eval",
        description:
          "Convert the preview run into an eval case with input, expected output, and diffs.",
        evidence: `${evalSuite.id}; ${evalCaseId}`,
        result:
          "Eval case staged with trace, tool, retrieval, memory, cost, and latency diffs.",
      },
    ],
  };
}

export function createProductionBlockedBuildFlowData(
  agentId = "agent_support",
  origin: BuildFlowOrigin = "behavior",
): BuildFlowData {
  const base = createBuildToTestFlowData(agentId, origin);
  return {
    ...base,
    objectState: "production",
    trust: "blocked",
    degradedReason:
      "The source object is production-protected. Forking and eval creation remain available, but direct mutation is locked.",
  };
}
