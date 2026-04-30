import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { CostDashboard } from "./cost-dashboard";
import type { UsageRecord } from "@/lib/costs";

const WS = "ws_x";
const APRIL_1 = Date.UTC(2026, 3, 1);
const MAY_1 = Date.UTC(2026, 4, 1);

const RECORDS: UsageRecord[] = [
  {
    workspace_id: WS,
    agent_id: "agt_a",
    agent_name: "Agent A",
    metric: "tokens.in",
    quantity: 1000,
    day_ms: APRIL_1,
  },
  {
    workspace_id: WS,
    agent_id: "agt_b",
    agent_name: "Agent B",
    metric: "tokens.out",
    quantity: 500,
    day_ms: APRIL_1,
  },
];

describe("CostDashboard", () => {
  it("renders MTD total formatted as USD", () => {
    render(
      <CostDashboard
        records={RECORDS}
        workspace_id={WS}
        period_start_ms={APRIL_1}
        period_end_ms={MAY_1}
      />,
    );
    // 1000 * 1c + 500 * 3c = 2500c = $25.00
    expect(screen.getByTestId("mtd-amount")).toHaveTextContent("$25.00");
  });

  it("lists per-agent rows ordered by spend", () => {
    render(
      <CostDashboard
        records={RECORDS}
        workspace_id={WS}
        period_start_ms={APRIL_1}
        period_end_ms={MAY_1}
      />,
    );
    expect(screen.getByTestId("agent-row-agt_b")).toBeInTheDocument();
    expect(screen.getByTestId("agent-row-agt_a")).toBeInTheDocument();
    const rows = screen.getAllByTestId(/agent-row-/);
    expect(rows[0]).toHaveTextContent("Agent B");
  });

  it("shows empty state when no records match", () => {
    render(
      <CostDashboard
        records={[]}
        workspace_id={WS}
        period_start_ms={APRIL_1}
        period_end_ms={MAY_1}
      />,
    );
    expect(screen.getByTestId("mtd-amount")).toHaveTextContent("$0.00");
    expect(screen.getByTestId("agents-table")).toHaveTextContent(
      "No usage in this period.",
    );
  });
});
