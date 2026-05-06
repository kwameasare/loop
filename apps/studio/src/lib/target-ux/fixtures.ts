import type {
  CanonicalDomain,
  TargetAgent,
  TargetCommand,
  TargetCostSlice,
  TargetDeploy,
  TargetEnterpriseControl,
  TargetEvalSuite,
  TargetInboxItem,
  TargetMemoryFact,
  TargetMigration,
  TargetScene,
  TargetSnapshot,
  TargetTool,
  TargetTrace,
  TargetUXFixture,
  TargetWorkspace,
} from "./types";

export const targetWorkspace: TargetWorkspace = {
  id: "ws_acme",
  name: "Acme Support Ops",
  region: "us-east-1",
  environment: "dev",
  branch: "draft/refund-clarity",
  trust: "watching",
  objectState: "draft",
  activeAgentId: "agent_support",
};

export const targetAgents: TargetAgent[] = [
  {
    id: "agent_support",
    name: "Acme Support Concierge",
    purpose: "Resolve order, refund, and escalation questions across chat and voice.",
    channel: "web",
    objectState: "canary",
    trust: "watching",
    evalPassRate: 96,
    p95LatencyMs: 1180,
    costPerTurnUsd: 0.043,
    nextBestAction: "Replay last week's refund escalations against the draft.",
  },
  {
    id: "agent_voice",
    name: "Voice Receptionist",
    purpose: "Qualify callers, route urgent issues, and create follow-up tasks.",
    channel: "voice",
    objectState: "staged",
    trust: "healthy",
    evalPassRate: 94,
    p95LatencyMs: 820,
    costPerTurnUsd: 0.058,
    nextBestAction: "Approve the phone handoff eval suite before canary.",
  },
];

export const targetTools: TargetTool[] = [
  {
    id: "tool_lookup_order",
    name: "lookup_order",
    owner: "Platform Integrations",
    sideEffect: "read",
    authMode: "mcp",
    objectState: "production",
    risk: "low",
    usage7d: 18342,
  },
  {
    id: "tool_issue_refund",
    name: "issue_refund",
    owner: "Revenue Operations",
    sideEffect: "money-movement",
    authMode: "secret",
    objectState: "staged",
    risk: "high",
    usage7d: 612,
  },
];

export const targetTraces: TargetTrace[] = [
  {
    id: "trace_refund_742",
    agentId: "agent_support",
    title: "Customer asks to cancel an annual renewal",
    version: "v23.1.4",
    snapshotId: "snap_refund_may",
    confidence: "medium",
    trust: "watching",
    replayAvailable: true,
    spans: [
      {
        id: "span_context",
        label: "Context assembled",
        kind: "server",
        startedAtMs: 0,
        durationMs: 112,
        status: "ok",
        evidence: "refund_policy_2026.pdf ranked above refund_policy_2024.pdf",
      },
      {
        id: "span_tool",
        label: "lookup_order",
        kind: "client",
        startedAtMs: 135,
        durationMs: 243,
        status: "ok",
      },
      {
        id: "span_answer",
        label: "Grounded answer",
        kind: "internal",
        startedAtMs: 410,
        durationMs: 620,
        status: "ok",
      },
    ],
  },
];

export const targetMemory: TargetMemoryFact[] = [
  {
    id: "mem_language",
    key: "preferred_language",
    before: "unknown",
    after: "English",
    source: "User said English is fine",
    policy: "durable user preference",
    risk: "none",
  },
];

export const targetEvals: TargetEvalSuite[] = [
  {
    id: "eval_refunds",
    name: "Refund and cancellation parity",
    coverage: "Production replay plus Botpress import parity",
    passRate: 96,
    regressionCount: 1,
    lastRun: "2026-05-06T08:30:00Z",
    confidence: "medium",
  },
];

export const targetMigrations: TargetMigration[] = [
  {
    id: "migration_botpress_acme",
    source: "botpress",
    stage: "parity",
    parityScore: 95,
    unmappedItems: 3,
    verifiedFormat: true,
    lineageSnapshotId: "snap_botpress_import",
  },
];

export const targetDeploys: TargetDeploy[] = [
  {
    id: "deploy_refund_canary",
    agentId: "agent_support",
    objectState: "canary",
    canaryPercent: 12,
    approvals: 1,
    requiredApprovals: 2,
    rollbackTarget: "v23.1.3",
    blockedReason: "One refund-window eval regressed under Spanish paraphrase.",
  },
];

export const targetCosts: TargetCostSlice[] = [
  {
    id: "cost_llm",
    label: "LLM reasoning",
    amountUsd: 1284.24,
    latencyMs: 620,
    share: 46,
    recommendation: "Cache low-risk refund policy context for repeat turns.",
  },
  {
    id: "cost_tools",
    label: "Tool calls",
    amountUsd: 338.72,
    latencyMs: 243,
    share: 18,
    recommendation: "Batch order lookup and entitlement lookup in preview.",
  },
];

export const targetInbox: TargetInboxItem[] = [
  {
    id: "inbox_legal_threat",
    customer: "J. Morgan",
    channel: "web",
    severity: "high",
    summary: "Customer disputes renewal charge and mentions legal review.",
    traceId: "trace_refund_742",
    suggestedAction: "Escalate to retention policy owner with trace and replay diff.",
  },
];

export const targetEnterprise: TargetEnterpriseControl[] = [
  {
    id: "control_pii",
    name: "No secret or payment data in durable memory",
    posture: "healthy",
    evidence: "Last 1,240 memory writes checked; zero policy violations.",
    owner: "Security",
  },
];

export const targetSnapshots: TargetSnapshot[] = [
  {
    id: "snap_refund_may",
    name: "Refund agent before May policy cutover",
    agentId: "agent_support",
    version: "v23.1.4",
    createdAt: "2026-05-06T08:15:00Z",
    signed: true,
    objectState: "saved",
    summary: "Prompts, tools, KB, memory rules, evals, and deploy state frozen.",
  },
];

export const targetScenes: TargetScene[] = [
  {
    id: "scene_escalation_legal_threat",
    name: "Escalation: legal threat during cancellation",
    domain: "refunds",
    source: "production",
    turns: 9,
    evalLinked: true,
    summary: "Canonical conversation for refund refusal, policy citation, and handoff.",
  },
];

export const targetCommands: TargetCommand[] = [
  {
    id: "cmd_replay_future",
    label: "Replay selected production turns against draft",
    intent: "simulate",
    shortcut: "R",
    domain: "traces",
  },
  {
    id: "cmd_promote_canary",
    label: "Open canary preflight",
    intent: "deploy",
    shortcut: "P",
    domain: "deploys",
  },
];

export const targetUxFixtures: TargetUXFixture = {
  workspace: targetWorkspace,
  agents: targetAgents,
  tools: targetTools,
  traces: targetTraces,
  memory: targetMemory,
  evals: targetEvals,
  migrations: targetMigrations,
  deploys: targetDeploys,
  costs: targetCosts,
  inbox: targetInbox,
  enterprise: targetEnterprise,
  snapshots: targetSnapshots,
  scenes: targetScenes,
  commands: targetCommands,
};

export function buildTargetUxFixture(
  overrides: Partial<TargetUXFixture> = {},
): TargetUXFixture {
  return {
    ...targetUxFixtures,
    ...overrides,
  };
}

export function fixtureDomainCoverage(
  fixture: TargetUXFixture = targetUxFixtures,
): Record<CanonicalDomain, boolean> {
  return {
    agents: fixture.agents.length > 0,
    traces: fixture.traces.length > 0,
    tools: fixture.tools.length > 0,
    memory: fixture.memory.length > 0,
    evals: fixture.evals.length > 0,
    migration: fixture.migrations.length > 0,
    deploys: fixture.deploys.length > 0,
    costs: fixture.costs.length > 0,
    inbox: fixture.inbox.length > 0,
    enterprise: fixture.enterprise.length > 0,
    snapshots: fixture.snapshots.length > 0,
    scenes: fixture.scenes.length > 0,
    command: fixture.commands.length > 0,
  };
}
