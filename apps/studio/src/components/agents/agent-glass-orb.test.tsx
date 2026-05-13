import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentGlassOrb } from "./agent-glass-orb";

describe("AgentGlassOrb", () => {
  it("renders an accessible per-agent hue object", () => {
    render(
      <AgentGlassOrb
        agentId="agent_support"
        label="Support concierge"
        state="watching"
      />,
    );

    expect(
      screen.getByRole("img", {
        name: /Support concierge agent hue, watching/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen
        .getByTestId("agent-glass-orb")
        .style.getPropertyValue("--agent-hue"),
    ).toMatch(/^\d+$/);
  });
});
