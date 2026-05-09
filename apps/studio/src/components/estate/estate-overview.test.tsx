import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EstateOverview } from "@/components/estate/estate-overview";
import type { EstateHealth } from "@/lib/estate-health";

const HEALTH: EstateHealth = {
  workspace_id: "ws_1",
  generated_at: "2026-05-08T12:00:00Z",
  data_source: "live",
  provenance: ["agents.list_for_workspace", "trace_search.run"],
  summary: {
    agents_total: 12,
    agents_production: 9,
    agents_draft: 3,
    pending_handoffs: 2,
    pending_approvals: 1,
    trace_errors: 4,
    trace_count: 88,
    eval_suites: 6,
    audit_events: 50,
    open_incidents: 0,
    blocked_deploys: 1,
  },
  attention: [
    {
      id: "pending-approvals",
      severity: "critical",
      title: "1 change set needs approval",
      detail: "Release candidate cannot promote.",
      href: "/deploys",
      source: "approval_changesets",
    },
  ],
};

describe("EstateOverview", () => {
  it("renders estate metrics and source-backed attention", () => {
    render(<EstateOverview health={HEALTH} />);

    expect(screen.getByTestId("estate-data-source")).toHaveTextContent(
      "Live cp-api",
    );
    expect(screen.getByTestId("estate-overview")).toHaveTextContent("12");
    expect(screen.getByTestId("estate-attention")).toHaveTextContent(
      "1 change set needs approval",
    );
    expect(screen.getByTestId("estate-attention")).toHaveTextContent(
      "source: approval_changesets",
    );
  });

  it("shows degraded provenance instead of pretending data is live", () => {
    render(
      <EstateOverview
        health={{
          ...HEALTH,
          data_source: "unavailable",
          degraded_reason: "cp-api estate health returned 503.",
        }}
      />,
    );

    expect(screen.getByTestId("estate-data-source")).toHaveTextContent(
      "cp-api unavailable",
    );
    expect(screen.getByTestId("estate-degraded-reason")).toHaveTextContent(
      "503",
    );
  });
});
