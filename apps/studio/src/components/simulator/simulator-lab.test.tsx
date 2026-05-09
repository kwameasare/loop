import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  SimulatorLab,
  type SimulatorInvoke,
} from "@/components/simulator/simulator-lab";
import { DEFAULT_SIMULATOR_CONFIG } from "@/lib/emulator-lab";
import type {
  SimulatorTurnRatingInput,
  SimulatorTurnRatingRecord,
} from "@/lib/simulator-feedback";

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
    expect(
      screen.getByTestId("save-persona-eval-journalist"),
    ).toHaveTextContent("Eval saved");
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

  it("turns a first-proof bad rating into an eval-backed artifact", async () => {
    const invoke = vi.fn(
      async (
        _agentId: string,
        _prompt: string,
        onFrame: Parameters<SimulatorInvoke>[2],
      ) => {
        onFrame({
          type: "complete",
          payload: {
            response: {
              content: [{ type: "text", text: "Yes, always refund." }],
            },
          },
          ts: "2026-05-01T00:00:00Z",
        });
      },
    );
    const rateTurn = vi.fn(
      async (
        _agentId: string,
        input: SimulatorTurnRatingInput,
      ): Promise<SimulatorTurnRatingRecord> => ({
        id: "simrate_1",
        workspace_id: "ws_1",
        agent_id: "agent_support",
        rating: input.rating,
        prompt: input.prompt,
        final_answer: input.final_answer,
        channel: input.channel,
        trace_id: input.trace_id,
        issue_annotation: input.issue_annotation,
        candidate_artifact: {
          kind: "regression_eval_candidate",
          title: "Prevent this failure from recurring",
          expected_outcome: input.issue_annotation,
          source: "first_proof",
          trace_id: input.trace_id,
        },
        eval_case_ref: { suite_id: "suite_1", case_id: "case_1" },
        cost_usd: input.cost_usd,
        latency_ms: input.latency_ms,
        created_by: "owner-1",
        created_at: "2026-05-01T00:00:00Z",
      }),
    );
    render(
      <SimulatorLab
        agentId="agent_support"
        invoke={invoke}
        rateTurn={rateTurn}
        initialConfig={DEFAULT_SIMULATOR_CONFIG}
      />,
    );

    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "Can I get a refund after deadline?" },
    });
    fireEvent.click(screen.getByTestId("emulator-send"));

    expect(await screen.findByTestId("first-proof-rating")).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("first-proof-annotation"), {
      target: { value: "Should cite policy and escalate exceptions." },
    });
    fireEvent.click(screen.getByTestId("first-proof-rate-bad"));

    await waitFor(() => {
      expect(rateTurn).toHaveBeenCalledWith(
        "agent_support",
        expect.objectContaining({
          rating: "bad",
          prompt: "Can I get a refund after deadline?",
          final_answer: "Yes, always refund.",
          save_as_eval: true,
        }),
      );
    });
    expect(await screen.findByTestId("first-proof-result")).toHaveTextContent(
      "Eval case created: case_1",
    );
  });
});
