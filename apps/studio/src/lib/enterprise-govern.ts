/**
 * Enterprise governance overview model.
 *
 * Backs the `/enterprise/govern` page. Canonical target §23
 * (governance + policy) and §24 (enterprise). The existing SSO and
 * audit-log surfaces stay where they are; this module fills the
 * remaining UX306 AC clauses: RBAC matrix, approvals, data residency,
 * BYOK, whitelabel, procurement evidence, private skill library,
 * policy/audit consequences.
 *
 * The Compliance Reviewer model is now cp-api wired; the remaining constants
 * still provide deterministic offline defaults for local Studio previews.
 */

import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

// ---------------------------------------------------------------------------
// SSO / SCIM connection summary
// ---------------------------------------------------------------------------

export type SsoStatus = "configured" | "pending" | "not_configured";

export interface SsoSummary {
  protocol: "saml" | "oidc" | "scim";
  label: string;
  status: SsoStatus;
  detail: string;
  evidenceRef: string;
}

export const SSO_SUMMARIES: readonly SsoSummary[] = [
  {
    protocol: "saml",
    label: "SAML SSO",
    status: "configured",
    detail: "EntraID · ACS round-trip last verified 4d ago",
    evidenceRef: "audit/sso-saml#last-verify",
  },
  {
    protocol: "oidc",
    label: "OIDC SSO",
    status: "not_configured",
    detail: "No OIDC IdP connected.",
    evidenceRef: "audit/sso-oidc",
  },
  {
    protocol: "scim",
    label: "SCIM provisioning",
    status: "configured",
    detail: "12 users / 4 groups synced; last bridge tick 11m ago.",
    evidenceRef: "audit/scim#last-tick",
  },
] as const;

// ---------------------------------------------------------------------------
// RBAC matrix (roles × resource-actions)
// ---------------------------------------------------------------------------

export type RbacRole =
  | "viewer"
  | "operator"
  | "builder"
  | "approver"
  | "admin"
  | "auditor";

export type RbacResource =
  | "agents"
  | "deploys"
  | "evals"
  | "knowledge"
  | "billing"
  | "members"
  | "audit";

export type RbacAction = "view" | "edit" | "approve" | "destroy" | "export";

export interface RbacCell {
  role: RbacRole;
  resource: RbacResource;
  action: RbacAction;
  allowed: boolean;
}

export const RBAC_ROLES: readonly RbacRole[] = [
  "viewer",
  "operator",
  "builder",
  "approver",
  "admin",
  "auditor",
] as const;

export const RBAC_RESOURCES: readonly RbacResource[] = [
  "agents",
  "deploys",
  "evals",
  "knowledge",
  "billing",
  "members",
  "audit",
] as const;

const ROLE_TEMPLATES: Record<
  RbacRole,
  Partial<Record<RbacResource, RbacAction[]>>
> = {
  viewer: {
    agents: ["view"],
    deploys: ["view"],
    evals: ["view"],
    knowledge: ["view"],
    audit: ["view"],
  },
  operator: {
    agents: ["view"],
    deploys: ["view"],
    evals: ["view"],
    knowledge: ["view"],
    audit: ["view"],
  },
  builder: {
    agents: ["view", "edit"],
    deploys: ["view"],
    evals: ["view", "edit"],
    knowledge: ["view", "edit"],
  },
  approver: {
    agents: ["view"],
    deploys: ["view", "approve"],
    evals: ["view"],
    knowledge: ["view"],
    members: ["view"],
  },
  admin: {
    agents: ["view", "edit", "destroy"],
    deploys: ["view", "approve"],
    evals: ["view", "edit", "destroy"],
    knowledge: ["view", "edit", "destroy"],
    billing: ["view", "edit"],
    members: ["view", "edit", "destroy"],
    audit: ["view", "export"],
  },
  auditor: {
    agents: ["view"],
    deploys: ["view"],
    evals: ["view"],
    knowledge: ["view"],
    billing: ["view"],
    members: ["view"],
    audit: ["view", "export"],
  },
};

export function rbacAllowed(
  role: RbacRole,
  resource: RbacResource,
  action: RbacAction,
): boolean {
  return ROLE_TEMPLATES[role][resource]?.includes(action) ?? false;
}

export function buildRbacMatrix(): readonly RbacCell[] {
  const cells: RbacCell[] = [];
  const actions: RbacAction[] = [
    "view",
    "edit",
    "approve",
    "destroy",
    "export",
  ];
  for (const role of RBAC_ROLES) {
    for (const resource of RBAC_RESOURCES) {
      for (const action of actions) {
        cells.push({
          role,
          resource,
          action,
          allowed: rbacAllowed(role, resource, action),
        });
      }
    }
  }
  return cells;
}

// ---------------------------------------------------------------------------
// Approvals: governance gates (separate from deploy gates).
// ---------------------------------------------------------------------------

export type ApprovalKind =
  | "high_cost_action"
  | "data_export"
  | "production_deploy"
  | "external_share"
  | "billing_change";

export type ApprovalState = "pending" | "approved" | "rejected" | "expired";

export interface ApprovalRequest {
  id: string;
  kind: ApprovalKind;
  subject: string;
  requester: string;
  approvers: readonly string[];
  state: ApprovalState;
  ageMinutes: number;
  evidenceRef: string;
}

export const APPROVAL_REQUESTS: readonly ApprovalRequest[] = [
  {
    id: "apr_1",
    kind: "production_deploy",
    subject: "Promote refunds-bot v34 → production",
    requester: "lina@acme",
    approvers: ["lead@acme", "sre@acme"],
    state: "pending",
    ageMinutes: 7,
    evidenceRef: "audit/approval/apr_1",
  },
  {
    id: "apr_2",
    kind: "data_export",
    subject: "Export Q3 audit log to CSV",
    requester: "sec@acme",
    approvers: ["compliance@acme"],
    state: "approved",
    ageMinutes: 42,
    evidenceRef: "audit/approval/apr_2",
  },
  {
    id: "apr_3",
    kind: "external_share",
    subject: "Share refunds-bot eval suite with vendor",
    requester: "kai@acme",
    approvers: ["lead@acme"],
    state: "rejected",
    ageMinutes: 64,
    evidenceRef: "audit/approval/apr_3",
  },
  {
    id: "apr_4",
    kind: "high_cost_action",
    subject: "Re-run nightly evals with GPT-4 ($120 est.)",
    requester: "ops@acme",
    approvers: ["finance@acme"],
    state: "expired",
    ageMinutes: 4320,
    evidenceRef: "audit/approval/apr_4",
  },
] as const;

export function pendingApprovals(
  rs: readonly ApprovalRequest[],
): readonly ApprovalRequest[] {
  return rs.filter((r) => r.state === "pending");
}

// ---------------------------------------------------------------------------
// Audit explorer fixture (separate from existing audit-log-page).
// ---------------------------------------------------------------------------

export type AuditCategory =
  | "auth"
  | "rbac"
  | "deploy"
  | "policy"
  | "data"
  | "billing";

export interface AuditEvent {
  id: string;
  ts: string;
  actor: string;
  category: AuditCategory;
  action: string;
  target: string;
  evidenceRef: string;
}

export const AUDIT_EVENTS: readonly AuditEvent[] = [
  {
    id: "ev_1001",
    ts: "2025-02-21T09:14:22Z",
    actor: "lina@acme",
    category: "deploy",
    action: "promote.requested",
    target: "agents/refunds-bot",
    evidenceRef: "audit/ev_1001",
  },
  {
    id: "ev_1002",
    ts: "2025-02-21T09:14:30Z",
    actor: "lead@acme",
    category: "rbac",
    action: "approval.granted",
    target: "approvals/apr_1",
    evidenceRef: "audit/ev_1002",
  },
  {
    id: "ev_1003",
    ts: "2025-02-21T09:18:01Z",
    actor: "sec@acme",
    category: "data",
    action: "export.requested",
    target: "audit-log/Q3",
    evidenceRef: "audit/ev_1003",
  },
  {
    id: "ev_1004",
    ts: "2025-02-21T09:21:47Z",
    actor: "ops@acme",
    category: "policy",
    action: "policy.violation",
    target: "agents/refunds-bot · refund>$200",
    evidenceRef: "audit/ev_1004",
  },
  {
    id: "ev_1005",
    ts: "2025-02-21T09:25:12Z",
    actor: "system",
    category: "auth",
    action: "scim.sync",
    target: "12 users / 4 groups",
    evidenceRef: "audit/ev_1005",
  },
] as const;

export function filterAudit(
  events: readonly AuditEvent[],
  filter: { category?: AuditCategory; actor?: string },
): readonly AuditEvent[] {
  return events.filter((e) => {
    if (filter.category && e.category !== filter.category) return false;
    if (filter.actor && !e.actor.includes(filter.actor)) return false;
    return true;
  });
}

// ---------------------------------------------------------------------------
// Compliance Reviewer workspace model
// ---------------------------------------------------------------------------

export type ComplianceRiskClass = "low" | "medium" | "high" | "critical";

export interface ComplianceReviewSummary {
  agents: number;
  pending_approvals: number;
  policy_violations: number;
  tool_reviews: number;
  memory_reviews: number;
  channel_blockers: number;
  open_incidents: number;
  policy_conflicts: number;
  data_access_changes: number;
  stale_risk_reviews: number;
}

export interface ComplianceApprovalQueueItem {
  id: string;
  agent_id: string;
  agent_name: string;
  change_package_id: string;
  subject: string;
  role: string;
  state: string;
  risk_class: ComplianceRiskClass;
  reason: string;
  content_hash: string;
  evidence_ref: string;
}

export interface CompliancePolicyViolation {
  id: string;
  title: string;
  severity: ComplianceRiskClass | "medium";
  target: string;
  status: string;
  evidence_ref: string;
}

export interface CompliancePolicyConflict {
  id: string;
  agent_id: string;
  agent_name: string;
  severity: ComplianceRiskClass | "medium";
  policy: string;
  summary: string;
  reviewer_action: string;
  evidence_ref: string;
}

export interface ComplianceDataAccessChange {
  id: string;
  agent_id: string;
  agent_name: string;
  surface: "tool" | "memory" | string;
  target: string;
  access: string[];
  state: string;
  reviewer_action: string;
  evidence_ref: string;
}

export interface ComplianceStaleRiskReview {
  id: string;
  agent_id: string;
  agent_name: string;
  change_package_id: string;
  severity: ComplianceRiskClass | "medium";
  summary: string;
  reviewer_action: string;
  evidence_ref: string;
}

export interface ComplianceReviewJob {
  id: string;
  status: "available" | "action_required" | "ready" | "clear" | string;
  output_count: number;
  reviewer_action: string;
  evidence_ref: string;
}

export interface ComplianceToolGrant {
  id: string;
  agent_id: string;
  agent_name: string;
  tool_id: string;
  name: string;
  side_effect_level: string;
  pii_access: boolean;
  money_movement: boolean;
  sandbox_status: string;
  live_status: string;
  reviewer_action: string;
  content_hash: string;
  evidence_ref: string;
}

export interface ComplianceMemoryPolicy {
  id: string;
  agent_id: string;
  agent_name: string;
  scope: string;
  allowed_memory_types: string[];
  retention: string;
  consent_requirement: string;
  pii_policy: string;
  delete_behavior: string;
  approval_status: string;
  reviewer_action: string;
  content_hash: string;
  evidence_ref: string;
}

export interface ComplianceChannelReadiness {
  id: string;
  agent_id: string;
  agent_name: string;
  channel_type: string;
  provider: string;
  status: string;
  blocking_checks: Array<{
    id: string;
    label: string;
    status: string;
    evidence_ref: string;
    message: string;
  }>;
  reviewer_action: string;
  evidence_ref: string;
}

export interface ComplianceIncident {
  id: string;
  agent_id: string;
  agent_name: string;
  severity: string;
  status: string;
  trigger: string;
  affected_conversation_count: number;
  rollback_action_ref: string;
  candidate_eval_suite_id: string | null;
  evidence_ref: string;
}

export interface ComplianceAuditEvent {
  id: string;
  occurred_at: string;
  actor_sub: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  payload_hash: string | null;
  outcome: string;
  evidence_ref: string;
}

export interface ComplianceProbeLibrary {
  id: string;
  name: string;
  required_for: string[];
  status: string;
  case_count: number;
  metrics: string[];
  evidence_ref: string;
}

export interface ComplianceReviewModel {
  workspace_id: string;
  generated_at: string;
  summary: ComplianceReviewSummary;
  /**
   * SSO/SCIM evidence supplied by cp-api. If omitted, Studio must show the
   * governance SSO tab as unavailable rather than rendering local fixture
   * connection claims.
   */
  sso_summaries?: SsoSummary[];
  approval_queue: ComplianceApprovalQueueItem[];
  policy_violations: CompliancePolicyViolation[];
  policy_conflicts: CompliancePolicyConflict[];
  data_access_changes: ComplianceDataAccessChange[];
  stale_risk_reviews: ComplianceStaleRiskReview[];
  review_jobs: ComplianceReviewJob[];
  tool_grants: ComplianceToolGrant[];
  memory_policies: ComplianceMemoryPolicy[];
  channel_readiness: ComplianceChannelReadiness[];
  incidents: ComplianceIncident[];
  audit_events: ComplianceAuditEvent[];
  industry_probe_libraries: ComplianceProbeLibrary[];
}

export interface ComplianceEvidenceExportInput {
  agent_id?: string;
  format?: "json" | "pdf" | "csv";
  include_sections?: string[];
}

export interface ComplianceEvidenceExport {
  id: string;
  workspace_id: string;
  agent_id: string | null;
  format: "json" | "pdf" | "csv";
  status: "ready";
  sections: string[];
  artifact_refs: string[];
  summary: ComplianceReviewSummary;
  download_url: string;
  generated_by: string;
  generated_at: string;
}

export interface ComplianceProbeSuiteAttachInput {
  agent_id?: string;
}

export interface ComplianceProbeSuiteCase {
  id: string;
  suite_id: string;
  workspace_id: string;
  name: string;
  input: Record<string, unknown>;
  expected: Record<string, unknown>;
  scorers: Array<Record<string, unknown>>;
  source: string;
  source_ref: string;
  attachments: string[];
  created_at: string;
  created_by: string;
}

export interface ComplianceProbeSuiteSummary {
  id: string;
  workspace_id: string;
  name: string;
  dataset_ref: string;
  metrics: string[];
  created_at: string;
  created_by: string;
}

export interface ComplianceProbeSuiteAttachedAgent {
  agent_id: string;
  agent_name: string;
  suite: ComplianceProbeSuiteSummary;
  cases_added: ComplianceProbeSuiteCase[];
  cases_existing: number;
  evidence_ref: string;
}

export interface ComplianceProbeSuiteAttachResult {
  library_id: string;
  library_name: string;
  status: "attached" | "no_recommended_agents";
  attached_agents: ComplianceProbeSuiteAttachedAgent[];
  suite_count: number;
  case_count: number;
  audit_ref: string;
}

type EnterpriseGovernMutationOptions = UxWireupClientOptions & {
  allowFixture?: boolean;
};

type ComplianceReviewClientOptions = UxWireupClientOptions & {
  allowFixture?: boolean;
};

export const COMPLIANCE_REVIEW_FIXTURE: ComplianceReviewModel = {
  workspace_id: "workspace_local",
  generated_at: new Date(0).toISOString(),
  sso_summaries: [...SSO_SUMMARIES],
  summary: {
    agents: 1,
    pending_approvals: 2,
    policy_violations: 1,
    tool_reviews: 1,
    memory_reviews: 1,
    channel_blockers: 1,
    open_incidents: 1,
    policy_conflicts: 3,
    data_access_changes: 2,
    stale_risk_reviews: 0,
  },
  approval_queue: [
    {
      id: "cp_refund:compliance",
      agent_id: "agent_support",
      agent_name: "Support Concierge",
      change_package_id: "cp_refund",
      subject: "Allow production refund automation.",
      role: "Compliance reviewer",
      state: "requested",
      risk_class: "high",
      reason: "Required for production or unaccepted commitment changes.",
      content_hash: "hash_refund",
      evidence_ref: "change-package/cp_refund",
    },
  ],
  policy_violations: [
    {
      id: "audit_policy_1",
      title: "policy.violation",
      severity: "high",
      target: "agents/support-concierge refund>$500",
      status: "success",
      evidence_ref: "audit/audit_policy_1",
    },
  ],
  policy_conflicts: [
    {
      id: "tc_refund:missing-budget-cap",
      agent_id: "agent_support",
      agent_name: "Support Concierge",
      severity: "high",
      policy: "money_movement_requires_budget_caps",
      summary: "Refund payment can move money but has no budget cap.",
      reviewer_action:
        "Block live use until per-action and per-turn caps are explicit.",
      evidence_ref: "tool-contract/tc_refund",
    },
  ],
  data_access_changes: [
    {
      id: "tool-access:tc_refund",
      agent_id: "agent_support",
      agent_name: "Support Concierge",
      surface: "tool",
      target: "Refund payment",
      access: ["PII", "money movement"],
      state: "blocked",
      reviewer_action:
        "Block live use until budget caps, owners, and compensation behavior are fixed.",
      evidence_ref: "tool-contract/tc_refund",
    },
    {
      id: "memory-access:mp_user",
      agent_id: "agent_support",
      agent_name: "Support Concierge",
      surface: "memory",
      target: "user memory",
      access: ["customer_preference"],
      state: "review_required",
      reviewer_action: "Review privacy implications before activation.",
      evidence_ref: "memory-policy/mp_user",
    },
  ],
  stale_risk_reviews: [],
  review_jobs: [
    {
      id: "detect_policy_conflicts",
      status: "action_required",
      output_count: 3,
      reviewer_action:
        "Resolve high and medium policy conflicts before production approval.",
      evidence_ref: "compliance-review/policy-conflicts",
    },
    {
      id: "summarize_data_access_changes",
      status: "ready",
      output_count: 2,
      reviewer_action:
        "Review PII, memory, and money movement access changes across agents.",
      evidence_ref: "compliance-review/data-access",
    },
  ],
  tool_grants: [
    {
      id: "tc_refund",
      agent_id: "agent_support",
      agent_name: "Support Concierge",
      tool_id: "refund_payment",
      name: "Refund payment",
      side_effect_level: "money_movement",
      pii_access: true,
      money_movement: true,
      sandbox_status: "sandbox",
      live_status: "blocked",
      reviewer_action:
        "Block live use until budget caps, owners, and compensation behavior are fixed.",
      content_hash: "hash_tool_refund",
      evidence_ref: "tool-contract/tc_refund",
    },
  ],
  memory_policies: [
    {
      id: "mp_user",
      agent_id: "agent_support",
      agent_name: "Support Concierge",
      scope: "user",
      allowed_memory_types: ["customer_preference"],
      retention: "Retain for 90 days.",
      consent_requirement: "Ask before storing support preferences.",
      pii_policy: "May include personal support preferences.",
      delete_behavior: "Delete on user request with audit trail.",
      approval_status: "review_required",
      reviewer_action: "Review privacy implications before activation.",
      content_hash: "hash_memory_user",
      evidence_ref: "memory-policy/mp_user",
    },
  ],
  channel_readiness: [
    {
      id: "cb_whatsapp",
      agent_id: "agent_support",
      agent_name: "Support Concierge",
      channel_type: "whatsapp",
      provider: "Meta Cloud API",
      status: "draft",
      blocking_checks: [
        {
          id: "business_verified",
          label: "Business identity verified",
          status: "failed",
          evidence_ref: "channel/whatsapp/business",
          message: "Business identity is not verified.",
        },
      ],
      reviewer_action: "Resolve readiness blockers before production traffic.",
      evidence_ref: "channel-binding/cb_whatsapp",
    },
  ],
  incidents: [
    {
      id: "inc_refund",
      agent_id: "agent_support",
      agent_name: "Support Concierge",
      severity: "high",
      status: "open",
      trigger: "Refund quote regressed in WhatsApp canary.",
      affected_conversation_count: 4,
      rollback_action_ref: "",
      candidate_eval_suite_id: null,
      evidence_ref: "incident/inc_refund",
    },
  ],
  audit_events: [
    {
      id: "audit_1",
      occurred_at: new Date(0).toISOString(),
      actor_sub: "owner-1",
      action: "change_package:generate",
      resource_type: "change_package",
      resource_id: "cp_refund",
      payload_hash: "hash_audit",
      outcome: "success",
      evidence_ref: "audit/audit_1",
    },
  ],
  industry_probe_libraries: [
    {
      id: "regulated-support",
      name: "Regulated support probes",
      required_for: ["pii", "refunds", "escalation", "data_export"],
      status: "available",
      case_count: 3,
      metrics: ["policy_adherence", "groundedness", "pii_minimization"],
      evidence_ref: "probe-library/regulated-support",
    },
  ],
};

export async function fetchComplianceReview(
  workspaceId: string,
  opts: ComplianceReviewClientOptions = {},
): Promise<ComplianceReviewModel> {
  return cpJson<ComplianceReviewModel>(
    `/workspaces/${encodeURIComponent(workspaceId)}/compliance-review`,
    {
      fallback: {
        ...COMPLIANCE_REVIEW_FIXTURE,
        workspace_id: workspaceId,
      },
      allowFallback: opts.allowFixture === true,
      ...opts,
    },
  );
}

export async function createComplianceEvidenceExport(
  workspaceId: string,
  input: ComplianceEvidenceExportInput,
  opts: EnterpriseGovernMutationOptions = {},
): Promise<ComplianceEvidenceExport> {
  return cpJson<ComplianceEvidenceExport>(
    `/workspaces/${encodeURIComponent(workspaceId)}/compliance-review/evidence-export`,
    {
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        id: "cex_local",
        workspace_id: workspaceId,
        agent_id: input.agent_id ?? null,
        format: input.format ?? "json",
        status: "ready",
        sections: input.include_sections ?? [
          "change_packages",
          "approvals",
          "audit_events",
        ],
        artifact_refs: [
          ...COMPLIANCE_REVIEW_FIXTURE.approval_queue.map(
            (row) => row.evidence_ref,
          ),
          ...COMPLIANCE_REVIEW_FIXTURE.tool_grants.map(
            (row) => row.evidence_ref,
          ),
          ...COMPLIANCE_REVIEW_FIXTURE.memory_policies.map(
            (row) => row.evidence_ref,
          ),
          ...COMPLIANCE_REVIEW_FIXTURE.incidents.map((row) => row.evidence_ref),
        ],
        summary: COMPLIANCE_REVIEW_FIXTURE.summary,
        download_url: `/v1/workspaces/${workspaceId}/compliance-review/evidence-exports/cex_local`,
        generated_by: "local-studio",
        generated_at: new Date(0).toISOString(),
      },
      ...opts,
    },
  );
}

export async function attachComplianceProbeSuite(
  workspaceId: string,
  libraryId: string,
  input: ComplianceProbeSuiteAttachInput = {},
  opts: EnterpriseGovernMutationOptions = {},
): Promise<ComplianceProbeSuiteAttachResult> {
  return cpJson<ComplianceProbeSuiteAttachResult>(
    `/workspaces/${encodeURIComponent(workspaceId)}/compliance-review/probe-libraries/${encodeURIComponent(libraryId)}/attach`,
    {
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        library_id: libraryId,
        library_name:
          COMPLIANCE_REVIEW_FIXTURE.industry_probe_libraries.find(
            (library) => library.id === libraryId,
          )?.name ?? "Compliance probe library",
        status: "attached",
        attached_agents: [
          {
            agent_id: "agent_support",
            agent_name: "Support Concierge",
            suite: {
              id: "suite_regulated_support",
              workspace_id: workspaceId,
              name: "Regulated support probes: support-concierge",
              dataset_ref: "compliance-probes/regulated-support/agent_support",
              metrics: ["policy_adherence", "groundedness"],
              created_at: new Date(0).toISOString(),
              created_by: "local-studio",
            },
            cases_added: [],
            cases_existing: 3,
            evidence_ref: "eval-suite/suite_regulated_support",
          },
        ],
        suite_count: 1,
        case_count: 0,
        audit_ref: `audit/compliance:probe_suite_attach/${libraryId}`,
      },
      ...opts,
    },
  );
}

// ---------------------------------------------------------------------------
// Data residency + BYOK
// ---------------------------------------------------------------------------

export type ResidencyRegion = "us-east" | "us-west" | "eu-west" | "ap-south";

export interface ResidencyZone {
  region: ResidencyRegion;
  label: string;
  active: boolean;
  jurisdictions: readonly string[];
  evidenceRef: string;
}

export const RESIDENCY_ZONES: readonly ResidencyZone[] = [
  {
    region: "us-east",
    label: "US East (Virginia)",
    active: true,
    jurisdictions: ["US"],
    evidenceRef: "audit/residency/us-east",
  },
  {
    region: "eu-west",
    label: "EU West (Ireland)",
    active: true,
    jurisdictions: ["EU", "UK"],
    evidenceRef: "audit/residency/eu-west",
  },
  {
    region: "ap-south",
    label: "AP South (Mumbai)",
    active: false,
    jurisdictions: ["IN"],
    evidenceRef: "audit/residency/ap-south",
  },
] as const;

export type ByokStatus = "rotated" | "active" | "warn" | "missing";

export interface ByokKey {
  id: string;
  alias: string;
  scope: "model" | "storage" | "logs";
  status: ByokStatus;
  rotatedAtDays: number;
  evidenceRef: string;
}

export const BYOK_KEYS: readonly ByokKey[] = [
  {
    id: "k_model_1",
    alias: "kms/model-inference",
    scope: "model",
    status: "active",
    rotatedAtDays: 14,
    evidenceRef: "audit/byok/k_model_1",
  },
  {
    id: "k_storage_1",
    alias: "kms/storage-conv",
    scope: "storage",
    status: "rotated",
    rotatedAtDays: 1,
    evidenceRef: "audit/byok/k_storage_1",
  },
  {
    id: "k_logs_1",
    alias: "kms/audit-logs",
    scope: "logs",
    status: "warn",
    rotatedAtDays: 92,
    evidenceRef: "audit/byok/k_logs_1",
  },
] as const;

// ---------------------------------------------------------------------------
// Whitelabel + procurement
// ---------------------------------------------------------------------------

export interface WhitelabelConfig {
  brandName: string;
  primaryColor: string;
  domain: string;
  emailFrom: string;
  evidenceRef: string;
}

export const WHITELABEL_DEFAULT: WhitelabelConfig = {
  brandName: "Acme Concierge",
  primaryColor: "hsl(var(--primary))",
  domain: "concierge.acme.com",
  emailFrom: "concierge@acme.com",
  evidenceRef: "audit/whitelabel#current",
};

export type ProcurementDocStatus = "ready" | "stale" | "missing";

export interface ProcurementDoc {
  id: string;
  title: string;
  status: ProcurementDocStatus;
  updatedAtDays: number;
  url: string;
  evidenceRef: string;
}

export const PROCUREMENT_DOCS: readonly ProcurementDoc[] = [
  {
    id: "soc2",
    title: "SOC 2 Type II report",
    status: "ready",
    updatedAtDays: 18,
    url: "/legal/soc2-2025.pdf",
    evidenceRef: "audit/procurement/soc2-2025",
  },
  {
    id: "iso27001",
    title: "ISO/IEC 27001 certificate",
    status: "ready",
    updatedAtDays: 96,
    url: "/legal/iso27001.pdf",
    evidenceRef: "audit/procurement/iso27001",
  },
  {
    id: "dpa",
    title: "Data processing addendum",
    status: "ready",
    updatedAtDays: 31,
    url: "/legal/dpa.pdf",
    evidenceRef: "audit/procurement/dpa",
  },
  {
    id: "pen-test",
    title: "Annual penetration test",
    status: "stale",
    updatedAtDays: 410,
    url: "/legal/pen-test-2024.pdf",
    evidenceRef: "audit/procurement/pen-test-2024",
  },
] as const;

// ---------------------------------------------------------------------------
// Private skill library
// ---------------------------------------------------------------------------

export type SkillVisibility = "private" | "workspace" | "public";

export interface PrivateSkill {
  id: string;
  name: string;
  visibility: SkillVisibility;
  owner: string;
  installs: number;
  evidenceRef: string;
}

export const PRIVATE_SKILLS: readonly PrivateSkill[] = [
  {
    id: "sk_acme_refund",
    name: "Acme refund policy lookup",
    visibility: "private",
    owner: "ops@acme",
    installs: 4,
    evidenceRef: "audit/skill/sk_acme_refund",
  },
  {
    id: "sk_acme_kyc",
    name: "Acme KYC verifier",
    visibility: "private",
    owner: "compliance@acme",
    installs: 2,
    evidenceRef: "audit/skill/sk_acme_kyc",
  },
  {
    id: "sk_acme_returns",
    name: "Acme returns flow",
    visibility: "workspace",
    owner: "ops@acme",
    installs: 7,
    evidenceRef: "audit/skill/sk_acme_returns",
  },
] as const;

// ---------------------------------------------------------------------------
// Policy / audit consequences
// ---------------------------------------------------------------------------

export type ConsequenceSeverity = "info" | "warn" | "blocking";

export interface PolicyConsequence {
  id: string;
  trigger: string;
  consequence: string;
  severity: ConsequenceSeverity;
  evidenceRef: string;
}

export const POLICY_CONSEQUENCES: readonly PolicyConsequence[] = [
  {
    id: "pc_1",
    trigger: "Three policy violations on the same agent in 24h",
    consequence:
      "Agent paused; rollback to last known-good. Notify owner + compliance.",
    severity: "blocking",
    evidenceRef: "policy/pc_1",
  },
  {
    id: "pc_2",
    trigger: "Audit export requested without compliance approval",
    consequence: "Request rejected. Audit event recorded. Approver notified.",
    severity: "blocking",
    evidenceRef: "policy/pc_2",
  },
  {
    id: "pc_3",
    trigger: "BYOK key un-rotated > 90 days",
    consequence: "Warning shown; rotation reminder sent. No automatic block.",
    severity: "warn",
    evidenceRef: "policy/pc_3",
  },
  {
    id: "pc_4",
    trigger: "PII detected in agent prompt",
    consequence: "PII redacted in logs; review queued in HITL inbox.",
    severity: "warn",
    evidenceRef: "policy/pc_4",
  },
  {
    id: "pc_5",
    trigger: "External share approved",
    consequence:
      "Audit event recorded; recipient receives revocable, expiring link.",
    severity: "info",
    evidenceRef: "policy/pc_5",
  },
] as const;
