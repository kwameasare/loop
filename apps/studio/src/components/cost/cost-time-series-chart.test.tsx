import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CostTimeSeriesChart } from "./cost-time-series-chart";
import type { UsageRecord } from "@/lib/costs";

const WS = "ws_t";
const DAY = 24 * 60 * 60 * 1000;
const START = Date.UTC(2026, 3, 1);

function rec(
  agent_id: string,
  agent_name: string,
  metric: UsageRecord["metric"],
  quantity: number,
  day_ms: number,
): UsageRecord {
  return { workspace_id: WS, agent_id, agent_name, metric, quantity, day_ms };
}

describe("CostTimeSeriesChart", () => {
  const records: UsageRecord[] = [
    rec("a", "Alpha", "tokens.in", 100, START),
    rec("b", "Bravo", "tokens.in", 50, START),
    rec("a", "Alpha", "tokens.in", 200, START + DAY),
  ];

  it("renders a point per day in the window plus axis labels", () => {
    render(
      <CostTimeSeriesChart
        records={records}
        workspace_id={WS}
        window_start_ms={START}
        window_end_ms={START + 3 * DAY}
      />,
    );
    expect(screen.getByTestId("cost-point-0")).toBeInTheDocument();
    expect(screen.getByTestId("cost-point-1")).toBeInTheDocument();
    expect(screen.getByTestId("cost-point-2")).toBeInTheDocument();
    expect(screen.getAllByText(/Apr/).length).toBeGreaterThan(0);
  });

  it("shows tooltip with per-agent breakdown on hover", () => {
    render(
      <CostTimeSeriesChart
        records={records}
        workspace_id={WS}
        window_start_ms={START}
        window_end_ms={START + 3 * DAY}
      />,
    );
    fireEvent.mouseEnter(screen.getByTestId("cost-point-0"));
    expect(screen.getByTestId("cost-tooltip-day")).toHaveTextContent("Apr 1");
    expect(screen.getByTestId("cost-tooltip-total")).toHaveTextContent("$1.50");
    expect(screen.getByTestId("cost-tooltip-agent-a")).toHaveTextContent("Alpha: $1.00");
    expect(screen.getByTestId("cost-tooltip-agent-b")).toHaveTextContent("Bravo: $0.50");
  });

  it("agent multi-select filters the series", async () => {
    render(
      <CostTimeSeriesChart
        records={records}
        workspace_id={WS}
        window_start_ms={START}
        window_end_ms={START + 3 * DAY}
      />,
    );
    const bravoLabel = screen.getByTestId("cost-agent-toggle-b");
    const checkbox = bravoLabel.querySelector("input")!;
    expect(checkbox).toBeChecked();
    await act(async () => {
      fireEvent.click(checkbox);
    });
    expect(checkbox).not.toBeChecked();
    fireEvent.mouseEnter(screen.getByTestId("cost-point-0"));
    expect(screen.queryByTestId("cost-tooltip-agent-b")).toBeNull();
    expect(screen.getByTestId("cost-tooltip-agent-a")).toBeInTheDocument();
    expect(screen.getByTestId("cost-tooltip-total")).toHaveTextContent("$1.00");
  });
});
