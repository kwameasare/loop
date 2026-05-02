import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WorkspaceKpiCards } from "./workspace-kpi-cards";

describe("WorkspaceKpiCards", () => {
  it("renders three cards with formatted amounts and deltas", () => {
    render(
      <WorkspaceKpiCards
        kpis={{
          today_cents: 100,
          yesterday_cents: 80,
          mtd_cents: 350,
          prev_month_cents: 9_000, // 30-day month → prior MTD-equivalent at day 10 = 3000c
          projected_eom_cents: 1_050,
          days_elapsed: 10,
          days_in_month: 30,
        }}
      />,
    );
    expect(screen.getByTestId("kpi-today-amount")).toHaveTextContent("$1.00");
    expect(screen.getByTestId("kpi-today-delta")).toHaveTextContent("+25.0%");
    expect(screen.getByTestId("kpi-mtd-amount")).toHaveTextContent("$3.50");
    // 350 vs 3000 is heavily down → delta should be negative
    expect(screen.getByTestId("kpi-mtd-delta").textContent).toMatch(/−/);
    expect(screen.getByTestId("kpi-mtd-caption")).toHaveTextContent(
      "10 of 30 days",
    );
    expect(screen.getByTestId("kpi-eom-amount")).toHaveTextContent("$10.50");
  });

  it("falls back to em-dash delta when prior period is zero", () => {
    render(
      <WorkspaceKpiCards
        kpis={{
          today_cents: 100,
          yesterday_cents: 0,
          mtd_cents: 0,
          prev_month_cents: 0,
          projected_eom_cents: 0,
          days_elapsed: 1,
          days_in_month: 30,
        }}
      />,
    );
    expect(screen.getByTestId("kpi-today-delta")).toHaveTextContent("—");
  });
});
