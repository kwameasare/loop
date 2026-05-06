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
 * Pure data + helpers; no I/O. The cp-api adapter will replace the
 * fixtures when the backend is wired.
 */

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

const ROLE_TEMPLATES: Record<RbacRole, Partial<Record<RbacResource, RbacAction[]>>> = {
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
  const actions: RbacAction[] = ["view", "edit", "approve", "destroy", "export"];
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
  primaryColor: "#0F172A",
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
    consequence: "Agent paused; rollback to last known-good. Notify owner + compliance.",
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
    consequence: "Audit event recorded; recipient receives revocable, expiring link.",
    severity: "info",
    evidenceRef: "policy/pc_5",
  },
] as const;
