import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import AgentHistoryPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentHistoryPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
  });

  it("shows degraded handoff evidence instead of a raw route error when cp-api is unconfigured", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(await AgentHistoryPage({ params: { agent_id: "agent_history" } }));

    expect(screen.getByTestId("target-state")).toHaveAttribute(
      "data-state",
      "degraded",
    );
    expect(
      screen.getByText("History Walkthrough is degraded"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/handoff history could not load/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
  });
});
