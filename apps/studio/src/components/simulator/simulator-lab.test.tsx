import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SimulatorLab } from "@/components/simulator/simulator-lab";
import { DEFAULT_SIMULATOR_CONFIG } from "@/lib/emulator-lab";

describe("SimulatorLab", () => {
  it("runs the first-user persona suite from the simulator surface", async () => {
    render(
      <SimulatorLab
        agentId="agent_support"
        invoke={vi.fn().mockResolvedValue(undefined)}
        initialConfig={DEFAULT_SIMULATOR_CONFIG}
      />,
    );

    expect(screen.getByTestId("persona-simulator-panel")).toHaveTextContent(
      "Run persona suite",
    );
    fireEvent.click(screen.getByTestId("run-persona-suite"));

    expect(await screen.findByTestId("persona-results")).toHaveTextContent(
      "Journalist",
    );
    fireEvent.click(screen.getByTestId("save-persona-eval-journalist"));
    expect(screen.getByTestId("save-persona-eval-journalist")).toHaveTextContent(
      "Eval saved",
    );
  });

  it("maps single-key channel switching to Slack, WhatsApp, SMS, and voice", () => {
    render(
      <SimulatorLab
        agentId="agent_support"
        invoke={vi.fn().mockResolvedValue(undefined)}
        initialConfig={{ ...DEFAULT_SIMULATOR_CONFIG, channel: "web" }}
      />,
    );

    fireEvent.keyDown(window, { key: "1" });
    expect(screen.getByTestId("sim-channel-slack")).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    fireEvent.keyDown(window, { key: "2" });
    expect(screen.getByTestId("sim-channel-whatsapp")).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    fireEvent.keyDown(window, { key: "3" });
    expect(screen.getByTestId("sim-channel-sms")).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    fireEvent.keyDown(window, { key: "4" });
    expect(screen.getByTestId("sim-channel-voice")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
