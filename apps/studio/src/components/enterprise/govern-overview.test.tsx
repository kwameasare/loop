import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import { GovernOverview } from "./govern-overview";

describe("GovernOverview", () => {
  it("renders compliance reviewer workspace by default", () => {
    render(<GovernOverview />);
    expect(screen.getByTestId("govern-overview")).toBeInTheDocument();
    expect(screen.getByTestId("compliance-review-pane")).toHaveTextContent(
      "Approval queue by risk",
    );
    expect(screen.getByTestId("compliance-tool-tc_refund")).toHaveTextContent(
      "Block live use",
    );
    expect(screen.getByTestId("compliance-memory-mp_user")).toHaveTextContent(
      "Review privacy",
    );
    expect(
      screen.getByTestId("compliance-channel-cb_whatsapp"),
    ).toHaveTextContent("readiness blocker");
    expect(
      screen.getByTestId("compliance-incident-inc_refund"),
    ).toHaveTextContent("WhatsApp canary");
    expect(
      screen.getByTestId("compliance-job-detect_policy_conflicts"),
    ).toHaveTextContent("action_required");
    expect(
      screen.getByTestId("compliance-conflict-tc_refund:missing-budget-cap"),
    ).toHaveTextContent("budget cap");
    expect(
      screen.getByTestId("compliance-access-tool-access:tc_refund"),
    ).toHaveTextContent("money movement");
  });

  it("creates compliance evidence exports from the default pane", async () => {
    const createExport = vi.fn(async () => ({
      id: "cex_1",
      workspace_id: "workspace_local",
      agent_id: null,
      format: "json" as const,
      status: "ready" as const,
      sections: ["approvals"],
      artifact_refs: ["change-package/cp_refund", "tool-contract/tc_refund"],
      summary: {
        agents: 1,
        pending_approvals: 1,
        policy_violations: 0,
        tool_reviews: 1,
        memory_reviews: 1,
        channel_blockers: 1,
        open_incidents: 1,
        policy_conflicts: 0,
        data_access_changes: 0,
        stale_risk_reviews: 0,
      },
      download_url:
        "/v1/workspaces/workspace_local/compliance-review/evidence-exports/cex_1",
      generated_by: "owner-1",
      generated_at: "2026-05-09T00:00:00Z",
    }));

    render(<GovernOverview createExport={createExport} />);

    fireEvent.click(screen.getByTestId("compliance-export"));

    expect(
      await screen.findByTestId("compliance-export-result"),
    ).toHaveTextContent("cex_1");
    expect(createExport).toHaveBeenCalledWith(
      "workspace_local",
      expect.objectContaining({
        include_sections: expect.arrayContaining(["approvals", "audit_events"]),
      }),
    );
  });

  it("attaches industry probe libraries as required eval suites", async () => {
    const attachProbeSuite = vi.fn(async () => ({
      library_id: "regulated-support",
      library_name: "Regulated support probes",
      status: "attached" as const,
      attached_agents: [
        {
          agent_id: "agent_support",
          agent_name: "Support Concierge",
          suite: {
            id: "suite_regulated_support",
            workspace_id: "workspace_local",
            name: "Regulated support probes: support-concierge",
            dataset_ref: "compliance-probes/regulated-support/agent_support",
            metrics: ["policy_adherence"],
            created_at: "2026-05-09T00:00:00Z",
            created_by: "owner-1",
          },
          cases_added: [
            {
              id: "case_1",
              suite_id: "suite_regulated_support",
              workspace_id: "workspace_local",
              name: "Support Concierge: refund cap",
              input: {},
              expected: {},
              scorers: [],
              source: "industry_probe_suite",
              source_ref: "probe-library/regulated-support/refund-cap",
              attachments: ["agent/agent_support"],
              created_at: "2026-05-09T00:00:00Z",
              created_by: "owner-1",
            },
          ],
          cases_existing: 0,
          evidence_ref: "eval-suite/suite_regulated_support",
        },
      ],
      suite_count: 1,
      case_count: 1,
      audit_ref: "audit/compliance:probe_suite_attach/regulated-support",
    }));

    render(<GovernOverview attachProbeSuite={attachProbeSuite} />);

    fireEvent.click(screen.getByTestId("attach-probe-regulated-support"));

    expect(
      await screen.findByTestId("compliance-probe-result"),
    ).toHaveTextContent("added 1 case");
    expect(screen.getByTestId("compliance-probe-result")).toHaveTextContent(
      "Regulated support probes: support-concierge",
    );
    expect(attachProbeSuite).toHaveBeenCalledWith(
      "workspace_local",
      "regulated-support",
    );
  });

  it("renders SSO summaries on the SSO tab", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-sso"));
    expect(screen.getByTestId("sso-row-saml")).toBeInTheDocument();
    expect(screen.getByTestId("sso-row-oidc")).toBeInTheDocument();
    expect(screen.getByTestId("sso-row-scim")).toBeInTheDocument();
  });

  it("RBAC tab shows full role × resource matrix", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-rbac"));
    const matrix = screen.getByTestId("rbac-matrix");
    expect(matrix).toBeInTheDocument();
    // viewer cannot destroy agents
    const viewerAgents = within(matrix).getByTestId("rbac-cell-viewer-agents");
    expect(viewerAgents.textContent).not.toContain("destroy");
    // admin can destroy agents
    const adminAgents = within(matrix).getByTestId("rbac-cell-admin-agents");
    expect(adminAgents.textContent).toContain("destroy");
  });

  it("approvals tab shows pending + resolved states", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-approvals"));
    expect(screen.getByTestId("approval-row-apr_1").textContent).toContain(
      "pending",
    );
    expect(screen.getByTestId("approval-row-apr_2").textContent).toContain(
      "approved",
    );
    expect(screen.getByTestId("approval-row-apr_3").textContent).toContain(
      "rejected",
    );
    expect(screen.getByTestId("approval-row-apr_4").textContent).toContain(
      "expired",
    );
  });

  it("audit explorer filters by category and shows empty state", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-audit"));
    const select = screen.getByTestId(
      "audit-category-filter",
    ) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "policy" } });
    expect(screen.getByTestId("audit-row-ev_1004")).toBeInTheDocument();
    expect(screen.queryByTestId("audit-row-ev_1001")).toBeNull();
    fireEvent.change(select, { target: { value: "billing" } });
    expect(screen.getByTestId("audit-empty")).toBeInTheDocument();
  });

  it("residency tab renders zones and BYOK key warning", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-residency"));
    expect(screen.getByTestId("residency-row-us-east").textContent).toContain(
      "active",
    );
    expect(screen.getByTestId("residency-row-ap-south").textContent).toContain(
      "off",
    );
    expect(screen.getByTestId("byok-row-k_logs_1").textContent).toContain(
      "warn",
    );
  });

  it("procurement tab flags stale documents", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-procurement"));
    expect(screen.getByTestId("procurement-row-soc2").textContent).toContain(
      "ready",
    );
    expect(
      screen.getByTestId("procurement-row-pen-test").textContent,
    ).toContain("stale");
  });

  it("policy tab shows blocking + warn consequences", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-policy"));
    expect(screen.getByTestId("policy-row-pc_1").textContent).toContain(
      "blocking",
    );
    expect(screen.getByTestId("policy-row-pc_3").textContent).toContain("warn");
  });

  it("skills tab shows visibility per skill", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-skills"));
    expect(
      screen.getByTestId("skill-row-sk_acme_refund").textContent,
    ).toContain("private");
    expect(
      screen.getByTestId("skill-row-sk_acme_returns").textContent,
    ).toContain("workspace");
  });
});
