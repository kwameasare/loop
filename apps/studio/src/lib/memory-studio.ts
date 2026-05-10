import type {
  ConfidenceLevel,
  ObjectState,
  TrustState,
} from "@/lib/design-tokens";
import {
  listMemoryPolicies,
  localMemoryPolicies,
  type MemoryPolicy,
} from "@/lib/memory-policies";
import type { TargetUXFixture } from "@/lib/target-ux";

export type MemoryScope =
  | "session"
  | "user"
  | "account"
  | "organization"
  | "task"
  | "agent"
  | "episodic"
  | "scratch";
export type MemorySafetyFlag =
  | "none"
  | "pii"
  | "secret-like"
  | "secret_like_redacted"
  | "conflict"
  | "stale"
  | "weak-evidence"
  | "missing_source_trace";
export type MemoryReplayMode = "current" | "without-memory" | "historical";

export interface MemoryStudioEntry {
  id: string;
  scope: MemoryScope;
  key: string;
  before: string;
  after: string;
  source: string;
  sourceTrace: string;
  sourceTurnId: string;
  sourceSpanId: string;
  policyRef: string;
  retentionPolicy: string;
  lastWrite: string;
  writerVersion: string;
  confidence: ConfidenceLevel;
  safetyFlags: MemorySafetyFlag[];
  deletionState: "available" | "blocked" | "queued";
  deletionReason: string;
  replayImpact: string;
}

export interface MemoryReplayResult {
  mode: MemoryReplayMode;
  label: string;
  answerDelta: string;
  toolDelta: string;
  evidence: string;
}

export interface MemoryStudioData {
  agentId: string;
  agentName: string;
  branch: string;
  objectState: ObjectState;
  trust: TrustState;
  entries: MemoryStudioEntry[];
  policies: MemoryPolicy[];
  replayResults: MemoryReplayResult[];
  retentionEvidence: string;
  degradedReason?: string | undefined;
}

export interface MemoryStudioClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

interface CpMemoryEntry {
  id: string;
  scope:
    | "user"
    | "bot"
    | "session"
    | "account"
    | "organization"
    | "task"
    | "agent";
  key: string;
  before: string;
  after: string;
  source: string;
  source_trace: string;
  source_turn_id?: string | null;
  source_span_id?: string | null;
  policy_ref?: string | null;
  retention_policy: string;
  updated_at: string;
  writer_version: string;
  confidence: ConfidenceLevel;
  safety_flags: MemorySafetyFlag[];
  deletion_state: "available" | "blocked" | "queued";
  deletion_reason: string;
  replay_impact: string;
}

function cpApiBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("LOOP_CP_API_BASE_URL is required for memory calls");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function headers(opts: MemoryStudioClientOptions): Record<string, string> {
  const out: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) out.authorization = `Bearer ${token}`;
  return out;
}

function scopeFromCp(scope: CpMemoryEntry["scope"]): MemoryScope {
  if (scope === "session") return "session";
  if (scope === "account") return "account";
  if (scope === "organization") return "organization";
  if (scope === "task") return "task";
  if (scope === "agent" || scope === "bot") return "agent";
  return "user";
}

function normalizeMemoryEntry(item: CpMemoryEntry): MemoryStudioEntry {
  return {
    id: item.id,
    scope: scopeFromCp(item.scope),
    key: item.key,
    before: item.before,
    after: item.after,
    source: item.source,
    sourceTrace: item.source_trace ?? "",
    sourceTurnId: item.source_turn_id ?? "",
    sourceSpanId: item.source_span_id ?? "",
    policyRef: item.policy_ref ?? "",
    retentionPolicy: item.retention_policy,
    lastWrite: item.updated_at || "not recorded",
    writerVersion: item.writer_version,
    confidence: item.confidence,
    safetyFlags: item.safety_flags,
    deletionState: item.deletion_state,
    deletionReason: item.deletion_reason,
    replayImpact: item.replay_impact,
  };
}

export function createMemoryStudioDataFromEntries(
  agentId: string,
  entries: MemoryStudioEntry[],
  policies = localMemoryPolicies(agentId),
): MemoryStudioData {
  return {
    agentId,
    agentName: `Agent ${agentId}`,
    branch: "Memory store",
    objectState: "saved",
    trust: entries.length > 0 ? "watching" : "degraded",
    entries,
    policies,
    replayResults: [],
    retentionEvidence:
      policies.length > 0
        ? "Loaded from cp-api memory policy records."
        : "No retention policy records loaded from cp-api.",
    degradedReason:
      entries.length === 0
        ? "No memory writes have been captured yet. Replay a turn or run a simulator scenario to inspect memory."
        : undefined,
  };
}

export async function fetchMemoryStudioData(
  agentId: string,
  userId: string,
  opts: MemoryStudioClientOptions = {},
): Promise<MemoryStudioData> {
  const base = cpApiBaseUrl(opts.baseUrl);
  const fetcher = opts.fetcher ?? fetch;
  const params = new URLSearchParams({ user_id: userId });
  const memoryRequest = fetcher(
    `${base}/agents/${encodeURIComponent(agentId)}/memory?${params}`,
    {
      method: "GET",
      headers: headers(opts),
      cache: "no-store",
    },
  );
  const policyRequest = listMemoryPolicies(agentId, opts);
  const [response, policies] = await Promise.all([
    memoryRequest,
    policyRequest,
  ]);
  if (response.status === 404) {
    return createEmptyMemoryStudioData(agentId, policies.items);
  }
  if (!response.ok) {
    throw new Error(`cp-api GET agent memory -> ${response.status}`);
  }
  const body = (await response.json()) as { items?: CpMemoryEntry[] };
  return createMemoryStudioDataFromEntries(
    agentId,
    (body.items ?? []).map(normalizeMemoryEntry),
    policies.items,
  );
}

export async function deleteMemoryStudioEntry(
  agentId: string,
  entry: MemoryStudioEntry,
  userId: string,
  opts: MemoryStudioClientOptions = {},
): Promise<void> {
  if (entry.scope !== "user") {
    throw new Error("Only durable user memory can be deleted through cp-api");
  }
  const fetcher = opts.fetcher ?? fetch;
  const params = new URLSearchParams({ user_id: userId });
  const response = await fetcher(
    `${cpApiBaseUrl(opts.baseUrl)}/agents/${encodeURIComponent(
      agentId,
    )}/memory/user/${encodeURIComponent(entry.key)}?${params}`,
    {
      method: "DELETE",
      headers: headers(opts),
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error(`cp-api DELETE agent memory -> ${response.status}`);
  }
}

export function createMemoryStudioData(
  agentId: string,
  fixture: TargetUXFixture,
): MemoryStudioData {
  const agent =
    fixture.agents.find((candidate) => candidate.id === agentId) ??
    fixture.agents[0]!;
  const memory = fixture.memory[0]!;
  const trace = fixture.traces[0]!;
  const enterprise = fixture.enterprise[0]!;
  return {
    agentId,
    agentName: agent.name,
    branch: fixture.workspace.branch,
    objectState: fixture.workspace.objectState,
    trust: fixture.workspace.trust,
    retentionEvidence: `${enterprise.id}: ${enterprise.evidence}`,
    policies: localMemoryPolicies(agentId),
    entries: [
      {
        id: memory.id,
        scope: "user",
        key: memory.key,
        before: memory.before,
        after: memory.after,
        source: memory.source,
        sourceTrace: trace.id,
        sourceTurnId: "turn_3",
        sourceSpanId: "span_memory_write_preferred_language",
        policyRef: "mp_local_user",
        retentionPolicy: memory.policy,
        lastWrite: "2026-05-06T08:42:00Z",
        writerVersion: trace.version,
        confidence: "high",
        safetyFlags: ["none"],
        deletionState: "available",
        deletionReason: "User memory can be deleted with audit trail.",
        replayImpact:
          "With memory, the draft keeps language preference and avoids asking again.",
      },
      {
        id: "mem_refund_policy_context",
        scope: "task",
        key: "refund_policy_context",
        before: "refund_policy_2024.pdf ranked first",
        after: "refund_policy_2026.pdf ranked above refund_policy_2024.pdf",
        source: "Context assembled from policy retrieval",
        sourceTrace: trace.id,
        sourceTurnId: "turn_3",
        sourceSpanId: "span_retrieval_policy_context",
        policyRef: "mp_local_task",
        retentionPolicy: "episodic trace memory, 30 day retention",
        lastWrite: "2026-05-06T08:41:12Z",
        writerVersion: trace.version,
        confidence: "medium",
        safetyFlags: ["stale"],
        deletionState: "available",
        deletionReason: "Episodic memory can be pruned from this trace.",
        replayImpact:
          "Without this memory, cancellation answers may cite the archived policy first.",
      },
      {
        id: "mem_account_tier",
        scope: "account",
        key: "account_plan_tier",
        before: "unknown",
        after: "enterprise annual",
        source: "Account lookup result approved for account-scope memory",
        sourceTrace: trace.id,
        sourceTurnId: "turn_3",
        sourceSpanId: "span_tool_lookup_order",
        policyRef: "mp_local_account",
        retentionPolicy: "account memory, 90 day retention",
        lastWrite: "2026-05-06T08:42:20Z",
        writerVersion: trace.version,
        confidence: "medium",
        safetyFlags: ["none"],
        deletionState: "available",
        deletionReason:
          "Account memory can be deleted with tenant audit and replay impact.",
        replayImpact:
          "Without account memory, replies must call account lookup before plan-specific guidance.",
      },
      {
        id: "mem_org_escalation",
        scope: "organization",
        key: "escalation_contract_owner",
        before: "support_lead@acme.test",
        after: "enterprise_success@acme.test",
        source: "Approved organization routing policy",
        sourceTrace: "trace_refund_742#policy_resolution",
        sourceTurnId: "turn_4",
        sourceSpanId: "span_policy_resolution",
        policyRef: "mp_local_organization",
        retentionPolicy: "organization memory, policy-bound retention",
        lastWrite: "2026-05-06T08:43:03Z",
        writerVersion: trace.version,
        confidence: "high",
        safetyFlags: ["none"],
        deletionState: "available",
        deletionReason:
          "Organization routing memory can be reverted through policy change.",
        replayImpact:
          "Historical replay routes contract escalations to the previous owner.",
      },
      {
        id: "mem_scratch_order",
        scope: "scratch",
        key: "active_order_lookup",
        before: "none",
        after: "lookup_order result staged for this turn only",
        source: "span_tool lookup_order",
        sourceTrace: trace.id,
        sourceTurnId: "turn_3",
        sourceSpanId: "span_tool_lookup_order",
        policyRef: "mp_local_scratch",
        retentionPolicy: "scratch memory, expires at turn end",
        lastWrite: "2026-05-06T08:41:31Z",
        writerVersion: trace.version,
        confidence: "high",
        safetyFlags: ["none"],
        deletionState: "blocked",
        deletionReason:
          "Scratch state expires automatically; no durable delete needed.",
        replayImpact:
          "Clearing scratch memory forces the replay to call lookup_order again.",
      },
      {
        id: "mem_payment_hint",
        scope: "session",
        key: "payment_hint",
        before: "none",
        after: "[redacted secret-like value]",
        source: "Rejected memory write from customer text",
        sourceTrace: trace.id,
        sourceTurnId: "turn_3",
        sourceSpanId: "span_memory_blocked_payment_hint",
        policyRef: "mp_local_session",
        retentionPolicy: "session memory blocked by PII and secret policy",
        lastWrite: "2026-05-06T08:41:52Z",
        writerVersion: trace.version,
        confidence: "unsupported",
        safetyFlags: ["pii", "secret-like", "weak-evidence"],
        deletionState: "queued",
        deletionReason:
          "Queued for review because the write was rejected before durable storage.",
        replayImpact:
          "Replay without memory confirms the answer does not depend on the rejected value.",
      },
      {
        id: "mem_agent_guardrail",
        scope: "agent",
        key: "refund_exception_guardrail",
        before: "per-call cap only",
        after: "cumulative cap across conversation",
        source: "Catch resolution accepted by builder",
        sourceTrace: "catch/cumulative_refund_cap",
        sourceTurnId: "catch_1",
        sourceSpanId: "span_catch_resolution",
        policyRef: "mp_local_agent",
        retentionPolicy: "agent memory, version-bound retention",
        lastWrite: "2026-05-06T08:45:10Z",
        writerVersion: "v23.1.4-draft",
        confidence: "high",
        safetyFlags: ["none"],
        deletionState: "available",
        deletionReason:
          "Agent memory can be superseded by a new accepted behavior version.",
        replayImpact:
          "Without agent memory, replay may approve multiple refunds below per-call cap.",
      },
      {
        id: "mem_conflict_language",
        scope: "user",
        key: "preferred_language",
        before: "English",
        after: "Spanish",
        source: "Weak evidence from translated paraphrase",
        sourceTrace: "trace_refund_742#turn_8",
        sourceTurnId: "turn_8",
        sourceSpanId: "span_memory_candidate_language",
        policyRef: "mp_local_user",
        retentionPolicy:
          "durable user preference requires explicit confirmation",
        lastWrite: "2026-05-06T08:44:00Z",
        writerVersion: "v23.1.4-draft",
        confidence: "low",
        safetyFlags: ["conflict", "weak-evidence"],
        deletionState: "available",
        deletionReason: "Conflicting user memory can be deleted or reverted.",
        replayImpact:
          "Historical replay shows the answer should ask for confirmation before switching language.",
      },
    ],
    replayResults: [
      {
        mode: "current",
        label: "Replay with current memory",
        answerDelta:
          "Answer keeps English preference and cites the May 2026 refund policy.",
        toolDelta: "Uses cached preference plus lookup_order.",
        evidence: `${trace.id}; ${memory.id}`,
      },
      {
        mode: "without-memory",
        label: "Replay without memory",
        answerDelta:
          "Answer asks for language preference again and still cites the policy.",
        toolDelta: "Forces lookup_order and retrieval; no durable memory read.",
        evidence: "replay turn=3 with-memory=cleared",
      },
      {
        mode: "historical",
        label: "Replay with historical memory",
        answerDelta:
          "Answer reproduces v23.1.4 behavior before the policy ranking change.",
        toolDelta: "Uses snap_refund_may historical memory snapshot.",
        evidence: "snap_refund_may; trace_refund_742",
      },
    ],
  };
}

export function createEmptyMemoryStudioData(
  agentId = "agent_empty",
  policies: MemoryPolicy[] = [],
): MemoryStudioData {
  return {
    agentId,
    agentName: `Agent ${agentId}`,
    branch: "No branch loaded",
    objectState: "draft",
    trust: "degraded",
    entries: [],
    policies,
    replayResults: [],
    retentionEvidence:
      policies.length > 0
        ? "Loaded memory policy records from cp-api; no memory writes found."
        : "No memory store or policy records loaded from cp-api.",
    degradedReason:
      "No memory writes have been captured yet. Replay a turn or run a simulator scenario to inspect memory.",
  };
}

export function createDegradedMemoryStudioData(
  agentId: string,
  reason: string,
  policies: MemoryPolicy[] = [],
): MemoryStudioData {
  const data = createEmptyMemoryStudioData(agentId, policies);
  return {
    ...data,
    retentionEvidence: reason,
    degradedReason: reason,
  };
}
