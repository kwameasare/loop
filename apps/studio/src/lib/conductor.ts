import type {
  ConfidenceLevel,
  ObjectState,
  TrustState,
} from "@/lib/design-tokens";
import { targetUxFixtures, type TargetUXFixture } from "@/lib/target-ux";

export type ConductorAgentStatus = "ready" | "active" | "degraded" | "blocked";

export type HandoffState = "ready" | "active" | "violated" | "blocked";

export interface ConductorToolGrant {
  name: string;
  mode: "read" | "draft" | "live" | "blocked";
  evidence: string;
}

export interface ConductorSubAgent {
  id: string;
  name: string;
  purpose: string;
  owner: string;
  version: string;
  objectState: ObjectState;
  trust: TrustState;
  status: ConductorAgentStatus;
  currentOwner: string;
  tools: ConductorToolGrant[];
  budgetUsd: number;
  spentUsd: number;
  latencyP95Ms: number;
  evalCoveragePercent: number;
  evalConfidence: ConfidenceLevel;
  memoryAccess: string;
  activeHandoffs: number;
  costEvidence: string;
  latencyEvidence: string;
  failurePaths: string[];
  traceSpans: string[];
}

export interface HandoffContract {
  id: string;
  name: string;
  from: string;
  to: string;
  purpose: string;
  state: HandoffState;
  inputSchema: string[];
  outputSchema: string[];
  timeoutMs: number;
  fallback: string;
  memoryAccess: string;
  toolGrants: string[];
  budgetUsd: number;
  currentOwner: string;
  evidenceTrace: string;
  violation?: string | undefined;
}

export interface DelegationTrace {
  id: string;
  traceId: string;
  contractId: string;
  sourceAgent: string;
  targetAgent: string;
  spanId: string;
  status: "ok" | "warning" | "failed";
  latencyMs: number;
  costUsd: number;
  evidence: string;
}

export interface ConductorTopologyEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  state: HandoffState;
}

export interface ConductorData {
  agentId: string;
  agentName: string;
  branch: string;
  objectState: ObjectState;
  trust: TrustState;
  subAgents: ConductorSubAgent[];
  contracts: HandoffContract[];
  delegations: DelegationTrace[];
  topology: ConductorTopologyEdge[];
  orchestrationEvidence: string;
  permissionReason?: string | undefined;
  degradedReason?: string | undefined;
}

export interface ConductorClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function cpApiBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("LOOP_CP_API_BASE_URL is required for conductor calls");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

export async function fetchConductorData(
  agentId: string,
  opts: ConductorClientOptions = {},
): Promise<ConductorData> {
  let base: string;
  try {
    base = cpApiBaseUrl(opts.baseUrl);
  } catch (err) {
    if (err instanceof Error && /LOOP_CP_API_BASE_URL/.test(err.message)) {
      return createConductorData(agentId);
    }
    throw err;
  }
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const response = await fetcher(
    `${base}/agents/${encodeURIComponent(agentId)}/conductor`,
    {
      method: "GET",
      headers,
      cache: "no-store",
    },
  );
  if (response.status === 404) return createBlockedConductorData(agentId);
  if (!response.ok) {
    throw new Error(`cp-api GET agent conductor -> ${response.status}`);
  }
  return (await response.json()) as ConductorData;
}

export function createConductorData(
  agentId: string,
  fixture: TargetUXFixture = targetUxFixtures,
): ConductorData {
  const agent =
    fixture.agents.find((candidate) => candidate.id === agentId) ??
    fixture.agents[0]!;
  const trace = fixture.traces[0]!;
  const evalSuite = fixture.evals[0]!;
  const memory = fixture.memory[0]!;
  const readTool = fixture.tools[0]!;
  const moneyTool = fixture.tools[1]!;
  const cost = fixture.costs[0]!;
  const enterprise = fixture.enterprise[0]!;

  const subAgents: ConductorSubAgent[] = [
    {
      id: "sub_intake_triage",
      name: "Intake Triage",
      purpose:
        "Classify renewal, refund, escalation, and channel constraints before deeper work begins.",
      owner: "Support Automation",
      version: "v12.4",
      objectState: "saved",
      trust: "healthy",
      status: "active",
      currentOwner: agent.name,
      tools: [
        {
          name: readTool.name,
          mode: "read",
          evidence: `${readTool.id}: ${readTool.usage7d.toLocaleString()} read calls over 7 days`,
        },
      ],
      budgetUsd: 0.012,
      spentUsd: 0.008,
      latencyP95Ms: 220,
      evalCoveragePercent: 98,
      evalConfidence: "high",
      memoryAccess: "session and scratch memory; durable writes denied",
      activeHandoffs: 2,
      costEvidence: `${cost.id}: cached routing keeps intake under $0.01 p50`,
      latencyEvidence: `${trace.id}: span_context completed in ${trace.spans[0]?.durationMs ?? 0} ms`,
      failurePaths: [
        "Ambiguous cancellation intent routes to Refund Specialist with low-confidence marker.",
        "Unsupported channel routes to human inbox with transcript and trace ID.",
      ],
      traceSpans: ["span_context", "span_answer"],
    },
    {
      id: "sub_refund_specialist",
      name: "Refund Specialist",
      purpose:
        "Quote the current refund policy, prepare a safe refund step, and keep money movement gated.",
      owner: "Revenue Operations",
      version: trace.version,
      objectState: "staged",
      trust: "watching",
      status: "active",
      currentOwner: "Refund policy owner",
      tools: [
        {
          name: readTool.name,
          mode: "read",
          evidence: `${readTool.id}: order lookup trace span ${trace.spans[1]?.id ?? "span_tool"}`,
        },
        {
          name: moneyTool.name,
          mode: "draft",
          evidence: `${moneyTool.id}: live grant requires approval before production`,
        },
      ],
      budgetUsd: 0.026,
      spentUsd: 0.019,
      latencyP95Ms: 610,
      evalCoveragePercent: evalSuite.passRate,
      evalConfidence: trace.confidence,
      memoryAccess: `reads ${memory.key}; may write only with explicit user confirmation`,
      activeHandoffs: 2,
      costEvidence: `${cost.id}: ${cost.recommendation}`,
      latencyEvidence: `${trace.id}: lookup_order plus grounded answer stayed under 900 ms`,
      failurePaths: [
        "Policy conflict holds the handoff for reviewer approval.",
        "Money movement remains draft-only until Revenue Operations approves the grant.",
      ],
      traceSpans: ["span_tool", "span_answer"],
    },
    {
      id: "sub_retention_guardian",
      name: "Retention Guardian",
      purpose:
        "Check cancellation tone, retention policy, and escalation language before a final answer ships.",
      owner: "Customer Success",
      version: "v8.9",
      objectState: "draft",
      trust: "drifting",
      status: "degraded",
      currentOwner: "Customer Success lead",
      tools: [],
      budgetUsd: 0.009,
      spentUsd: 0.006,
      latencyP95Ms: 340,
      evalCoveragePercent: 82,
      evalConfidence: "medium",
      memoryAccess: "no durable memory; reads session summary only",
      activeHandoffs: 1,
      costEvidence:
        "cost_retention: tone check sampled on high-risk turns only",
      latencyEvidence: "trace_refund_742#tone_guard: 340 ms p95 under canary",
      failurePaths: [
        "Missing retention policy routes back to Refund Specialist with exact contract violation.",
        "Legal-threat language escalates to inbox without sending a customer reply.",
      ],
      traceSpans: ["tone_guard", "handoff_review"],
    },
  ];

  const contracts: HandoffContract[] = [
    {
      id: "contract_intake_to_refund",
      name: "Cancellation intent to refund policy",
      from: "Intake Triage",
      to: "Refund Specialist",
      purpose:
        "Move a classified cancellation request into refund reasoning with visible constraints.",
      state: "active",
      inputSchema: ["intent", "channel", "order_id", "confidence"],
      outputSchema: ["policy_quote", "allowed_actions", "risk_reason"],
      timeoutMs: 1200,
      fallback:
        "Return to Intake Triage with low-confidence reason and keep the customer reply paused.",
      memoryAccess: "session read, scratch read/write, durable user read only",
      toolGrants: [`${readTool.name}: read`, `${moneyTool.name}: draft only`],
      budgetUsd: 0.026,
      currentOwner: "Refund policy owner",
      evidenceTrace: `${trace.id}#span_context`,
    },
    {
      id: "contract_refund_to_retention",
      name: "Refund answer to retention guard",
      from: "Refund Specialist",
      to: "Retention Guardian",
      purpose:
        "Ask the retention guard to check tone, cancellation promise, and escalation risk.",
      state: "violated",
      inputSchema: ["draft_answer", "policy_quote", "customer_segment"],
      outputSchema: ["approved_answer", "tone_notes", "handoff_reason"],
      timeoutMs: 900,
      fallback:
        "Hold the answer and create an inbox task for Customer Success lead.",
      memoryAccess: "session summary only; no durable reads",
      toolGrants: ["none"],
      budgetUsd: 0.009,
      currentOwner: "Customer Success lead",
      evidenceTrace: `${trace.id}#handoff_review`,
      violation:
        "Contract violation: customer_segment missing from input; fallback created inbox draft.",
    },
    {
      id: "contract_voice_followup",
      name: "Voice follow-up preparation",
      from: "Retention Guardian",
      to: "Voice Receptionist",
      purpose:
        "Prepare a concise phone handoff only after the customer asks for a callback.",
      state: "ready",
      inputSchema: ["approved_answer", "callback_window", "consent"],
      outputSchema: ["voice_brief", "call_guardrails"],
      timeoutMs: 1500,
      fallback: "Send web reply and leave callback unqueued.",
      memoryAccess: "no memory writes; reads approved answer snapshot",
      toolGrants: ["voice_channel: draft"],
      budgetUsd: 0.015,
      currentOwner: "Voice operations",
      evidenceTrace: "eval_voice_handoff#case_14",
    },
  ];

  return {
    agentId,
    agentName: agent.name,
    branch: fixture.workspace.branch,
    objectState: fixture.workspace.objectState,
    trust: fixture.workspace.trust,
    subAgents,
    contracts,
    delegations: [
      {
        id: "delegation_refund_742_1",
        traceId: trace.id,
        contractId: "contract_intake_to_refund",
        sourceAgent: "Intake Triage",
        targetAgent: "Refund Specialist",
        spanId: "span_context",
        status: "ok",
        latencyMs: 112,
        costUsd: 0.004,
        evidence: "intent classified with 0.91 confidence; order lookup queued",
      },
      {
        id: "delegation_refund_742_2",
        traceId: trace.id,
        contractId: "contract_refund_to_retention",
        sourceAgent: "Refund Specialist",
        targetAgent: "Retention Guardian",
        spanId: "handoff_review",
        status: "warning",
        latencyMs: 340,
        costUsd: 0.006,
        evidence: "customer_segment missing; fallback inbox task linked",
      },
    ],
    topology: [
      {
        id: "edge_intake_refund",
        source: "sub_intake_triage",
        target: "sub_refund_specialist",
        label: "active handoff",
        state: "active",
      },
      {
        id: "edge_refund_retention",
        source: "sub_refund_specialist",
        target: "sub_retention_guardian",
        label: "violated contract",
        state: "violated",
      },
    ],
    orchestrationEvidence: `${enterprise.id}; ${trace.id}; ${evalSuite.id}; branch ${fixture.workspace.branch}`,
  };
}

export function createBlockedConductorData(
  agentId = "agent_blocked",
): ConductorData {
  const base = createConductorData(agentId);
  return {
    ...base,
    trust: "blocked",
    degradedReason:
      "The conductor can show topology and traces, but editing handoff contracts is locked until workspace approval.",
    permissionReason:
      "Editing production handoff contracts requires Workspace admin approval because the refund tool can move money.",
    contracts: base.contracts.map((contract) => ({
      ...contract,
      state: contract.state === "violated" ? "violated" : "blocked",
      violation:
        contract.violation ??
        "Blocked by workspace policy until handoff approval is granted.",
    })),
  };
}
