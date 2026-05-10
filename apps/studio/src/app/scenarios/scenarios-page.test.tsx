import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ScenariosDemoPage from "./page";

describe("ScenariosDemoPage", () => {
  it("renders the merged agent-flow journeys before the canonical scenario set", () => {
    render(<ScenariosDemoPage />);

    expect(
      screen.getByRole("heading", {
        name: "Merged agent-flow acceptance journeys",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Canonical north-star scenarios" }),
    ).toBeInTheDocument();

    const support = screen.getByTestId(
      "journey-card-flow-a-create-billing-support-agent",
    );
    expect(support).toHaveTextContent("Create a new billing support agent");
    expect(support).toHaveTextContent("commitment_document.id");
    expect(support).toHaveTextContent("/agents/[agent_id]/contract");

    const migration = screen.getByTestId(
      "journey-card-flow-b-migrate-from-botpress",
    );
    expect(migration).toHaveTextContent("Migrate from Botpress");
    expect(migration).toHaveTextContent("parity.report_id");
    expect(migration).toHaveTextContent("/migrate/parity");

    const journeyCards = screen.getAllByTestId(/^journey-card-/);
    expect(journeyCards).toHaveLength(5);
    const canonical = screen.getByTestId("scenario-card-maya-migrates-botpress");
    expect(within(canonical).getByText(/Maya migrates/)).toBeInTheDocument();
  });
});
