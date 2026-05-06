import type {
  ConfidenceLevel,
  ObjectState,
  TrustState,
} from "@/lib/design-tokens";
import { targetUxFixtures, type TargetUXFixture } from "@/lib/target-ux";

export type AgentMapNodeKind =
  | "trigger"
  | "routine"
  | "policy"
  | "tool"
  | "memory"
  | "eval"
  | "deploy"
  | "output";

export type AgentMapRisk = "none" | "low" | "medium" | "high" | "blocked";

export interface AgentMapNode {
  id: string;
  kind: AgentMapNodeKind;
  label: string;
  summary: string;
  x: number;
  y: number;
  objectState: ObjectState;
  trust: TrustState;
  risk: AgentMapRisk;
  coveragePercent: number;
  latencyMs: number;
  costUsd: number;
  dependencies: string[];
  toolIds: string[];
  memoryIds: string[];
  evalIds: string[];
  evidence: string[];
  codeRef: string;
  canEdit: boolean;
  readonlyReason?: string | undefined;
  hazardIds: string[];
}

export interface AgentMapEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  evidence: string;
  status: "ok" | "warning" | "blocked";
}

export interface AgentMapHazard {
  id: string;
  title: string;
  severity: AgentMapRisk;
  description: string;
  nodeIds: string[];
  evidence: string;
  requiredBehavior: string;
}

export interface AgentMapForkPoint {
  id: string;
  nodeId: string;
  label: string;
  branch: string;
  traceId: string;
  snapshotId: string;
  evidence: string;
  tokenDelta: string;
  latencyDelta: string;
  costDelta: string;
  evalDelta: string;
}

export interface AgentMapCoverage {
  dependency: number;
  tool: number;
  memory: number;
  eval: number;
}

export interface AgentMapData {
  agentId: string;
  agentName: string;
  branch: string;
  objectState: ObjectState;
  trust: TrustState;
  confidence: ConfidenceLevel;
  nodes: AgentMapNode[];
  edges: AgentMapEdge[];
  hazards: AgentMapHazard[];
  forkPoints: AgentMapForkPoint[];
  coverage: AgentMapCoverage;
  degradedReason?: string | undefined;
}

export interface AgentMapEditAttempt {
  source: string;
  target: string;
  label: string;
}

export interface AgentMapEditResult {
  accepted: boolean;
  reason: string;
  evidence: string;
}

export const INVALID_AGENT_MAP_EDIT: AgentMapEditAttempt = {
  source: "output-answer",
  target: "trigger-chat",
  label: "Route final answer back to chat trigger",
};

function hasPath(
  edges: readonly AgentMapEdge[],
  start: string,
  target: string,
  visited = new Set<string>(),
): boolean {
  if (start === target) return true;
  if (visited.has(start)) return false;
  visited.add(start);
  return edges
    .filter((edge) => edge.source === start)
    .some((edge) => hasPath(edges, edge.target, target, visited));
}

export function evaluateAgentMapEdit(
  data: AgentMapData,
  attempt: AgentMapEditAttempt,
): AgentMapEditResult {
  const source = data.nodes.find((node) => node.id === attempt.source);
  const target = data.nodes.find((node) => node.id === attempt.target);
  if (!source || !target) {
    return {
      accepted: false,
      reason:
        "Invalid edit rejected. One endpoint is missing from this agent state.",
      evidence: "map_edit_validation missing_endpoint",
    };
  }
  if (!source.canEdit || !target.canEdit) {
    return {
      accepted: false,
      reason:
        "Invalid edit rejected. Protected production objects require a preview branch.",
      evidence:
        source.readonlyReason ??
        target.readonlyReason ??
        "map_edit_validation protected_object",
    };
  }
  if (hasPath(data.edges, attempt.target, attempt.source)) {
    return {
      accepted: false,
      reason:
        "Invalid edit rejected. This attachment would create a circular dependency before preview can run.",
      evidence:
        "hazard_circular_dependency and map_edit_validation cycle_check",
    };
  }
  return {
    accepted: true,
    reason: "Edit accepted for preview.",
    evidence: "map_edit_validation acyclic_preview",
  };
}

export function createAgentMapData(
  agentId: string,
  fixture: TargetUXFixture = targetUxFixtures,
): AgentMapData {
  const agent =
    fixture.agents.find((candidate) => candidate.id === agentId) ??
    fixture.agents[0]!;
  const trace =
    fixture.traces.find((candidate) => candidate.agentId === agent.id) ??
    fixture.traces[0]!;
  const evalSuite = fixture.evals[0]!;
  const deploy =
    fixture.deploys.find((candidate) => candidate.agentId === agent.id) ??
    fixture.deploys[0]!;
  const readTool = fixture.tools[0]!;
  const mutatingTool = fixture.tools[1]!;
  const memory = fixture.memory[0]!;
  const enterpriseControl = fixture.enterprise[0]!;

  const nodes: AgentMapNode[] = [
    {
      id: "trigger-chat",
      kind: "trigger",
      label: "Chat and voice turns",
      summary:
        "Inbound channel events start the same agent state, not separate flow logic.",
      x: 12,
      y: 18,
      objectState: agent.objectState,
      trust: agent.trust,
      risk: "low",
      coveragePercent: 98,
      latencyMs: 32,
      costUsd: 0,
      dependencies: [],
      toolIds: [],
      memoryIds: [],
      evalIds: [evalSuite.id],
      evidence: [trace.id, "channel_web_voice_binding"],
      codeRef: "agent.channels.yaml#web_voice",
      canEdit: true,
      hazardIds: [],
    },
    {
      id: "intent-router",
      kind: "routine",
      label: "Intent router",
      summary:
        "Classifies order lookup, refund dispute, cancellation, and escalation turns.",
      x: 32,
      y: 18,
      objectState: "saved",
      trust: "watching",
      risk: "medium",
      coveragePercent: 91,
      latencyMs: 118,
      costUsd: 0.006,
      dependencies: ["trigger-chat"],
      toolIds: [],
      memoryIds: [],
      evalIds: [evalSuite.id],
      evidence: ["trace_refund_742 span_context", evalSuite.id],
      codeRef: "agent.behavior.yaml#intent_router",
      canEdit: true,
      hazardIds: [],
    },
    {
      id: "policy-refund",
      kind: "policy",
      label: "Refund policy guard",
      summary:
        "Requires current May 2026 policy evidence before quoting refund windows.",
      x: 52,
      y: 18,
      objectState: "saved",
      trust: "watching",
      risk: "high",
      coveragePercent: 88,
      latencyMs: 84,
      costUsd: 0.004,
      dependencies: ["intent-router"],
      toolIds: [],
      memoryIds: [],
      evalIds: [evalSuite.id],
      evidence: ["snap_refund_may", "eval_refunds refund_window_es_may"],
      codeRef: "agent.behavior.yaml#refund_policy_guard",
      canEdit: true,
      hazardIds: ["hazard_stale_approval"],
    },
    {
      id: "tool-lookup",
      kind: "tool",
      label: readTool.name,
      summary:
        "Read-only MCP grant checks order state before account-specific answers.",
      x: 32,
      y: 48,
      objectState: readTool.objectState,
      trust: "healthy",
      risk: readTool.risk,
      coveragePercent: 96,
      latencyMs: 243,
      costUsd: 0.012,
      dependencies: ["intent-router"],
      toolIds: [readTool.id],
      memoryIds: [],
      evalIds: [evalSuite.id],
      evidence: ["span_tool lookup_order", readTool.id],
      codeRef: "tools.yaml#lookup_order",
      canEdit: false,
      readonlyReason: "Production read-only tool grant opens in Tools Room.",
      hazardIds: [],
    },
    {
      id: "tool-refund",
      kind: "tool",
      label: mutatingTool.name,
      summary:
        "Money-moving tool remains staged until approval and replay pass.",
      x: 54,
      y: 48,
      objectState: mutatingTool.objectState,
      trust: "blocked",
      risk: "blocked",
      coveragePercent: 74,
      latencyMs: 310,
      costUsd: 0.021,
      dependencies: ["policy-refund", "tool-lookup"],
      toolIds: [mutatingTool.id],
      memoryIds: [],
      evalIds: [evalSuite.id],
      evidence: [mutatingTool.id, deploy.id],
      codeRef: "tools.yaml#issue_refund",
      canEdit: false,
      readonlyReason:
        "Mutating tool grants require preview, approval, and a safety contract.",
      hazardIds: ["hazard_tool_grant"],
    },
    {
      id: "memory-preference",
      kind: "memory",
      label: "Preference memory",
      summary: "Writes durable language preference and excludes payment data.",
      x: 74,
      y: 48,
      objectState: "saved",
      trust: "healthy",
      risk: memory.risk === "none" ? "low" : "high",
      coveragePercent: 93,
      latencyMs: 74,
      costUsd: 0.002,
      dependencies: ["policy-refund"],
      toolIds: [],
      memoryIds: [memory.id],
      evalIds: [evalSuite.id],
      evidence: [memory.id, enterpriseControl.id],
      codeRef: "memory.policy.yaml#durable_preferences",
      canEdit: true,
      hazardIds: [],
    },
    {
      id: "eval-coverage",
      kind: "eval",
      label: evalSuite.name,
      summary:
        "Replay and migration parity coverage gate map changes before apply.",
      x: 52,
      y: 78,
      objectState: "saved",
      trust: evalSuite.regressionCount > 0 ? "watching" : "healthy",
      risk: evalSuite.regressionCount > 0 ? "high" : "low",
      coveragePercent: evalSuite.passRate,
      latencyMs: 0,
      costUsd: 0,
      dependencies: ["policy-refund", "tool-refund", "memory-preference"],
      toolIds: [readTool.id, mutatingTool.id],
      memoryIds: [memory.id],
      evalIds: [evalSuite.id],
      evidence: [evalSuite.id, trace.id],
      codeRef: "evals/refunds.yaml",
      canEdit: true,
      hazardIds: ["hazard_stale_approval"],
    },
    {
      id: "output-answer",
      kind: "output",
      label: "Grounded answer",
      summary:
        "Final response cites policy, tool result, memory boundary, and handoff rule.",
      x: 82,
      y: 18,
      objectState: agent.objectState,
      trust: agent.trust,
      risk: "medium",
      coveragePercent: 94,
      latencyMs: agent.p95LatencyMs,
      costUsd: agent.costPerTurnUsd,
      dependencies: ["policy-refund", "tool-lookup", "memory-preference"],
      toolIds: [readTool.id],
      memoryIds: [memory.id],
      evalIds: [evalSuite.id],
      evidence: ["span_answer", trace.snapshotId],
      codeRef: "agent.response.yaml#grounded_refund_answer",
      canEdit: true,
      hazardIds: ["hazard_circular_dependency"],
    },
  ];

  return {
    agentId,
    agentName: agent.name,
    branch: fixture.workspace.branch,
    objectState: agent.objectState,
    trust: agent.trust,
    confidence: evalSuite.confidence,
    nodes,
    edges: [
      {
        id: "edge-trigger-router",
        source: "trigger-chat",
        target: "intent-router",
        label: "turn classified",
        evidence: "trace_refund_742 span_context",
        status: "ok",
      },
      {
        id: "edge-router-policy",
        source: "intent-router",
        target: "policy-refund",
        label: "refund intent",
        evidence: "eval_refunds cancellation cases",
        status: "warning",
      },
      {
        id: "edge-policy-output",
        source: "policy-refund",
        target: "output-answer",
        label: "policy citation",
        evidence: "snap_refund_may",
        status: "ok",
      },
      {
        id: "edge-router-lookup",
        source: "intent-router",
        target: "tool-lookup",
        label: "order lookup",
        evidence: "span_tool lookup_order",
        status: "ok",
      },
      {
        id: "edge-policy-refund-tool",
        source: "policy-refund",
        target: "tool-refund",
        label: "refund side effect",
        evidence: deploy.id,
        status: "blocked",
      },
      {
        id: "edge-policy-memory",
        source: "policy-refund",
        target: "memory-preference",
        label: "safe memory write",
        evidence: enterpriseControl.id,
        status: "ok",
      },
      {
        id: "edge-eval-gate",
        source: "eval-coverage",
        target: "tool-refund",
        label: "gates staged tool",
        evidence: evalSuite.id,
        status: "blocked",
      },
      {
        id: "edge-output-eval",
        source: "output-answer",
        target: "eval-coverage",
        label: "replay coverage",
        evidence: trace.id,
        status: "warning",
      },
    ],
    hazards: [
      {
        id: "hazard_circular_dependency",
        title: "Circular dependency",
        severity: "blocked",
        description:
          "Routing final answers back into the trigger would hide logic in the map and create an infinite preview path.",
        nodeIds: ["output-answer", "trigger-chat"],
        evidence: "map_edit_validation cycle_check",
        requiredBehavior:
          "Reject the edit before the graph enters a bad state.",
      },
      {
        id: "hazard_tool_grant",
        title: "Money-moving tool grant",
        severity: "high",
        description:
          "The staged refund tool can affect money movement and needs approval before production.",
        nodeIds: ["tool-refund"],
        evidence: `${deploy.id}; ${mutatingTool.id}`,
        requiredBehavior:
          "Keep the grant staged, require preview, and show the approval path.",
      },
      {
        id: "hazard_stale_approval",
        title: "Stale approval after edit",
        severity: "medium",
        description:
          "Editing the refund policy invalidates the existing approval request.",
        nodeIds: ["policy-refund", "eval-coverage"],
        evidence: "approval_request_refund_policy_v23",
        requiredBehavior:
          "Invalidate and request approval again after preview.",
      },
    ],
    forkPoints: [
      {
        id: "fork-refund-turn",
        nodeId: "output-answer",
        label: "Fork from refund trace",
        branch: "fork/trace_refund_742-may-policy",
        traceId: trace.id,
        snapshotId: trace.snapshotId,
        evidence: `${trace.id}; ${trace.snapshotId}`,
        tokenDelta: "+128 tokens",
        latencyDelta: "+210 ms",
        costDelta: "+USD $0.004",
        evalDelta: "1 Spanish refund case still failing",
      },
    ],
    coverage: {
      dependency: 92,
      tool: 85,
      memory: 93,
      eval: evalSuite.passRate,
    },
  };
}

export function createEmptyAgentMapData(agentId = "agent_empty"): AgentMapData {
  const base = createAgentMapData(agentId);
  return {
    ...base,
    nodes: [],
    edges: [],
    hazards: [],
    forkPoints: [],
    coverage: {
      dependency: 0,
      tool: 0,
      memory: 0,
      eval: 0,
    },
    confidence: "unsupported",
    degradedReason:
      "No map instrumentation has been captured for this agent branch.",
  };
}
