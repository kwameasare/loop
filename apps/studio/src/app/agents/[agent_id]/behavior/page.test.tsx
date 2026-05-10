import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import AgentBehaviorPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentBehaviorPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
  });

  it("surfaces behavior load degradation instead of showing fixture behavior as live", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(await AgentBehaviorPage({ params: { agent_id: "agent_support" } }));

    expect(screen.getByTestId("behavior-editor")).toBeInTheDocument();
    expect(screen.getByText("Behavior data is degraded")).toBeInTheDocument();
    expect(
      screen.getAllByText(/control-plane versions endpoint/i).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("No behavior sections yet")).toBeInTheDocument();
    expect(
      screen.queryByText("Acme Support Concierge"),
    ).not.toBeInTheDocument();
  });
});
