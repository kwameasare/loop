import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AgentSimulatorPage from "./page";

describe("AgentSimulatorPage", () => {
  it("starts with empty evidence rather than fixture traces or tools", () => {
    render(<AgentSimulatorPage params={{ agent_id: "agent_sim" }} />);

    expect(screen.getByTestId("agent-simulator")).toBeInTheDocument();
    expect(screen.getByTestId("emulator-panel")).toHaveTextContent(
      "Blank run",
    );
    expect(screen.getByTestId("emulator-panel")).toHaveTextContent(
      "Send a turn to generate draft output and trace evidence.",
    );
    expect(screen.queryByText(/trace_refund_742/i)).toBeNull();
    expect(screen.queryByText(/lookup_order/i)).toBeNull();
    expect(screen.queryByText(/refund_policy_2026/i)).toBeNull();
  });
});
