import { describe, expect, it, vi } from "vitest";

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
  SSO_SUMMARIES,
  attachComplianceProbeSuite,
  buildRbacMatrix,
  createComplianceEvidenceExport,
  fetchComplianceReview,
  fetchEnterpriseSecurity,
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

describe("compliance review client", () => {
  it("requires cp-api for compliance review by default", async () => {
    await expect(
      fetchComplianceReview("workspace_1", { baseUrl: "" }),
    ).rejects.toThrow(/LOOP_CP_API_BASE_URL is required/i);
  });

  it("keeps fixture-backed compliance review explicitly opt-in", async () => {
    const model = await fetchComplianceReview("workspace_1", {
      baseUrl: "",
      allowFixture: true,
    });

    expect(model.workspace_id).toBe("workspace_1");
    expect(model.summary.pending_approvals).toBeGreaterThan(0);
    expect(model.tool_grants[0]?.reviewer_action).toContain("Block live use");
    expect(model.industry_probe_libraries[0]?.id).toBe("regulated-support");
    expect(model.sso_summaries?.map((item) => item.protocol)).toEqual([
      "saml",
      "oidc",
      "scim",
    ]);
  });

  it("posts evidence export requests to the workspace compliance endpoint", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        id: "cex_1",
        workspace_id: "workspace_1",
        agent_id: "agent_1",
        format: "json",
        status: "ready",
        sections: ["approvals"],
        artifact_refs: ["change-package/cp_1"],
        summary: COMPLIANCE_REVIEW_FIXTURE.summary,
        download_url:
          "/v1/workspaces/workspace_1/compliance-review/evidence-exports/cex_1",
        generated_by: "owner-1",
        generated_at: "2026-05-09T00:00:00Z",
      }),
    );

    const exportResult = await createComplianceEvidenceExport(
      "workspace_1",
      {
        agent_id: "agent_1",
        format: "json",
        include_sections: ["approvals"],
      },
      { baseUrl: "https://cp.test", fetcher, token: "tok" },
    );

    expect(exportResult.id).toBe("cex_1");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/workspace_1/compliance-review/evidence-export",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ authorization: "Bearer tok" }),
      }),
    );
    const [, init] = fetcher.mock.calls[0]!;
    expect(JSON.parse(String(init?.body))).toMatchObject({
      agent_id: "agent_1",
      include_sections: ["approvals"],
    });
  });

  it("requires cp-api before creating compliance evidence exports", async () => {
    await expect(
      createComplianceEvidenceExport(
        "workspace_1",
        { format: "json", include_sections: ["approvals"] },
        { baseUrl: "" },
      ),
    ).rejects.toThrow(/LOOP_CP_API_BASE_URL is required/i);
  });

  it("requires cp-api before attaching compliance probe suites", async () => {
    await expect(
      attachComplianceProbeSuite(
        "workspace_1",
        "regulated-support",
        {},
        { baseUrl: "" },
      ),
    ).rejects.toThrow(/LOOP_CP_API_BASE_URL is required/i);
  });

  it("loads source-backed residency and BYOK posture", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        workspace_id: "workspace_1",
        residency_zones: [
          {
            region: "eu-west",
            label: "EU West",
            active: true,
            jurisdictions: ["EU", "UK"],
            evidence_ref: "workspace/residency/eu-west",
          },
        ],
        byok_keys: [
          {
            id: "workspace_key_v2",
            alias: "arn:aws:kms:eu-west-2:111:key/abc",
            scope: "storage",
            status: "rotated",
            rotated_at_days: 0,
            evidence_ref: "audit/byok/workspace_1/v2",
          },
        ],
        evidence_ref: "enterprise/security/workspace_1",
      }),
    );

    const model = await fetchEnterpriseSecurity("workspace_1", {
      baseUrl: "https://cp.test",
      fetcher,
    });

    expect(model.residencyZones[0]?.region).toBe("eu-west");
    expect(model.byokKeys[0]?.status).toBe("rotated");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/workspace_1/enterprise/security",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
