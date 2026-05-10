"use client";

import { useMemo, useState } from "react";

import {
  APPROVAL_REQUESTS,
  AUDIT_EVENTS,
  BYOK_KEYS,
  COMPLIANCE_REVIEW_FIXTURE,
  PRIVATE_SKILLS,
  PROCUREMENT_DOCS,
  POLICY_CONSEQUENCES,
  RBAC_RESOURCES,
  RBAC_ROLES,
  RESIDENCY_ZONES,
  WHITELABEL_DEFAULT,
  attachComplianceProbeSuite,
  createComplianceEvidenceExport,
  filterAudit,
  rbacAllowed,
  type ComplianceEvidenceExport,
  type ComplianceEvidenceExportInput,
  type ComplianceProbeSuiteAttachInput,
  type ComplianceProbeSuiteAttachResult,
  type ComplianceReviewModel,
  type AuditCategory,
  type ByokKey,
  type ResidencyZone,
} from "@/lib/enterprise-govern";

const SECTIONS = [
  { id: "compliance", label: "Compliance review" },
  { id: "sso", label: "SSO / SCIM" },
  { id: "rbac", label: "RBAC matrix" },
  { id: "approvals", label: "Approvals" },
  { id: "audit", label: "Audit explorer" },
  { id: "residency", label: "Residency · BYOK" },
  { id: "whitelabel", label: "Whitelabel" },
  { id: "procurement", label: "Procurement" },
  { id: "skills", label: "Private skills" },
  { id: "policy", label: "Policy consequences" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

const STATUS_TONE: Record<string, string> = {
  configured: "border-success/30 bg-success/10 text-success",
  pending: "border-warning/30 bg-warning/10 text-warning",
  not_configured: "border-border bg-muted text-muted-foreground",
  approved: "border-success/30 bg-success/10 text-success",
  rejected: "border-destructive/30 bg-destructive/10 text-destructive",
  expired: "border-border bg-muted text-muted-foreground",
  active: "border-success/30 bg-success/10 text-success",
  rotated: "border-info/30 bg-info/10 text-info",
  warn: "border-warning/30 bg-warning/10 text-warning",
  missing: "border-destructive/30 bg-destructive/10 text-destructive",
  ready: "border-success/30 bg-success/10 text-success",
  stale: "border-warning/30 bg-warning/10 text-warning",
  info: "border-border bg-muted text-muted-foreground",
  blocking: "border-destructive/30 bg-destructive/10 text-destructive",
  low: "border-border bg-muted text-muted-foreground",
  medium: "border-warning/30 bg-warning/10 text-warning",
  high: "border-destructive/30 bg-destructive/10 text-destructive",
  critical: "border-destructive/30 bg-destructive/10 text-destructive",
  action_required: "border-destructive/30 bg-destructive/10 text-destructive",
  clear: "border-success/30 bg-success/10 text-success",
};

function pill(status: string): string {
  return (
    "inline-flex items-center px-2 py-0.5 text-xs font-medium border rounded " +
    (STATUS_TONE[status] ?? "border-border bg-muted text-muted-foreground")
  );
}

export interface GovernOverviewProps {
  compliance?: ComplianceReviewModel;
  createExport?: (
    workspaceId: string,
    input: ComplianceEvidenceExportInput,
  ) => Promise<ComplianceEvidenceExport>;
  attachProbeSuite?: (
    workspaceId: string,
    libraryId: string,
    input?: ComplianceProbeSuiteAttachInput,
  ) => Promise<ComplianceProbeSuiteAttachResult>;
  residencyZones?: readonly ResidencyZone[];
  byokKeys?: readonly ByokKey[];
  securityEvidenceRef?: string;
  securityDegradedReason?: string;
}

export function GovernOverview({
  compliance = COMPLIANCE_REVIEW_FIXTURE,
  createExport = createComplianceEvidenceExport,
  attachProbeSuite = attachComplianceProbeSuite,
  residencyZones = RESIDENCY_ZONES,
  byokKeys = BYOK_KEYS,
  securityEvidenceRef,
  securityDegradedReason,
}: GovernOverviewProps): JSX.Element {
  const [section, setSection] = useState<SectionId>("compliance");
  const [auditCategory, setAuditCategory] = useState<AuditCategory | "all">(
    "all",
  );
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] =
    useState<ComplianceEvidenceExport | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [attachingProbeId, setAttachingProbeId] = useState<string | null>(null);
  const [probeResult, setProbeResult] =
    useState<ComplianceProbeSuiteAttachResult | null>(null);
  const [probeError, setProbeError] = useState<string | null>(null);
  const ssoSummaries = compliance.sso_summaries ?? [];

  const auditRows = useMemo(
    () =>
      filterAudit(
        AUDIT_EVENTS,
        auditCategory === "all" ? {} : { category: auditCategory },
      ),
    [auditCategory],
  );

  async function handleEvidenceExport() {
    setExporting(true);
    setExportError(null);
    setExportResult(null);
    try {
      const result = await createExport(compliance.workspace_id, {
        format: "json",
        include_sections: [
          "change_packages",
          "approvals",
          "incidents",
          "audit_events",
          "tool_grants",
          "memory_policies",
          "channel_readiness",
        ],
      });
      setExportResult(result);
    } catch (error) {
      setExportError(
        error instanceof Error
          ? error.message
          : "Could not create compliance evidence export.",
      );
    } finally {
      setExporting(false);
    }
  }

  async function handleAttachProbeSuite(libraryId: string) {
    setAttachingProbeId(libraryId);
    setProbeError(null);
    setProbeResult(null);
    try {
      const result = await attachProbeSuite(compliance.workspace_id, libraryId);
      setProbeResult(result);
    } catch (error) {
      setProbeError(
        error instanceof Error
          ? error.message
          : "Could not attach compliance probe suite.",
      );
    } finally {
      setAttachingProbeId(null);
    }
  }

  return (
    <div data-testid="govern-overview" className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Enterprise governance</h1>
        <p className="text-sm text-muted-foreground">
          Identity, RBAC, approvals, audit, residency, BYOK, whitelabel,
          procurement evidence, and policy consequences in one place.
        </p>
      </header>

      <nav
        data-testid="govern-tablist"
        role="tablist"
        className="flex flex-wrap gap-1 border-b border-border"
      >
        {SECTIONS.map((s) => {
          const active = section === s.id;
          return (
            <button
              key={s.id}
              type="button"
              role="tab"
              aria-selected={active}
              data-testid={`govern-tab-${s.id}`}
              onClick={() => setSection(s.id)}
              className={
                "px-3 py-1.5 text-sm border-b-2 -mb-px " +
                (active
                  ? "border-foreground text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground")
              }
            >
              {s.label}
            </button>
          );
        })}
      </nav>

      <section
        role="tabpanel"
        data-testid={`govern-pane-${section}`}
        className="space-y-3"
      >
        {section === "compliance" && (
          <div className="space-y-4" data-testid="compliance-review-pane">
            <div className="grid gap-3 md:grid-cols-4">
              {[
                ["Pending approvals", compliance.summary.pending_approvals],
                ["Tool reviews", compliance.summary.tool_reviews],
                ["Memory reviews", compliance.summary.memory_reviews],
                ["Policy conflicts", compliance.summary.policy_conflicts],
              ].map(([label, value]) => (
                <div key={label} className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">{label}</div>
                  <div className="mt-1 text-2xl font-semibold">{value}</div>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 rounded border p-3">
              <div>
                <h2 className="text-sm font-semibold">Evidence export</h2>
                <p className="text-sm text-muted-foreground">
                  Exports Commitment, Change Package, eval/replay refs,
                  approvals, incidents, audit, tool, memory, and channel
                  evidence for review.
                </p>
              </div>
              <button
                type="button"
                data-testid="compliance-export"
                className="rounded border px-3 py-1.5 text-sm font-medium hover:bg-muted disabled:opacity-60"
                disabled={exporting}
                onClick={() => void handleEvidenceExport()}
              >
                {exporting ? "Exporting" : "Create evidence export"}
              </button>
            </div>
            {exportResult ? (
              <div
                className="rounded border border-success/30 bg-success/10 p-3 text-sm text-success"
                data-testid="compliance-export-result"
              >
                Export {exportResult.id} is ready with{" "}
                {exportResult.artifact_refs.length} artifact refs.
              </div>
            ) : null}
            {exportError ? (
              <div
                className="rounded border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
                role="alert"
              >
                {exportError}
              </div>
            ) : null}

            <section className="rounded border p-3">
              <h2 className="text-sm font-semibold">Derived compliance jobs</h2>
              <ul className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                {compliance.review_jobs.map((job) => (
                  <li
                    key={job.id}
                    className="rounded border p-3"
                    data-testid={`compliance-job-${job.id}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="font-medium">
                          {job.id.replace(/_/g, " ")}
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {job.output_count} output(s)
                        </div>
                      </div>
                      <span className={pill(job.status)}>{job.status}</span>
                    </div>
                    <p className="mt-2 text-sm text-foreground">
                      {job.reviewer_action}
                    </p>
                    <div className="mt-2 break-all text-xs text-muted-foreground">
                      evidence: {job.evidence_ref}
                    </div>
                  </li>
                ))}
              </ul>
            </section>

            <div className="grid gap-3 lg:grid-cols-2">
              <section className="rounded border p-3">
                <h2 className="text-sm font-semibold">
                  Approval queue by risk
                </h2>
                <ul className="mt-3 space-y-2">
                  {compliance.approval_queue.map((item) => (
                    <li
                      key={item.id}
                      className="rounded border p-3"
                      data-testid={`compliance-approval-${item.id}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-medium">{item.subject}</div>
                          <div className="text-sm text-muted-foreground">
                            {item.agent_name} · {item.role} · {item.reason}
                          </div>
                        </div>
                        <span className={pill(item.risk_class)}>
                          {item.risk_class}
                        </span>
                      </div>
                      <div className="mt-1 break-all text-xs text-muted-foreground">
                        evidence: {item.evidence_ref}
                      </div>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="rounded border p-3">
                <h2 className="text-sm font-semibold">Policy violations</h2>
                <ul className="mt-3 space-y-2">
                  {compliance.policy_violations.length ? (
                    compliance.policy_violations.map((item) => (
                      <li
                        key={item.id}
                        className="rounded border p-3"
                        data-testid={`compliance-policy-${item.id}`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium">{item.title}</span>
                          <span className={pill(item.severity)}>
                            {item.severity}
                          </span>
                        </div>
                        <div className="mt-1 text-sm text-muted-foreground">
                          {item.target}
                        </div>
                        <div className="mt-1 break-all text-xs text-muted-foreground">
                          evidence: {item.evidence_ref}
                        </div>
                      </li>
                    ))
                  ) : (
                    <li className="rounded border p-3 text-sm text-muted-foreground">
                      No policy violations in the current review window.
                    </li>
                  )}
                </ul>
              </section>

              <section className="rounded border p-3">
                <h2 className="text-sm font-semibold">Policy conflicts</h2>
                <ul className="mt-3 space-y-2">
                  {compliance.policy_conflicts.length ? (
                    compliance.policy_conflicts.map((item) => (
                      <li
                        key={item.id}
                        className="rounded border p-3"
                        data-testid={`compliance-conflict-${item.id}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="font-medium">
                              {item.policy.replace(/_/g, " ")}
                            </div>
                            <div className="mt-1 text-sm text-muted-foreground">
                              {item.summary}
                            </div>
                          </div>
                          <span className={pill(item.severity)}>
                            {item.severity}
                          </span>
                        </div>
                        <p className="mt-2 text-sm text-foreground">
                          {item.reviewer_action}
                        </p>
                        <div className="mt-1 break-all text-xs text-muted-foreground">
                          evidence: {item.evidence_ref}
                        </div>
                      </li>
                    ))
                  ) : (
                    <li className="rounded border p-3 text-sm text-muted-foreground">
                      No derived policy conflicts in this review window.
                    </li>
                  )}
                </ul>
              </section>

              <section className="rounded border p-3">
                <h2 className="text-sm font-semibold">Data access changes</h2>
                <ul className="mt-3 space-y-2">
                  {compliance.data_access_changes.length ? (
                    compliance.data_access_changes.map((item) => (
                      <li
                        key={item.id}
                        className="rounded border p-3"
                        data-testid={`compliance-access-${item.id}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="font-medium">{item.target}</div>
                            <div className="mt-1 text-sm text-muted-foreground">
                              {item.agent_name} · {item.surface} ·{" "}
                              {item.access.join(", ")}
                            </div>
                          </div>
                          <span className={pill(item.state)}>{item.state}</span>
                        </div>
                        <p className="mt-2 text-sm text-foreground">
                          {item.reviewer_action}
                        </p>
                      </li>
                    ))
                  ) : (
                    <li className="rounded border p-3 text-sm text-muted-foreground">
                      No PII, memory, or money movement access changes detected.
                    </li>
                  )}
                </ul>
              </section>

              <section className="rounded border p-3">
                <h2 className="text-sm font-semibold">Tool grant review</h2>
                <ul className="mt-3 space-y-2">
                  {compliance.tool_grants.map((item) => (
                    <li
                      key={item.id}
                      className="rounded border p-3"
                      data-testid={`compliance-tool-${item.id}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-medium">{item.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {item.agent_name} · {item.side_effect_level}
                            {item.pii_access ? " · PII" : ""}
                            {item.money_movement ? " · money movement" : ""}
                          </div>
                        </div>
                        <span className={pill(item.live_status)}>
                          {item.live_status}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-foreground">
                        {item.reviewer_action}
                      </p>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="rounded border p-3">
                <h2 className="text-sm font-semibold">Memory policy review</h2>
                <ul className="mt-3 space-y-2">
                  {compliance.memory_policies.map((item) => (
                    <li
                      key={item.id}
                      className="rounded border p-3"
                      data-testid={`compliance-memory-${item.id}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-medium">{item.scope} memory</div>
                          <div className="text-sm text-muted-foreground">
                            {item.agent_name} · {item.retention}
                          </div>
                        </div>
                        <span className={pill(item.approval_status)}>
                          {item.approval_status}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-foreground">
                        {item.reviewer_action}
                      </p>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="rounded border p-3">
                <h2 className="text-sm font-semibold">
                  Channel compliance readiness
                </h2>
                <ul className="mt-3 space-y-2">
                  {compliance.channel_readiness.map((item) => (
                    <li
                      key={item.id}
                      className="rounded border p-3"
                      data-testid={`compliance-channel-${item.id}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-medium">
                            {item.channel_type.replace(/_/g, " ")}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {item.agent_name} · {item.provider}
                          </div>
                        </div>
                        <span className={pill(item.status)}>{item.status}</span>
                      </div>
                      <p className="mt-2 text-sm text-foreground">
                        {item.reviewer_action}
                      </p>
                      {item.blocking_checks.length ? (
                        <div className="mt-2 text-xs text-muted-foreground">
                          {item.blocking_checks.length} readiness blocker(s)
                        </div>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="rounded border p-3">
                <h2 className="text-sm font-semibold">
                  Incident investigation
                </h2>
                <ul className="mt-3 space-y-2">
                  {compliance.incidents.map((item) => (
                    <li
                      key={item.id}
                      className="rounded border p-3"
                      data-testid={`compliance-incident-${item.id}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-medium">{item.trigger}</div>
                          <div className="text-sm text-muted-foreground">
                            {item.agent_name} ·{" "}
                            {item.affected_conversation_count} conversations
                            affected
                          </div>
                        </div>
                        <span className={pill(item.severity)}>
                          {item.severity}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="rounded border p-3 lg:col-span-2">
                <h2 className="text-sm font-semibold">
                  Industry probe libraries
                </h2>
                <ul className="mt-3 grid gap-2 md:grid-cols-2">
                  {compliance.industry_probe_libraries.map((item) => (
                    <li
                      key={item.id}
                      className="rounded border p-3"
                      data-testid={`compliance-probe-${item.id}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-medium">{item.name}</div>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {item.case_count} required cases ·{" "}
                            {item.metrics.join(", ")}
                          </div>
                        </div>
                        <button
                          type="button"
                          className="rounded border border-border px-2 py-1 text-xs font-medium text-foreground hover:border-foreground hover:text-foreground disabled:cursor-wait disabled:opacity-50"
                          disabled={attachingProbeId === item.id}
                          data-testid={`attach-probe-${item.id}`}
                          onClick={() => void handleAttachProbeSuite(item.id)}
                        >
                          {attachingProbeId === item.id
                            ? "Attaching"
                            : "Attach suite"}
                        </button>
                      </div>
                      <div className="mt-1 text-sm text-muted-foreground">
                        Required for {item.required_for.join(", ")}
                      </div>
                      <div className="mt-1 break-all text-xs text-muted-foreground">
                        evidence: {item.evidence_ref}
                      </div>
                    </li>
                  ))}
                </ul>
                {probeResult ? (
                  <div
                    className="mt-3 rounded border border-success/30 bg-success/10 p-3 text-sm text-success"
                    data-testid="compliance-probe-result"
                  >
                    Attached {probeResult.library_name} to{" "}
                    {probeResult.suite_count} agent(s); added{" "}
                    {probeResult.case_count} case(s).
                    <div className="mt-1 text-xs text-success">
                      {probeResult.attached_agents
                        .map((agent) => agent.suite.name)
                        .join(", ") || "No high-risk agents required it."}
                    </div>
                  </div>
                ) : null}
                {probeError ? (
                  <div
                    className="mt-3 rounded border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
                    data-testid="compliance-probe-error"
                  >
                    {probeError}
                  </div>
                ) : null}
              </section>
            </div>
          </div>
        )}

        {section === "sso" && (
          <>
            {ssoSummaries.length === 0 ? (
              <div
                data-testid="sso-evidence-unavailable"
                className="rounded border border-warning/30 bg-warning/10 p-3 text-sm text-warning"
              >
                <p className="font-medium">SSO evidence unavailable.</p>
                <p className="mt-1 text-xs">
                  The compliance-review response did not include SSO or SCIM
                  evidence. Studio will not substitute local connection claims
                  for this workspace.
                </p>
              </div>
            ) : (
              <ul className="space-y-2">
                {ssoSummaries.map((s) => (
                  <li
                    key={s.protocol}
                    data-testid={`sso-row-${s.protocol}`}
                    className="flex items-start justify-between rounded border p-3"
                  >
                    <div>
                      <div className="font-medium">{s.label}</div>
                      <div className="text-sm text-muted-foreground">
                        {s.detail}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        evidence: {s.evidenceRef}
                      </div>
                    </div>
                    <span className={pill(s.status)}>{s.status}</span>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}

        {section === "rbac" && (
          <div className="overflow-x-auto">
            <table data-testid="rbac-matrix" className="w-full text-sm border">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left p-2 border-b">Role × resource</th>
                  {RBAC_RESOURCES.map((r) => (
                    <th key={r} className="p-2 border-b text-left">
                      {r}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {RBAC_ROLES.map((role) => (
                  <tr key={role} data-testid={`rbac-row-${role}`}>
                    <td className="p-2 border-b font-medium">{role}</td>
                    {RBAC_RESOURCES.map((res) => {
                      const can = (
                        a: "view" | "edit" | "approve" | "destroy" | "export",
                      ) => rbacAllowed(role, res, a);
                      const verbs: string[] = [];
                      if (can("view")) verbs.push("view");
                      if (can("edit")) verbs.push("edit");
                      if (can("approve")) verbs.push("approve");
                      if (can("destroy")) verbs.push("destroy");
                      if (can("export")) verbs.push("export");
                      return (
                        <td
                          key={res}
                          data-testid={`rbac-cell-${role}-${res}`}
                          className="p-2 border-b text-xs text-muted-foreground"
                        >
                          {verbs.length ? verbs.join(", ") : "—"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {section === "approvals" && (
          <ul className="space-y-2">
            {APPROVAL_REQUESTS.map((a) => (
              <li
                key={a.id}
                data-testid={`approval-row-${a.id}`}
                className="flex items-start justify-between border rounded p-3"
              >
                <div>
                  <div className="font-medium">{a.subject}</div>
                  <div className="text-sm text-muted-foreground">
                    {a.kind.replace(/_/g, " ")} · {a.requester} →{" "}
                    {a.approvers.join(", ")}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    age: {a.ageMinutes}m · evidence: {a.evidenceRef}
                  </div>
                </div>
                <span className={pill(a.state)}>{a.state}</span>
              </li>
            ))}
          </ul>
        )}

        {section === "audit" && (
          <div className="space-y-2">
            <label className="text-sm flex items-center gap-2">
              <span>Filter category:</span>
              <select
                data-testid="audit-category-filter"
                value={auditCategory}
                onChange={(e) =>
                  setAuditCategory(e.target.value as AuditCategory | "all")
                }
                className="border rounded px-2 py-1 text-sm"
              >
                <option value="all">all</option>
                <option value="auth">auth</option>
                <option value="rbac">rbac</option>
                <option value="deploy">deploy</option>
                <option value="policy">policy</option>
                <option value="data">data</option>
                <option value="billing">billing</option>
              </select>
            </label>
            <ul data-testid="audit-list" className="space-y-2">
              {auditRows.map((e) => (
                <li
                  key={e.id}
                  data-testid={`audit-row-${e.id}`}
                  className="border rounded p-3"
                >
                  <div className="flex items-center gap-2 text-sm">
                    <span className={pill(e.category)}>{e.category}</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {e.ts}
                    </span>
                  </div>
                  <div className="mt-1 text-sm">
                    <span className="font-medium">{e.actor}</span> · {e.action}{" "}
                    · <span className="text-muted-foreground">{e.target}</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    evidence: {e.evidenceRef}
                  </div>
                </li>
              ))}
              {auditRows.length === 0 && (
                <li
                  data-testid="audit-empty"
                  className="text-sm text-muted-foreground border rounded p-3"
                >
                  No audit events match this filter.
                </li>
              )}
            </ul>
          </div>
        )}

        {section === "residency" && (
          <div className="grid gap-3 md:grid-cols-2">
            {securityDegradedReason ? (
              <div
                className="rounded border border-warning/30 bg-warning/10 p-3 text-sm text-warning md:col-span-2"
                data-testid="enterprise-security-degraded"
                role="status"
              >
                Enterprise security evidence is degraded:{" "}
                {securityDegradedReason}
              </div>
            ) : securityEvidenceRef ? (
              <div
                className="rounded border bg-card p-3 text-xs text-muted-foreground md:col-span-2"
                data-testid="enterprise-security-evidence"
              >
                source: {securityEvidenceRef}
              </div>
            ) : null}
            <div>
              <h2 className="text-sm font-medium mb-2">Active regions</h2>
              <ul className="space-y-2">
                {residencyZones.map((z) => (
                  <li
                    key={z.region}
                    data-testid={`residency-row-${z.region}`}
                    className="flex items-start justify-between border rounded p-3"
                  >
                    <div>
                      <div className="font-medium">{z.label}</div>
                      <div className="text-sm text-muted-foreground">
                        jurisdictions: {z.jurisdictions.join(", ")}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        evidence: {z.evidenceRef}
                      </div>
                    </div>
                    <span
                      className={pill(z.active ? "active" : "not_configured")}
                    >
                      {z.active ? "active" : "off"}
                    </span>
                  </li>
                ))}
                {residencyZones.length === 0 ? (
                  <li
                    className="rounded border border-dashed p-3 text-sm text-muted-foreground"
                    data-testid="residency-empty"
                  >
                    No residency evidence loaded from cp-api.
                  </li>
                ) : null}
              </ul>
            </div>
            <div>
              <h2 className="text-sm font-medium mb-2">BYOK keys</h2>
              <ul className="space-y-2">
                {byokKeys.map((k) => (
                  <li
                    key={k.id}
                    data-testid={`byok-row-${k.id}`}
                    className="flex items-start justify-between border rounded p-3"
                  >
                    <div>
                      <div className="font-medium">{k.alias}</div>
                      <div className="text-sm text-muted-foreground">
                        scope: {k.scope} · rotated {k.rotatedAtDays}d ago
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        evidence: {k.evidenceRef}
                      </div>
                    </div>
                    <span className={pill(k.status)}>{k.status}</span>
                  </li>
                ))}
                {byokKeys.length === 0 ? (
                  <li
                    className="rounded border border-dashed p-3 text-sm text-muted-foreground"
                    data-testid="byok-empty"
                  >
                    No BYOK evidence loaded from cp-api.
                  </li>
                ) : null}
              </ul>
            </div>
          </div>
        )}

        {section === "whitelabel" && (
          <dl
            data-testid="whitelabel-summary"
            className="border rounded p-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm"
          >
            <dt className="text-muted-foreground">Brand</dt>
            <dd>{WHITELABEL_DEFAULT.brandName}</dd>
            <dt className="text-muted-foreground">Domain</dt>
            <dd className="font-mono text-xs">{WHITELABEL_DEFAULT.domain}</dd>
            <dt className="text-muted-foreground">Email-from</dt>
            <dd className="font-mono text-xs">
              {WHITELABEL_DEFAULT.emailFrom}
            </dd>
            <dt className="text-muted-foreground">Primary color</dt>
            <dd>
              <span
                aria-hidden="true"
                className="inline-block w-3 h-3 rounded-sm align-middle mr-2"
                style={{ backgroundColor: WHITELABEL_DEFAULT.primaryColor }}
              />
              <span className="font-mono text-xs">
                {WHITELABEL_DEFAULT.primaryColor}
              </span>
            </dd>
            <dt className="text-muted-foreground">Evidence</dt>
            <dd className="font-mono text-xs">
              {WHITELABEL_DEFAULT.evidenceRef}
            </dd>
          </dl>
        )}

        {section === "procurement" && (
          <ul className="space-y-2">
            {PROCUREMENT_DOCS.map((d) => (
              <li
                key={d.id}
                data-testid={`procurement-row-${d.id}`}
                className="flex items-start justify-between border rounded p-3"
              >
                <div>
                  <div className="font-medium">{d.title}</div>
                  <div className="text-sm text-muted-foreground">
                    updated {d.updatedAtDays}d ago ·{" "}
                    <a className="underline" href={d.url}>
                      open
                    </a>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    evidence: {d.evidenceRef}
                  </div>
                </div>
                <span className={pill(d.status)}>{d.status}</span>
              </li>
            ))}
          </ul>
        )}

        {section === "skills" && (
          <ul className="space-y-2">
            {PRIVATE_SKILLS.map((s) => (
              <li
                key={s.id}
                data-testid={`skill-row-${s.id}`}
                className="flex items-start justify-between border rounded p-3"
              >
                <div>
                  <div className="font-medium">{s.name}</div>
                  <div className="text-sm text-muted-foreground">
                    owner: {s.owner} · installs: {s.installs}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    evidence: {s.evidenceRef}
                  </div>
                </div>
                <span
                  className={pill(
                    s.visibility === "private" ? "active" : "info",
                  )}
                >
                  {s.visibility}
                </span>
              </li>
            ))}
          </ul>
        )}

        {section === "policy" && (
          <ul className="space-y-2">
            {POLICY_CONSEQUENCES.map((p) => (
              <li
                key={p.id}
                data-testid={`policy-row-${p.id}`}
                className="border rounded p-3"
              >
                <div className="flex items-center justify-between">
                  <div className="font-medium">{p.trigger}</div>
                  <span className={pill(p.severity)}>{p.severity}</span>
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  {p.consequence}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  evidence: {p.evidenceRef}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
