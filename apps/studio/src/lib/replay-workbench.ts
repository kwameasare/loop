import {
  searchTraces,
  type TraceSummary,
  type TracesClientOptions,
} from "@/lib/traces";
import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type ReplayRisk = "low" | "medium" | "high";

export interface ProductionConversationCandidate {
  id: string;
  title: string;
  agentName: string;
  agentId: string;
  channelBindingId: string | undefined;
  sourceVersion: string;
  draftVersion: string;
  snapshotId: string;
  traceId: string;
  turns: number;
  risk: ReplayRisk;
  issue: string;
}

export interface FutureReplayDiff {
  id: string;
  frame: string;
  baseline: string;
  draft: string;
  status: "same" | "changed" | "improved" | "regressed";
  evidenceRef: string;
}

export interface FutureReplaySummary {
  conversationId: string;
  behavioralDistance: number;
  changedFrames: number;
  latencyDeltaMs: number;
  costDeltaPct: number;
  mostLikelyBreak: string;
  diffRows: readonly FutureReplayDiff[];
}

export interface PersonaSimulationResult {
  id: string;
  persona: string;
  lens: string;
  scenarios: number;
  passRate: number;
  failedScenarios: number;
  candidateEvalId: string;
  insight: string;
}

export interface ConversationPropertyResult {
  id: string;
  axis: string;
  samples: number;
  robustness: number;
  failures: number;
  representativeFailure: string;
  nextAction: string;
}

export interface ReplayFailureCluster {
  id: string;
  label: string;
  count: number;
  severity: ReplayRisk;
  nextAction: string;
  evidenceRef: string;
}

export interface CanonicalScene {
  id: string;
  name: string;
  source: "production" | "synthetic" | "migration";
  turns: number;
  evalLinked: boolean;
  summary: string;
  provenance: string;
  linkedTraceId: string;
}

export interface WorkspaceScene {
  id: string;
  name: string;
  category: string;
  trace_ids: string[];
  expected_behavior: string;
  created_by: string;
  created_at: string;
}

export interface ReplayWorkbenchModel {
  conversations: readonly ProductionConversationCandidate[];
  selectedReplay: FutureReplaySummary;
  personas: readonly PersonaSimulationResult[];
  properties: readonly ConversationPropertyResult[];
  clusters: readonly ReplayFailureCluster[];
  scenes: readonly CanonicalScene[];
  degradedReason?: string | undefined;
}

export interface ReplayForkResult {
  ok: true;
  branch: {
    id: string;
    name: string;
    base_version_id: string;
    status: string;
  };
  change_set: {
    id: string;
    name: string;
    source_type: string;
    source_refs: string[];
    status: string;
  };
  evidence_refs: string[];
  next_url: string;
}

export interface ReplayEvalCaseResult {
  ok: true;
  suite_id: string;
  case_id: string;
  case: {
    id: string;
    name: string;
    source: string;
    source_ref: string;
  };
  evidence_refs: string[];
  next_url: string;
}

function riskForTrace(trace: TraceSummary): ReplayRisk {
  if (trace.status === "error") return "high";
  if (trace.duration_ns > 1_200_000_000 || trace.span_count >= 8)
    return "medium";
  return "low";
}

function liveConversation(
  trace: TraceSummary,
  index: number,
): ProductionConversationCandidate {
  const risk = riskForTrace(trace);
  return {
    id: trace.id,
    title: trace.root_name || `Production turn ${index + 1}`,
    agentName: trace.agent_name,
    agentId: trace.agent_id,
    channelBindingId: trace.channel_binding_id,
    sourceVersion: "production",
    draftVersion: "active draft",
    snapshotId: `snap-${trace.id.slice(0, 8)}`,
    traceId: trace.id,
    turns: Math.max(1, trace.span_count),
    risk,
    issue:
      risk === "high"
        ? "Error trace should be replayed before promotion."
        : risk === "medium"
          ? "Long or tool-heavy trace is likely to change under a draft."
          : "Representative production trace ready for replay coverage.",
  };
}

function replaySummaryForTrace(trace: TraceSummary): FutureReplaySummary {
  const changedFrames =
    trace.status === "error" ? Math.max(1, Math.ceil(trace.span_count / 2)) : 1;
  const behavioralDistance =
    trace.status === "error" ? 61 : Math.min(44, 12 + trace.span_count * 3);
  return {
    conversationId: trace.id,
    behavioralDistance,
    changedFrames,
    latencyDeltaMs: -Math.round(trace.duration_ns / 8_000_000),
    costDeltaPct: trace.status === "error" ? 9 : -4,
    mostLikelyBreak:
      trace.status === "error"
        ? "The recorded production turn failed; replay the same input against the draft and require an explicit regression decision."
        : "The draft may alter tool ordering or retrieval evidence for this production turn.",
    diffRows: [
      {
        id: `${trace.id}-frame-1`,
        frame: "turn / recorded input",
        baseline: `${trace.root_name} on ${trace.agent_name}`,
        draft:
          "Draft receives the same production input with current behavior state.",
        status: "same",
        evidenceRef: `${trace.id}/input`,
      },
      {
        id: `${trace.id}-frame-2`,
        frame: "turn / spans",
        baseline: `${trace.span_count} recorded spans, ${trace.status} status.`,
        draft:
          trace.status === "error"
            ? "Draft must remove the recorded failure before promotion."
            : "Draft span plan is expected to stay within the same behavior envelope.",
        status: trace.status === "error" ? "regressed" : "changed",
        evidenceRef: `${trace.id}/spans`,
      },
      {
        id: `${trace.id}-frame-3`,
        frame: "turn / latency budget",
        baseline: `${Math.round(trace.duration_ns / 1_000_000)} ms production latency.`,
        draft: "Replay records the new latency and cost deltas before deploy.",
        status: "improved",
        evidenceRef: `${trace.id}/latency`,
      },
    ],
  };
}

function modelFromTraces(
  traces: readonly TraceSummary[],
  degradedReason?: string,
): ReplayWorkbenchModel {
  const emptySelectedReplay: FutureReplaySummary = {
    conversationId: "no_trace_loaded",
    behavioralDistance: 0,
    changedFrames: 0,
    latencyDeltaMs: 0,
    costDeltaPct: 0,
    mostLikelyBreak: "No production traces loaded.",
    diffRows: [],
  };
  if (traces.length === 0) {
    return {
      conversations: [],
      selectedReplay: emptySelectedReplay,
      personas: [],
      properties: [],
      clusters: [],
      scenes: [],
      degradedReason,
    };
  }
  const ordered = [...traces].sort((a, b) => {
    const riskOrder: Record<ReplayRisk, number> = {
      high: 0,
      medium: 1,
      low: 2,
    };
    return riskOrder[riskForTrace(a)] - riskOrder[riskForTrace(b)];
  });
  const [first] = ordered;
  return {
    conversations: ordered.map(liveConversation),
    selectedReplay: replaySummaryForTrace(first!),
    personas: [],
    properties: [],
    clusters: [],
    scenes: [],
    degradedReason,
  };
}

export async function fetchReplayWorkbenchModel(
  workspaceId: string,
  opts: TracesClientOptions = {},
): Promise<ReplayWorkbenchModel> {
  try {
    const result = await searchTraces(workspaceId, { page_size: 25 }, opts);
    return modelFromTraces(result.traces);
  } catch (err) {
    if (
      err instanceof Error &&
      /LOOP_CP_API_BASE_URL is required/.test(err.message)
    ) {
      return modelFromTraces([], err.message);
    }
    throw err;
  }
}

export async function replayAgainstDraft(
  agentId: string,
  args: {
    traceIds: readonly string[];
    draftBranchRef: string;
    compareVersionRef?: string;
  },
  opts: UxWireupClientOptions = {},
): Promise<{ items: readonly FutureReplaySummary[] }> {
  const body = await cpJson<{
    items?: Array<{
      trace_id: string;
      behavioral_distance: number;
      latency_delta_ms: number;
      cost_delta_pct: number;
      status: FutureReplayDiff["status"];
      token_aligned_rows: Array<{
        frame: string;
        baseline: string;
        draft: string;
        status: FutureReplayDiff["status"];
      }>;
    }>;
  }>(`/agents/${encodeURIComponent(agentId)}/replay/against-draft`, {
    ...opts,
    method: "POST",
    body: {
      trace_ids: args.traceIds,
      draft_branch_ref: args.draftBranchRef,
      compare_version_ref: args.compareVersionRef,
    },
    allowFallback: false,
    fallback: { items: [] },
  });
  if (!body.items?.length) return { items: [] };
  return {
    items: body.items.map((item) => ({
      conversationId: item.trace_id,
      behavioralDistance: item.behavioral_distance,
      changedFrames: item.token_aligned_rows.filter(
        (row) => row.status !== "same",
      ).length,
      latencyDeltaMs: item.latency_delta_ms,
      costDeltaPct: item.cost_delta_pct,
      mostLikelyBreak:
        item.status === "regressed"
          ? "Replay found a likely behavioral regression before promotion."
          : "Replay produced a draft diff ready for review.",
      diffRows: item.token_aligned_rows.map((row, index) => ({
        id: `${item.trace_id}-${index}`,
        frame: row.frame,
        baseline: row.baseline,
        draft: row.draft,
        status: row.status,
        evidenceRef: `${item.trace_id}/against-draft/${index}`,
      })),
    })),
  };
}

export async function forkReplayFrame(
  agentId: string,
  args: {
    traceId: string;
    frameId: string;
    sourceVersionRef: string;
    snapshotId?: string;
    evidenceRef: string;
    purpose: string;
  },
  opts: UxWireupClientOptions = {},
): Promise<ReplayForkResult> {
  return cpJson<ReplayForkResult>(
    `/agents/${encodeURIComponent(agentId)}/replay/forks`,
    {
      ...opts,
      method: "POST",
      body: {
        trace_id: args.traceId,
        frame_id: args.frameId,
        source_version_ref: args.sourceVersionRef,
        snapshot_id: args.snapshotId,
        evidence_ref: args.evidenceRef,
        purpose: args.purpose,
      },
      allowFallback: false,
      fallback: {
        ok: true,
        branch: {
          id: "",
          name: "",
          base_version_id: args.sourceVersionRef,
          status: "active",
        },
        change_set: {
          id: "",
          name: "",
          source_type: "trace_replay_frame",
          source_refs: [],
          status: "draft",
        },
        evidence_refs: [],
        next_url: "",
      },
    },
  );
}

export async function saveReplayAsEvalCase(
  agentId: string,
  args: {
    title: string;
    traceId: string;
    frameId: string;
    sourceVersionRef: string;
    draftBranchRef: string;
    channel: string;
    snapshotId?: string;
    expectedBehavior: string;
    failureReason: string;
    replayRef: string;
    riskTags: readonly string[];
  },
  opts: UxWireupClientOptions = {},
): Promise<ReplayEvalCaseResult> {
  return cpJson<ReplayEvalCaseResult>(
    `/agents/${encodeURIComponent(agentId)}/replay/eval-cases`,
    {
      ...opts,
      method: "POST",
      body: {
        title: args.title,
        trace_id: args.traceId,
        frame_id: args.frameId,
        source_version_ref: args.sourceVersionRef,
        draft_branch_ref: args.draftBranchRef,
        channel: args.channel,
        snapshot_id: args.snapshotId,
        expected_behavior: args.expectedBehavior,
        failure_reason: args.failureReason,
        replay_ref: args.replayRef,
        risk_tags: args.riskTags,
      },
      allowFallback: false,
      fallback: {
        ok: true,
        suite_id: "",
        case_id: "",
        case: {
          id: "",
          name: args.title,
          source: "production-replay",
          source_ref: args.traceId,
        },
        evidence_refs: [],
        next_url: "",
      },
    },
  );
}

export async function createReplayScene(
  workspaceId: string,
  args: {
    name: string;
    category: string;
    traceIds: readonly string[];
    expectedBehavior: string;
  },
  opts: UxWireupClientOptions = {},
): Promise<WorkspaceScene> {
  return cpJson<WorkspaceScene>(
    `/workspaces/${encodeURIComponent(workspaceId)}/scenes`,
    {
      ...opts,
      method: "POST",
      body: {
        name: args.name,
        category: args.category,
        trace_ids: args.traceIds,
        expected_behavior: args.expectedBehavior,
      },
      allowFallback: false,
      fallback: {
        id: "",
        name: args.name,
        category: args.category,
        trace_ids: [...args.traceIds],
        expected_behavior: args.expectedBehavior,
        created_by: "",
        created_at: "",
      },
    },
  );
}
