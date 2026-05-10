/**
 * P0.3: cp-api client for agent tool catalog.
 *
 * Reads ``GET /v1/agents/{agent_id}/tools`` for per-agent tool bindings.
 * The first live route exposes tools declared on the active/latest agent
 * version spec; richer credential health and marketplace install metadata
 * can layer onto the same shape.
 */

import type {
  ConfidenceLevel,
  ObjectState,
  TrustState,
} from "@/lib/design-tokens";
import { targetUxFixtures, type TargetUXFixture } from "@/lib/target-ux";
import { localToolContracts, type ToolContract } from "@/lib/tool-contracts";

export type AgentToolKind = "mcp" | "http";

export interface AgentTool {
  id: string;
  name: string;
  kind: AgentToolKind;
  /** Human-readable description, optional. */
  description?: string;
  /** Origin server URL (MCP base URL or HTTP server root). */
  source?: string;
}

export interface AgentToolsClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function cpApiBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) throw new Error("LOOP_CP_API_BASE_URL is required for tools calls");
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

export async function listAgentTools(
  agent_id: string,
  opts: AgentToolsClientOptions = {},
): Promise<AgentTool[]> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const url = `${cpApiBaseUrl(opts.baseUrl)}/agents/${encodeURIComponent(
    agent_id,
  )}/tools`;
  const res = await fetcher(url, {
    method: "GET",
    headers,
    cache: "no-store",
  });
  if (res.status === 404) {
    throw new Error(
      "cp-api GET agent tools -> 404. Studio will not treat an unavailable tool-binding route as an agent with no tools.",
    );
  }
  if (!res.ok) throw new Error(`cp-api GET agent tools -> ${res.status}`);
  const body = (await res.json()) as { items?: AgentTool[] };
  return body.items ?? [];
}

export type ToolSideEffect =
  | "read"
  | "write"
  | "money-movement"
  | "external-message";

export type ToolAuthMode = "mock" | "oauth" | "secret" | "mcp";

export type ToolEnvironmentMode = "mock" | "live" | "blocked";

export type ToolDraftSource = "curl" | "openapi" | "postman" | "devtools";

export interface ToolSchemaField {
  name: string;
  type: string;
  required: boolean;
  sensitive: boolean;
  description: string;
}

export interface ToolSafetyContract {
  mutatesData: boolean;
  spendsMoney: boolean;
  exposesPersonalData: boolean;
  agentsAllowed: string[];
  sensitiveArguments: string[];
  failureMode: string;
  auditEvent: string;
  evidence: string;
}

export interface ToolEnvironmentStatus {
  dev: ToolEnvironmentMode;
  staging: ToolEnvironmentMode;
  production: ToolEnvironmentMode;
  reason: string;
}

export interface ToolsRoomTool {
  id: string;
  name: string;
  kind: AgentToolKind;
  description: string;
  source: string;
  owner: string;
  objectState: ObjectState;
  trust: TrustState;
  sideEffect: ToolSideEffect;
  authMode: ToolAuthMode;
  secretRef: string;
  kmsKeyRef: string;
  usage7d: number;
  failureRate: number;
  costPer1kUsd: number;
  evalCoveragePercent: number;
  evalConfidence: ConfidenceLevel;
  successRatePercent: number;
  p95LatencyMs: number;
  retryRatePercent: number;
  failedCalls7d: number;
  piiSent7d: number;
  lastSchemaChangeAt: string;
  environment: string;
  dataClassification: string;
  idempotency: string;
  allowedChannels: string[];
  approvalRequirements: string;
  auditRequirements: string;
  compensationBehavior: string;
  timeoutMs: number;
  retryPolicy: string;
  rateLimit: string;
  mockStatus: string;
  liveStatus: string;
  productionGrant: "approved" | "blocked" | "review";
  productionBoundary: string;
  productionNextStep: string;
  schema: ToolSchemaField[];
  outputSchema: ToolSchemaField[];
  sampleCall: string;
  mockResponse: string;
  safety: ToolSafetyContract;
  evidence: string[];
}

export interface ToolDraft {
  source: ToolDraftSource;
  name: string;
  method: string;
  url: string;
  authNeeds: string[];
  sideEffect: ToolSideEffect;
  schema: ToolSchemaField[];
  mockResponse: string;
  evalStub: string;
  productionBoundary: string;
  evidence: string;
}

export interface ToolsRoomData {
  agentId: string;
  agentName: string;
  branch: string;
  objectState: ObjectState;
  trust: TrustState;
  tools: ToolsRoomTool[];
  toolContracts: ToolContract[];
  catalogEvidence: string;
  degradedReason?: string | undefined;
}

const DEFAULT_TOOL_IMPORT = [
  "curl -X POST https://api.example.test/refunds",
  "  -H 'Authorization: Bearer <redacted>'",
  "  -H 'Content-Type: application/json'",
  '  -d \'{"order_id":"ord_123","amount_cents":5000,"reason":"policy_exception"}\'',
].join(" \\\n");

function methodFromCurl(input: string): string {
  const method = input.match(/(?:-X|--request)\s+([A-Z]+)/i)?.[1];
  if (method) return method.toUpperCase();
  return input.includes("-d") || input.includes("--data") ? "POST" : "GET";
}

function urlFromRequest(input: string): string {
  const match = input.match(/https?:\/\/[^\s'"]+/);
  return match?.[0]?.replace(/\\$/, "") ?? "https://api.example.test/tool";
}

function sideEffectFor(method: string, url: string): ToolSideEffect {
  if (/refund|charge|payment/i.test(url)) return "money-movement";
  if (method === "GET" || method === "HEAD") return "read";
  return "write";
}

function schemaFromRequest(input: string): ToolSchemaField[] {
  const json = input.match(/\{[\s\S]*\}/)?.[0];
  if (!json) {
    return [
      {
        name: "id",
        type: "string",
        required: true,
        sensitive: false,
        description: "Resource identifier from the request path or query.",
      },
    ];
  }
  try {
    const parsed = JSON.parse(json.replace(/\\'/g, "'"));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("non-object body");
    }
    return Object.entries(parsed).map(([name, value]) => ({
      name,
      type: typeof value === "number" ? "number" : "string",
      required: true,
      sensitive: /token|secret|password|card|payment/i.test(name),
      description: `Captured from request body field ${name}.`,
    }));
  } catch {
    return [
      {
        name: "body",
        type: "json",
        required: true,
        sensitive: false,
        description: "Raw request body; review before saving the draft.",
      },
    ];
  }
}

function toolFromFixture(
  agentId: string,
  fixture: TargetUXFixture,
  index: number,
): ToolsRoomTool {
  const target = fixture.tools[index] ?? fixture.tools[0]!;
  const evalSuite = fixture.evals[0]!;
  const deploy = fixture.deploys[0]!;
  const enterprise = fixture.enterprise[0]!;
  const isMoneyMovement = target.sideEffect === "money-movement";
  const name = target.name;
  return {
    id: target.id,
    name,
    kind: target.authMode === "mcp" ? "mcp" : "http",
    description: isMoneyMovement
      ? "Create a refund after policy and approval checks pass."
      : "Look up order status and entitlement before account-specific answers.",
    source: isMoneyMovement
      ? "https://api.example.test/refunds"
      : "mcp://orders.lookup",
    owner: target.owner,
    objectState: target.objectState,
    trust: isMoneyMovement ? "blocked" : "healthy",
    sideEffect: target.sideEffect,
    authMode: target.authMode,
    secretRef: isMoneyMovement
      ? `vault/data/workspace/ws_acme/agent/${agentId}/refunds_api`
      : "mcp grant; no raw secret visible",
    kmsKeyRef: "workspace/ws_acme/tenant_kms_key_id",
    usage7d: target.usage7d,
    failureRate: isMoneyMovement ? 2.8 : 0.4,
    costPer1kUsd: isMoneyMovement ? 3.42 : 0.28,
    evalCoveragePercent: isMoneyMovement ? 84 : evalSuite.passRate,
    evalConfidence: evalSuite.confidence,
    successRatePercent: isMoneyMovement ? 97.2 : 99.6,
    p95LatencyMs: isMoneyMovement ? 840 : 210,
    retryRatePercent: isMoneyMovement ? 0 : 0.7,
    failedCalls7d: isMoneyMovement ? 14 : 5,
    piiSent7d: isMoneyMovement ? 0 : 0,
    lastSchemaChangeAt: isMoneyMovement
      ? "2026-05-02T14:22:00Z"
      : "2026-04-28T09:10:00Z",
    environment: isMoneyMovement ? "staging" : "production",
    dataClassification: isMoneyMovement
      ? "financial action; no raw card data"
      : "customer order metadata",
    idempotency: isMoneyMovement
      ? "Required: order_id + amount_cents + policy window"
      : "Read-only; idempotent by request",
    allowedChannels: isMoneyMovement
      ? ["web_chat", "email"]
      : ["web_chat", "whatsapp", "slack", "teams", "email"],
    approvalRequirements: isMoneyMovement
      ? "Release Manager approval and money cap review"
      : "Tool owner review for schema changes",
    auditRequirements: isMoneyMovement
      ? "tool.refund.requested with reason and trace"
      : "tool.order.lookup with trace span",
    compensationBehavior: isMoneyMovement
      ? "Create reversal ticket; no automatic retry"
      : "Retry lookup or answer with uncertainty",
    timeoutMs: isMoneyMovement ? 3_000 : 1_500,
    retryPolicy: isMoneyMovement
      ? "No automatic retry; idempotency key required."
      : "Two retries with jitter for transport failures.",
    rateLimit: isMoneyMovement
      ? "20 calls / min / agent"
      : "600 calls / min / agent",
    mockStatus: isMoneyMovement
      ? "Deterministic mock recorded from approved refund fixture."
      : "Mock mirrors last 1,240 successful lookup responses.",
    liveStatus: isMoneyMovement
      ? "Live blocked in production until Release Manager approval."
      : "Live approved for production read-only calls.",
    productionGrant: isMoneyMovement ? "blocked" : "approved",
    productionBoundary: isMoneyMovement
      ? "Production grant blocked: money movement requires approval, eval pass, and audit reason."
      : "Production grant approved for read-only lookup after MCP contract check.",
    productionNextStep: isMoneyMovement
      ? "Request approval after `eval_refunds` clears the Spanish refund regression."
      : "Keep monitoring failure rate and cost per 1,000 calls.",
    schema: isMoneyMovement
      ? [
          {
            name: "order_id",
            type: "string",
            required: true,
            sensitive: false,
            description: "Order identifier resolved by lookup_order.",
          },
          {
            name: "amount_cents",
            type: "number",
            required: true,
            sensitive: false,
            description: "Refund amount in cents.",
          },
          {
            name: "reason",
            type: "string",
            required: true,
            sensitive: false,
            description: "Audit-visible refund reason.",
          },
        ]
      : [
          {
            name: "order_id",
            type: "string",
            required: true,
            sensitive: false,
            description: "Customer order identifier.",
          },
          {
            name: "include_entitlements",
            type: "boolean",
            required: false,
            sensitive: false,
            description: "Include refund and cancellation entitlement details.",
          },
        ],
    outputSchema: isMoneyMovement
      ? [
          {
            name: "refund_id",
            type: "string",
            required: true,
            sensitive: false,
            description: "Refund request identifier.",
          },
          {
            name: "status",
            type: "string",
            required: true,
            sensitive: false,
            description: "Approval or completion status.",
          },
        ]
      : [
          {
            name: "refund_window",
            type: "string",
            required: true,
            sensitive: false,
            description: "Policy window returned by lookup.",
          },
          {
            name: "entitlements",
            type: "json",
            required: false,
            sensitive: false,
            description: "Entitlement summary for behavior grounding.",
          },
        ],
    sampleCall: isMoneyMovement
      ? DEFAULT_TOOL_IMPORT
      : "lookup_order({ order_id: 'ord_123', include_entitlements: true })",
    mockResponse: isMoneyMovement
      ? '{"refund_id":"rf_mock_42","status":"requires_approval"}'
      : '{"order_id":"ord_123","refund_window":"May 2026 policy"}',
    safety: {
      mutatesData: isMoneyMovement,
      spendsMoney: isMoneyMovement,
      exposesPersonalData: false,
      agentsAllowed: [agentId],
      sensitiveArguments: isMoneyMovement ? ["authorization header"] : [],
      failureMode: isMoneyMovement
        ? "Do not promise a refund; escalate with trace and request ID."
        : "Answer with uncertainty and ask the customer to retry order lookup.",
      auditEvent: isMoneyMovement
        ? "tool.refund.requested"
        : "tool.order.lookup",
      evidence: isMoneyMovement
        ? `${deploy.id}; ${evalSuite.id}; ${enterprise.id}`
        : `span_tool; ${evalSuite.id}`,
    },
    evidence: isMoneyMovement
      ? [target.id, deploy.id, evalSuite.id, enterprise.id]
      : [target.id, "span_tool lookup_order", evalSuite.id],
  };
}

export function createToolsRoomData(
  agentId: string,
  liveTools: AgentTool[] = [],
  fixture: TargetUXFixture = targetUxFixtures,
  toolContracts: ToolContract[] = [],
  degradedReason?: string | undefined,
): ToolsRoomData {
  const usesLiveData = liveTools.length > 0 || toolContracts.length > 0;
  const fixtureAgent = fixture.agents.find(
    (candidate) => candidate.id === agentId,
  );
  const fixtureFallback = usesLiveData ? undefined : fixture.agents[0];
  const agentName =
    fixtureAgent?.name ?? fixtureFallback?.name ?? `Agent ${agentId}`;
  const tools = usesLiveData
    ? []
    : fixture.tools.map((_, index) =>
        toolFromFixture(agentId, fixture, index),
      );
  const liveOnlyTools = liveTools
    .filter((tool) => !tools.some((candidate) => candidate.id === tool.id))
    .map<ToolsRoomTool>((tool) => ({
      id: tool.id,
      name: tool.name,
      kind: tool.kind,
      description:
        tool.description ?? "Live cp-api binding awaiting safety review.",
      source: tool.source ?? "cp-api tool binding",
      owner: "Workspace builder",
      objectState: "draft",
      trust: "watching",
      sideEffect: "read",
      authMode: "mock",
      secretRef: "No secret attached",
      kmsKeyRef: "workspace/ws_acme/tenant_kms_key_id",
      usage7d: 0,
      failureRate: 0,
      costPer1kUsd: 0,
      evalCoveragePercent: 0,
      evalConfidence: "unsupported",
      successRatePercent: 0,
      p95LatencyMs: 0,
      retryRatePercent: 0,
      failedCalls7d: 0,
      piiSent7d: 0,
      lastSchemaChangeAt: "Not reviewed",
      environment: "draft",
      dataClassification: "Unclassified",
      idempotency: "Review required",
      allowedChannels: [],
      approvalRequirements: "Review required",
      auditRequirements: "Review required",
      compensationBehavior: "Review required",
      timeoutMs: 1_000,
      retryPolicy: "Review required before retry policy is active.",
      rateLimit: "Review required",
      mockStatus: "Draft mock required before evals can run.",
      liveStatus: "Live disabled until safety contract is complete.",
      productionGrant: "review",
      productionBoundary:
        "Production grant unavailable until schema and auth are reviewed.",
      productionNextStep: "Complete safety contract and save a mock response.",
      schema: [],
      outputSchema: [],
      sampleCall: "No sample call captured yet.",
      mockResponse: "{}",
      safety: {
        mutatesData: false,
        spendsMoney: false,
        exposesPersonalData: false,
        agentsAllowed: [agentId],
        sensitiveArguments: [],
        failureMode: "Tool is draft-only.",
        auditEvent: "tool.draft.review",
        evidence: "cp-api live binding draft",
      },
      evidence: ["cp-api live binding draft"],
    }));

  return {
    agentId,
    agentName,
    branch: usesLiveData ? "cp-api tool bindings" : fixture.workspace.branch,
    objectState: usesLiveData ? "draft" : fixture.workspace.objectState,
    trust: usesLiveData ? "watching" : fixture.workspace.trust,
    tools: [...tools, ...liveOnlyTools],
    toolContracts:
      toolContracts.length > 0
        ? toolContracts
        : localToolContracts(
            agentId,
            [...tools, ...liveOnlyTools].map((tool) => tool.id),
          ),
    catalogEvidence:
      usesLiveData
        ? "Loaded from live cp-api tool bindings."
        : "Explicit local fixture tool catalog for tests and demos.",
    degradedReason,
  };
}

export function createEmptyToolsRoomData(
  agentId = "agent_empty",
  degradedReason =
    "No tools are bound yet. Paste a curl command, OpenAPI fragment, or Postman sample to draft one.",
): ToolsRoomData {
  return {
    agentId,
    agentName: `Agent ${agentId}`,
    branch: "No branch loaded",
    objectState: "draft",
    trust: "degraded",
    tools: [],
    toolContracts: [],
    catalogEvidence: "No live tool bindings loaded.",
    degradedReason,
  };
}

export function draftToolFromRequest(
  input: string,
  source: ToolDraftSource = "curl",
): ToolDraft {
  const method = methodFromCurl(input);
  const url = urlFromRequest(input);
  const sideEffect = sideEffectFor(method, url);
  const schema = schemaFromRequest(input);
  const toolName = url.replace(/^https?:\/\//, "").split(/[/?#]/)[0] ?? "tool";
  const authNeeds = /authorization:|api-key|x-api-key/i.test(input)
    ? [
        "Authorization header detected; value redacted and stored as a per-agent Vault secret.",
      ]
    : ["No auth header detected; review before live calls."];
  return {
    source,
    name: toolName.replace(/[^a-z0-9]+/gi, "_").toLowerCase(),
    method,
    url,
    authNeeds,
    sideEffect,
    schema,
    mockResponse:
      sideEffect === "read"
        ? '{"status":"mocked","source":"recorded_fixture"}'
        : '{"status":"mocked","requires_approval":true}',
    evalStub: `${method} ${url} should return a deterministic mock before live grant.`,
    productionBoundary:
      sideEffect === "money-movement" || sideEffect === "write"
        ? "Draft only. Production grant requires approval, eval coverage, audit event, rate limit, and secret review."
        : "Draft only. Production grant requires schema, auth, and mock review.",
    evidence: "local request parser; no secret values retained",
  };
}

export { DEFAULT_TOOL_IMPORT };
