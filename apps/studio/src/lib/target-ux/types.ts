import type {
  ConfidenceLevel,
  ObjectState,
  TrustState,
} from "@/lib/design-tokens";

export const CANONICAL_DOMAINS = [
  "agents",
  "traces",
  "tools",
  "memory",
  "evals",
  "migration",
  "deploys",
  "costs",
  "inbox",
  "enterprise",
  "snapshots",
  "scenes",
  "command",
] as const;

export type CanonicalDomain = (typeof CANONICAL_DOMAINS)[number];

export interface TargetWorkspace {
  id: string;
  name: string;
  region: string;
  environment: "dev" | "staging" | "production";
  branch: string;
  trust: TrustState;
  objectState: ObjectState;
  activeAgentId: string;
}

export interface TargetAgent {
  id: string;
  name: string;
  purpose: string;
  channel: "web" | "slack" | "voice" | "whatsapp" | "sms";
  objectState: ObjectState;
  trust: TrustState;
  evalPassRate: number;
  p95LatencyMs: number;
  costPerTurnUsd: number;
  nextBestAction: string;
}

export interface TargetTool {
  id: string;
  name: string;
  owner: string;
  sideEffect: "read" | "write" | "money-movement" | "external-message";
  authMode: "mock" | "oauth" | "secret" | "mcp";
  objectState: ObjectState;
  risk: "none" | "low" | "medium" | "high";
  usage7d: number;
}

export interface TargetTraceSpan {
  id: string;
  label: string;
  kind: "server" | "client" | "internal" | "producer" | "consumer";
  startedAtMs: number;
  durationMs: number;
  status: "ok" | "error" | "unset";
  evidence?: string;
}

export interface TargetTrace {
  id: string;
  agentId: string;
  title: string;
  version: string;
  snapshotId: string;
  confidence: ConfidenceLevel;
  trust: TrustState;
  spans: TargetTraceSpan[];
  replayAvailable: boolean;
}

export interface TargetMemoryFact {
  id: string;
  key: string;
  before: string;
  after: string;
  source: string;
  policy: string;
  risk: "none" | "pii" | "secret-like" | "conflict";
}

export interface TargetEvalSuite {
  id: string;
  name: string;
  coverage: string;
  passRate: number;
  regressionCount: number;
  lastRun: string;
  confidence: ConfidenceLevel;
}

export interface TargetMigration {
  id: string;
  source: "botpress" | "dialogflow" | "rasa" | "copilot-studio" | "custom";
  stage: "imported" | "mapped" | "parity" | "cutover" | "archived";
  parityScore: number;
  unmappedItems: number;
  verifiedFormat: boolean;
  lineageSnapshotId: string;
}

export interface TargetDeploy {
  id: string;
  agentId: string;
  objectState: ObjectState;
  canaryPercent: number;
  approvals: number;
  requiredApprovals: number;
  rollbackTarget: string;
  blockedReason?: string;
}

export interface TargetCostSlice {
  id: string;
  label: string;
  amountUsd: number;
  latencyMs: number;
  share: number;
  recommendation: string;
}

export interface TargetInboxItem {
  id: string;
  customer: string;
  channel: TargetAgent["channel"];
  severity: "low" | "medium" | "high" | "critical";
  summary: string;
  traceId: string;
  suggestedAction: string;
}

export interface TargetEnterpriseControl {
  id: string;
  name: string;
  posture: TrustState;
  evidence: string;
  owner: string;
}

export interface TargetSnapshot {
  id: string;
  name: string;
  agentId: string;
  version: string;
  createdAt: string;
  signed: boolean;
  objectState: ObjectState;
  summary: string;
}

export interface TargetScene {
  id: string;
  name: string;
  domain: string;
  source: "production" | "synthetic" | "migration";
  turns: number;
  evalLinked: boolean;
  summary: string;
}

export interface TargetCommand {
  id: string;
  label: string;
  intent: "navigate" | "create" | "review" | "simulate" | "deploy";
  shortcut?: string;
  domain: CanonicalDomain;
}

export interface TargetUXFixture {
  workspace: TargetWorkspace;
  agents: TargetAgent[];
  tools: TargetTool[];
  traces: TargetTrace[];
  memory: TargetMemoryFact[];
  evals: TargetEvalSuite[];
  migrations: TargetMigration[];
  deploys: TargetDeploy[];
  costs: TargetCostSlice[];
  inbox: TargetInboxItem[];
  enterprise: TargetEnterpriseControl[];
  snapshots: TargetSnapshot[];
  scenes: TargetScene[];
  commands: TargetCommand[];
}
