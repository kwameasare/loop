import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import { GovernOverview } from "./govern-overview";

describe("GovernOverview", () => {
  it("renders SSO summaries by default", () => {
    render(<GovernOverview />);
    expect(screen.getByTestId("govern-overview")).toBeInTheDocument();
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
    expect(screen.getByTestId("approval-row-apr_1").textContent).toContain("pending");
    expect(screen.getByTestId("approval-row-apr_2").textContent).toContain("approved");
    expect(screen.getByTestId("approval-row-apr_3").textContent).toContain("rejected");
    expect(screen.getByTestId("approval-row-apr_4").textContent).toContain("expired");
  });

  it("audit explorer filters by category and shows empty state", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-audit"));
    const select = screen.getByTestId("audit-category-filter") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "policy" } });
    expect(screen.getByTestId("audit-row-ev_1004")).toBeInTheDocument();
    expect(screen.queryByTestId("audit-row-ev_1001")).toBeNull();
    fireEvent.change(select, { target: { value: "billing" } });
    expect(screen.getByTestId("audit-empty")).toBeInTheDocument();
  });

  it("residency tab renders zones and BYOK key warning", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-residency"));
    expect(screen.getByTestId("residency-row-us-east").textContent).toContain("active");
    expect(screen.getByTestId("residency-row-ap-south").textContent).toContain("off");
    expect(screen.getByTestId("byok-row-k_logs_1").textContent).toContain("warn");
  });

  it("procurement tab flags stale documents", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-procurement"));
    expect(screen.getByTestId("procurement-row-soc2").textContent).toContain("ready");
    expect(screen.getByTestId("procurement-row-pen-test").textContent).toContain("stale");
  });

  it("policy tab shows blocking + warn consequences", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-policy"));
    expect(screen.getByTestId("policy-row-pc_1").textContent).toContain("blocking");
    expect(screen.getByTestId("policy-row-pc_3").textContent).toContain("warn");
  });

  it("skills tab shows visibility per skill", () => {
    render(<GovernOverview />);
    fireEvent.click(screen.getByTestId("govern-tab-skills"));
    expect(screen.getByTestId("skill-row-sk_acme_refund").textContent).toContain("private");
    expect(screen.getByTestId("skill-row-sk_acme_returns").textContent).toContain("workspace");
  });
});
