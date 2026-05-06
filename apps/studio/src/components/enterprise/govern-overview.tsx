"use client";

import { useMemo, useState } from "react";

import {
  APPROVAL_REQUESTS,
  AUDIT_EVENTS,
  BYOK_KEYS,
  PRIVATE_SKILLS,
  PROCUREMENT_DOCS,
  POLICY_CONSEQUENCES,
  RBAC_RESOURCES,
  RBAC_ROLES,
  RESIDENCY_ZONES,
  SSO_SUMMARIES,
  WHITELABEL_DEFAULT,
  filterAudit,
  rbacAllowed,
  type AuditCategory,
} from "@/lib/enterprise-govern";

const SECTIONS = [
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
  configured: "bg-emerald-50 text-emerald-700 border-emerald-200",
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  not_configured: "bg-slate-50 text-slate-600 border-slate-200",
  approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-rose-50 text-rose-700 border-rose-200",
  expired: "bg-slate-50 text-slate-500 border-slate-200",
  active: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rotated: "bg-sky-50 text-sky-700 border-sky-200",
  warn: "bg-amber-50 text-amber-700 border-amber-200",
  missing: "bg-rose-50 text-rose-700 border-rose-200",
  ready: "bg-emerald-50 text-emerald-700 border-emerald-200",
  stale: "bg-amber-50 text-amber-700 border-amber-200",
  info: "bg-slate-50 text-slate-600 border-slate-200",
  blocking: "bg-rose-50 text-rose-700 border-rose-200",
};

function pill(status: string): string {
  return (
    "inline-flex items-center px-2 py-0.5 text-xs font-medium border rounded " +
    (STATUS_TONE[status] ?? "bg-slate-50 text-slate-600 border-slate-200")
  );
}

export function GovernOverview(): JSX.Element {
  const [section, setSection] = useState<SectionId>("sso");
  const [auditCategory, setAuditCategory] = useState<AuditCategory | "all">("all");

  const auditRows = useMemo(
    () =>
      filterAudit(
        AUDIT_EVENTS,
        auditCategory === "all" ? {} : { category: auditCategory },
      ),
    [auditCategory],
  );

  return (
    <div data-testid="govern-overview" className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Enterprise governance</h1>
        <p className="text-sm text-slate-600">
          Identity, RBAC, approvals, audit, residency, BYOK, whitelabel,
          procurement evidence, and policy consequences in one place.
        </p>
      </header>

      <nav
        data-testid="govern-tablist"
        role="tablist"
        className="flex flex-wrap gap-1 border-b border-slate-200"
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
                  ? "border-slate-900 text-slate-900"
                  : "border-transparent text-slate-500 hover:text-slate-800")
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
        {section === "sso" && (
          <ul className="space-y-2">
            {SSO_SUMMARIES.map((s) => (
              <li
                key={s.protocol}
                data-testid={`sso-row-${s.protocol}`}
                className="flex items-start justify-between border rounded p-3"
              >
                <div>
                  <div className="font-medium">{s.label}</div>
                  <div className="text-sm text-slate-600">{s.detail}</div>
                  <div className="text-xs text-slate-400 mt-1">
                    evidence: {s.evidenceRef}
                  </div>
                </div>
                <span className={pill(s.status)}>{s.status}</span>
              </li>
            ))}
          </ul>
        )}

        {section === "rbac" && (
          <div className="overflow-x-auto">
            <table
              data-testid="rbac-matrix"
              className="w-full text-sm border"
            >
              <thead className="bg-slate-50">
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
                      const can = (a: "view" | "edit" | "approve" | "destroy" | "export") =>
                        rbacAllowed(role, res, a);
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
                          className="p-2 border-b text-xs text-slate-600"
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
                  <div className="text-sm text-slate-600">
                    {a.kind.replace(/_/g, " ")} · {a.requester} → {a.approvers.join(", ")}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
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
                    <span className="font-mono text-xs text-slate-500">{e.ts}</span>
                  </div>
                  <div className="mt-1 text-sm">
                    <span className="font-medium">{e.actor}</span> · {e.action} ·{" "}
                    <span className="text-slate-600">{e.target}</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    evidence: {e.evidenceRef}
                  </div>
                </li>
              ))}
              {auditRows.length === 0 && (
                <li
                  data-testid="audit-empty"
                  className="text-sm text-slate-500 border rounded p-3"
                >
                  No audit events match this filter.
                </li>
              )}
            </ul>
          </div>
        )}

        {section === "residency" && (
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <h2 className="text-sm font-medium mb-2">Active regions</h2>
              <ul className="space-y-2">
                {RESIDENCY_ZONES.map((z) => (
                  <li
                    key={z.region}
                    data-testid={`residency-row-${z.region}`}
                    className="flex items-start justify-between border rounded p-3"
                  >
                    <div>
                      <div className="font-medium">{z.label}</div>
                      <div className="text-sm text-slate-600">
                        jurisdictions: {z.jurisdictions.join(", ")}
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        evidence: {z.evidenceRef}
                      </div>
                    </div>
                    <span className={pill(z.active ? "active" : "not_configured")}>
                      {z.active ? "active" : "off"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h2 className="text-sm font-medium mb-2">BYOK keys</h2>
              <ul className="space-y-2">
                {BYOK_KEYS.map((k) => (
                  <li
                    key={k.id}
                    data-testid={`byok-row-${k.id}`}
                    className="flex items-start justify-between border rounded p-3"
                  >
                    <div>
                      <div className="font-medium">{k.alias}</div>
                      <div className="text-sm text-slate-600">
                        scope: {k.scope} · rotated {k.rotatedAtDays}d ago
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        evidence: {k.evidenceRef}
                      </div>
                    </div>
                    <span className={pill(k.status)}>{k.status}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {section === "whitelabel" && (
          <dl
            data-testid="whitelabel-summary"
            className="border rounded p-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm"
          >
            <dt className="text-slate-500">Brand</dt>
            <dd>{WHITELABEL_DEFAULT.brandName}</dd>
            <dt className="text-slate-500">Domain</dt>
            <dd className="font-mono text-xs">{WHITELABEL_DEFAULT.domain}</dd>
            <dt className="text-slate-500">Email-from</dt>
            <dd className="font-mono text-xs">{WHITELABEL_DEFAULT.emailFrom}</dd>
            <dt className="text-slate-500">Primary color</dt>
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
            <dt className="text-slate-500">Evidence</dt>
            <dd className="font-mono text-xs">{WHITELABEL_DEFAULT.evidenceRef}</dd>
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
                  <div className="text-sm text-slate-600">
                    updated {d.updatedAtDays}d ago ·{" "}
                    <a className="underline" href={d.url}>
                      open
                    </a>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
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
                  <div className="text-sm text-slate-600">
                    owner: {s.owner} · installs: {s.installs}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    evidence: {s.evidenceRef}
                  </div>
                </div>
                <span className={pill(s.visibility === "private" ? "active" : "info")}>
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
                <div className="text-sm text-slate-600 mt-1">{p.consequence}</div>
                <div className="text-xs text-slate-400 mt-1">
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
