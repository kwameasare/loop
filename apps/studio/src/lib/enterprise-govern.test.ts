import { describe, expect, it } from "vitest";

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
  buildRbacMatrix,
  filterAudit,
  pendingApprovals,
  rbacAllowed,
} from "./enterprise-govern";

describe("rbac matrix", () => {
  it("denies destroy for viewer everywhere", () => {
    for (const r of RBAC_RESOURCES) {
      expect(rbacAllowed("viewer", r, "destroy")).toBe(false);
    }
  });

  it("admin can destroy agents but auditor cannot", () => {
    expect(rbacAllowed("admin", "agents", "destroy")).toBe(true);
    expect(rbacAllowed("auditor", "agents", "destroy")).toBe(false);
  });

  it("only admin and auditor can export audit", () => {
    for (const role of RBAC_ROLES) {
      const allowed = rbacAllowed(role, "audit", "export");
      expect(allowed).toBe(role === "admin" || role === "auditor");
    }
  });

  it("buildRbacMatrix returns one cell per (role,resource,action)", () => {
    const cells = buildRbacMatrix();
    const expected = RBAC_ROLES.length * RBAC_RESOURCES.length * 5;
    expect(cells.length).toBe(expected);
  });
});

describe("approvals", () => {
  it("pendingApprovals returns only pending", () => {
    const pending = pendingApprovals(APPROVAL_REQUESTS);
    expect(pending.every((r) => r.state === "pending")).toBe(true);
    expect(pending.length).toBeGreaterThan(0);
  });
});

describe("audit filter", () => {
  it("filters by category", () => {
    const policy = filterAudit(AUDIT_EVENTS, { category: "policy" });
    expect(policy.every((e) => e.category === "policy")).toBe(true);
    expect(policy.length).toBe(1);
  });

  it("filters by actor substring", () => {
    const sec = filterAudit(AUDIT_EVENTS, { actor: "sec@" });
    expect(sec.every((e) => e.actor.includes("sec@"))).toBe(true);
    expect(sec.length).toBe(1);
  });

  it("returns all when no filter", () => {
    expect(filterAudit(AUDIT_EVENTS, {}).length).toBe(AUDIT_EVENTS.length);
  });
});

describe("fixtures carry evidence refs", () => {
  it("every governance row has an evidenceRef", () => {
    const all = [
      ...SSO_SUMMARIES,
      ...APPROVAL_REQUESTS,
      ...AUDIT_EVENTS,
      ...RESIDENCY_ZONES,
      ...BYOK_KEYS,
      ...PROCUREMENT_DOCS,
      ...PRIVATE_SKILLS,
      ...POLICY_CONSEQUENCES,
    ];
    for (const row of all) {
      expect(row.evidenceRef).toMatch(/^(audit|policy)\//);
    }
  });
});
