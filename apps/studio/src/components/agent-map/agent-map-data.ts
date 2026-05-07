import type {
  ConfidenceLevel,
  ObjectState,
  TrustState,
} from "@/lib/design-tokens";
import {
  listAgentVersions,
  type AgentVersionDetail,
  type EvalStatus,
} from "@/lib/agent-versions";
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

export interface AgentMapClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
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

function parseVersionSpec(version: AgentVersionDetail): Record<string, unknown> {
  try {
    const parsed = JSON.parse(version.config_json) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

function textFromSpec(
  spec: Record<string, unknown>,
  keys: readonly string[],
): string {
  for (const key of keys) {
    const value = spec[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}

function labelFromUnknown(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  for (const key of ["name", "id", "key", "label", "path"]) {
    const item = record[key];
    if (typeof item === "string" && item.trim()) return item.trim();
  }
  return null;
}

function listFromSpec(
  spec: Record<string, unknown>,
  keys: readonly string[],
): string[] {
  for (const key of keys) {
    const value = spec[key];
    if (Array.isArray(value)) {
      const out = value
        .map(labelFromUnknown)
        .filter((item): item is string => Boolean(item));
      if (out.length > 0) return out;
    }
    if (typeof value === "string" && value.trim()) {
      return value
        .split(/[,\n]/)
        .map((part) => part.trim())
        .filter(Boolean);
    }
  }
  return [];
}

function sentencePreview(text: string): string {
  const [first] = text
    .split(/(?<=[.!?])\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (!first) return "No system prompt declared in this version.";
  return first.length > 156 ? `${first.slice(0, 153)}...` : first;
}

function objectStateFromVersion(version: AgentVersionDetail): ObjectState {
  if (version.deploy_state === "active") return "production";
  if (version.deploy_state === "canary") return "canary";
  if (version.deploy_state === "rolled_back") return "archived";
  if (version.promoted_to === "staging") return "staged";
  return "saved";
}

function trustFromEval(status: EvalStatus): TrustState {
  if (status === "passed") return "healthy";
  if (status === "failed") return "blocked";
  if (status === "running" || status === "pending") return "watching";
  return "drifting";
}

function confidenceFromEval(status: EvalStatus): ConfidenceLevel {
  if (status === "passed") return "high";
  if (status === "failed") return "low";
  if (status === "running" || status === "pending") return "medium";
  return "unsupported";
}

function coverageFromEval(status: EvalStatus): number {
  if (status === "passed") return 96;
  if (status === "failed") return 62;
  if (status === "running") return 78;
  if (status === "pending") return 54;
  return 0;
}

function riskFromToolName(name: string): AgentMapRisk {
  const lower = name.toLowerCase();
  if (
    /refund|charge|payment|delete|write|send|email|sms|transfer|payout/.test(
      lower,
    )
  ) {
    return "high";
  }
  if (/update|create|post|patch|mutation|webhook/.test(lower)) {
    return "medium";
  }
  return "low";
}

function nodeId(prefix: string, label: string): string {
  const safe =
    label
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 42) || "item";
  return `${prefix}-${safe}`;
}

function uniqueLabels(labels: readonly string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const label of labels) {
    const trimmed = label.trim();
    if (!trimmed || seen.has(trimmed)) continue;
    seen.add(trimmed);
    out.push(trimmed);
  }
  return out;
}

export function createAgentMapDataFromVersion(
  agentId: string,
  version: AgentVersionDetail,
  fixture: TargetUXFixture = targetUxFixtures,
): AgentMapData {
  const base = createAgentMapData(agentId, fixture);
  const spec = parseVersionSpec(version);
  const prompt = textFromSpec(spec, [
    "system_prompt",
    "prompt",
    "instructions",
    "behavior",
  ]);
  const tools = uniqueLabels(
    listFromSpec(spec, ["tools", "tool_ids", "tool_grants"]),
  );
  const memoryRules = uniqueLabels(
    listFromSpec(spec, ["memory", "memory_rules", "memory_policies"]),
  );
  const evals = uniqueLabels(
    listFromSpec(spec, ["evals", "eval_suites", "evaluation_suites"]),
  );
  const subAgents = uniqueLabels(
    listFromSpec(spec, ["sub_agents", "agents", "delegates"]),
  );
  const state = objectStateFromVersion(version);
  const trust = trustFromEval(version.eval_status);
  const coverage = coverageFromEval(version.eval_status);
  const versionRef = `agent:${agentId}:v${version.version}`;
  const nodes: AgentMapNode[] = [
    {
      id: "trigger-live-turn",
      kind: "trigger",
      label: "Inbound turns",
      summary:
        "Channel events enter the saved agent version before any tool, memory, or handoff can run.",
      x: 12,
      y: 22,
      objectState: state,
      trust,
      risk: "low",
      coveragePercent: coverage,
      latencyMs: 20,
      costUsd: 0,
      dependencies: [],
      toolIds: [],
      memoryIds: [],
      evalIds: evals,
      evidence: [versionRef],
      codeRef: "version.spec#channels",
      canEdit: state !== "production",
      readonlyReason:
        state === "production"
          ? "Production version opens as read-only; fork before editing."
          : undefined,
      hazardIds: [],
    },
    {
      id: "behavior-live-policy",
      kind: "policy",
      label: "Behavior instructions",
      summary: sentencePreview(prompt),
      x: 34,
      y: 22,
      objectState: state === "production" ? "saved" : state,
      trust,
      risk: prompt ? "medium" : "high",
      coveragePercent: coverage,
      latencyMs: 80,
      costUsd: 0.004,
      dependencies: ["trigger-live-turn"],
      toolIds: tools,
      memoryIds: memoryRules,
      evalIds: evals,
      evidence: [versionRef, prompt ? "spec.system_prompt" : "spec.prompt_missing"],
      codeRef: "version.spec#system_prompt",
      canEdit: state !== "production",
      readonlyReason:
        state === "production"
          ? "Production behavior requires a preview branch before edit."
          : undefined,
      hazardIds: prompt ? [] : ["hazard-missing-prompt"],
    },
  ];
  const edges: AgentMapEdge[] = [
    {
      id: "edge-live-trigger-behavior",
      source: "trigger-live-turn",
      target: "behavior-live-policy",
      label: "context enters behavior",
      evidence: versionRef,
      status: "ok",
    },
  ];
  const toolNodes = tools.slice(0, 6).map((tool, index) => {
    const risk = riskFromToolName(tool);
    const id = nodeId("tool", tool);
    const y = 42 + (index % 3) * 15;
    const x = 24 + Math.floor(index / 3) * 18;
    edges.push({
      id: `edge-behavior-${id}`,
      source: "behavior-live-policy",
      target: id,
      label: risk === "high" ? "gated tool grant" : "tool call",
      evidence: `${versionRef}:tools.${index}`,
      status: risk === "high" ? "warning" : "ok",
    });
    return {
      id,
      kind: "tool" as const,
      label: tool,
      summary:
        risk === "high"
          ? "Side-effect capable tool detected from the live version spec; preview and approval should gate production changes."
          : "Tool binding detected from the live version spec.",
      x,
      y,
      objectState: risk === "high" ? "staged" : state,
      trust: risk === "high" && version.eval_status !== "passed" ? "watching" : trust,
      risk,
      coveragePercent: risk === "high" ? Math.max(coverage - 12, 0) : coverage,
      latencyMs: risk === "high" ? 260 : 140,
      costUsd: risk === "high" ? 0.018 : 0.006,
      dependencies: ["behavior-live-policy"],
      toolIds: [tool],
      memoryIds: [],
      evalIds: evals,
      evidence: [`${versionRef}:tools.${index}`],
      codeRef: `version.spec#tools.${index}`,
      canEdit: risk !== "high" && state !== "production",
      readonlyReason:
        risk === "high"
          ? "Side-effect capable tool grants open in Tools Room with safety contract."
          : state === "production"
            ? "Production tool bindings require a preview branch."
            : undefined,
      hazardIds: risk === "high" ? ["hazard-live-tool-grant"] : [],
    };
  });
  nodes.push(...toolNodes);

  const memoryNodeIds = memoryRules.slice(0, 3).map((rule, index) => {
    const id = nodeId("memory", rule);
    nodes.push({
      id,
      kind: "memory",
      label: rule,
      summary:
        "Memory policy declared by the saved version; inspect Memory Studio for per-turn writes and deletion state.",
      x: 64,
      y: 34 + index * 16,
      objectState: state === "production" ? "saved" : state,
      trust,
      risk: /secret|payment|card|password|token/i.test(rule) ? "high" : "low",
      coveragePercent: coverage,
      latencyMs: 60,
      costUsd: 0.002,
      dependencies: ["behavior-live-policy"],
      toolIds: [],
      memoryIds: [rule],
      evalIds: evals,
      evidence: [`${versionRef}:memory.${index}`],
      codeRef: `version.spec#memory.${index}`,
      canEdit: state !== "production",
      readonlyReason:
        state === "production"
          ? "Production memory rules require a preview branch."
          : undefined,
      hazardIds: /secret|payment|card|password|token/i.test(rule)
        ? ["hazard-memory-sensitive"]
        : [],
    });
    edges.push({
      id: `edge-behavior-${id}`,
      source: "behavior-live-policy",
      target: id,
      label: "memory boundary",
      evidence: `${versionRef}:memory.${index}`,
      status: /secret|payment|card|password|token/i.test(rule)
        ? "warning"
        : "ok",
    });
    return id;
  });

  const outputDependencies = [
    "behavior-live-policy",
    ...toolNodes.map((node) => node.id),
    ...memoryNodeIds,
  ];
  nodes.push({
    id: "eval-live-gate",
    kind: "eval",
    label: evals[0] ?? "Version eval gate",
    summary:
      version.eval_status === "passed"
        ? "The latest saved eval state is passing for this version."
        : `Latest eval state is ${version.eval_status}; promotion needs evidence before production.`,
    x: 52,
    y: 82,
    objectState: version.eval_status === "passed" ? "saved" : "draft",
    trust,
    risk: version.eval_status === "failed" ? "blocked" : "medium",
    coveragePercent: coverage,
    latencyMs: 0,
    costUsd: 0,
    dependencies: outputDependencies,
    toolIds: tools,
    memoryIds: memoryRules,
    evalIds: evals,
    evidence: [`${versionRef}:eval_status=${version.eval_status}`],
    codeRef: "version.spec#evals",
    canEdit: true,
    hazardIds: version.eval_status === "failed" ? ["hazard-eval-regression"] : [],
  });
  nodes.push({
    id: "output-live-answer",
    kind: "output",
    label: "Grounded answer",
    summary:
      "Final response must remain explainable through behavior, tools, memory boundaries, and eval evidence.",
    x: 84,
    y: 22,
    objectState: state,
    trust,
    risk: version.eval_status === "failed" ? "high" : "medium",
    coveragePercent: coverage,
    latencyMs: 980,
    costUsd: 0.025,
    dependencies: outputDependencies,
    toolIds: tools,
    memoryIds: memoryRules,
    evalIds: evals,
    evidence: [versionRef],
    codeRef: "version.spec#response",
    canEdit: state !== "production",
    readonlyReason:
      state === "production"
        ? "Fork from this production version before changing final behavior."
        : undefined,
    hazardIds: version.eval_status === "failed" ? ["hazard-eval-regression"] : [],
  });
  edges.push(
    {
      id: "edge-behavior-output",
      source: "behavior-live-policy",
      target: "output-live-answer",
      label: "answer policy",
      evidence: versionRef,
      status: version.eval_status === "failed" ? "warning" : "ok",
    },
    {
      id: "edge-output-eval",
      source: "output-live-answer",
      target: "eval-live-gate",
      label: "replay coverage",
      evidence: `${versionRef}:eval_status=${version.eval_status}`,
      status: version.eval_status === "passed" ? "ok" : "warning",
    },
  );
  for (const toolNode of toolNodes) {
    edges.push({
      id: `edge-${toolNode.id}-output`,
      source: toolNode.id,
      target: "output-live-answer",
      label: "tool evidence",
      evidence: toolNode.evidence[0] ?? versionRef,
      status: toolNode.risk === "high" ? "warning" : "ok",
    });
  }
  for (const memoryId of memoryNodeIds) {
    edges.push({
      id: `edge-${memoryId}-output`,
      source: memoryId,
      target: "output-live-answer",
      label: "memory evidence",
      evidence: versionRef,
      status: "ok",
    });
  }

  const hazards: AgentMapHazard[] = [];
  if (!prompt) {
    hazards.push({
      id: "hazard-missing-prompt",
      title: "Missing behavior instructions",
      severity: "high",
      description:
        "The live version spec does not declare a system prompt or instruction field.",
      nodeIds: ["behavior-live-policy"],
      evidence: `${versionRef}:prompt_missing`,
      requiredBehavior:
        "Keep edits in draft and add explicit behavior instructions before preview.",
    });
  }
  if (toolNodes.some((node) => node.risk === "high")) {
    hazards.push({
      id: "hazard-live-tool-grant",
      title: "Side-effect capable tool",
      severity: "high",
      description:
        "At least one tool appears capable of money movement, writes, deletion, or external messaging.",
      nodeIds: toolNodes
        .filter((node) => node.risk === "high")
        .map((node) => node.id),
      evidence: `${versionRef}:tools`,
      requiredBehavior:
        "Gate production changes through Tools Room safety contract, preview, approval, and rollback.",
    });
  }
  if (memoryRules.some((rule) => /secret|payment|card|password|token/i.test(rule))) {
    hazards.push({
      id: "hazard-memory-sensitive",
      title: "Sensitive memory rule",
      severity: "high",
      description:
        "A memory rule mentions secret-like or payment-like data and needs policy review.",
      nodeIds: memoryNodeIds,
      evidence: `${versionRef}:memory`,
      requiredBehavior:
        "Route to Memory Studio, block durable writes, and require explicit retention evidence.",
    });
  }
  if (version.eval_status === "failed") {
    hazards.push({
      id: "hazard-eval-regression",
      title: "Eval regression",
      severity: "blocked",
      description:
        "The saved version has failing eval evidence; promotion should remain blocked.",
      nodeIds: ["eval-live-gate", "output-live-answer"],
      evidence: `${versionRef}:eval_status=failed`,
      requiredBehavior:
        "Replay failures, repair the draft, and rerun evals before production.",
    });
  }
  if (subAgents.length > 0) {
    hazards.push({
      id: "hazard-handoff-contracts",
      title: "Handoff contracts present",
      severity: "medium",
      description:
        "Sub-agent topology is declared; Multi-Agent Conductor owns contract-level verification.",
      nodeIds: ["behavior-live-policy"],
      evidence: `${versionRef}:sub_agents=${subAgents.length}`,
      requiredBehavior:
        "Inspect Conductor before changing shared memory, tools, or ownership boundaries.",
    });
  }

  return {
    ...base,
    agentId,
    branch: `v${version.version}`,
    objectState: state,
    trust,
    confidence: confidenceFromEval(version.eval_status),
    nodes,
    edges,
    hazards,
    forkPoints: [
      {
        id: `fork-${version.id}`,
        nodeId: "output-live-answer",
        label: `Fork v${version.version}`,
        branch: `fork/${agentId}-v${version.version}`,
        traceId: version.id,
        snapshotId: `version:${version.id}`,
        evidence: versionRef,
        tokenDelta: "preview required",
        latencyDelta: "computed after replay",
        costDelta: "computed after replay",
        evalDelta:
          version.eval_status === "passed"
            ? "baseline passing"
            : `baseline ${version.eval_status}`,
      },
    ],
    coverage: {
      dependency:
        outputDependencies.length > 1
          ? Math.min(100, 72 + outputDependencies.length * 4)
          : 45,
      tool: tools.length > 0 ? Math.max(70, coverage - 6) : 0,
      memory: memoryRules.length > 0 ? Math.max(70, coverage - 8) : 0,
      eval: coverage,
    },
    degradedReason:
      version.eval_status === "skipped"
        ? "No eval run is attached to this saved version yet."
        : undefined,
  };
}

export async function fetchAgentMapData(
  agentId: string,
  opts: AgentMapClientOptions = {},
): Promise<AgentMapData> {
  const versions = await listAgentVersions(agentId, {
    ...opts,
    pageSize: 1,
  });
  const [latest] = versions.items;
  if (!latest) return createEmptyAgentMapData(agentId);
  return createAgentMapDataFromVersion(agentId, latest);
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
