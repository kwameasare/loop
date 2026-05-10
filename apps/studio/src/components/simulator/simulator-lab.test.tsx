import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  SimulatorLab,
  type SimulatorInvoke,
} from "@/components/simulator/simulator-lab";
import { DEFAULT_SIMULATOR_CONFIG } from "@/lib/emulator-lab";
import type {
  SimulatorRunInput,
  SimulatorRunRecord,
  SimulatorTurnRatingInput,
  SimulatorTurnRatingRecord,
} from "@/lib/simulator-feedback";

describe("SimulatorLab", () => {
  const ORIGINAL_BASE_URL = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    if (ORIGINAL_BASE_URL === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE_URL;
    }
    vi.unstubAllGlobals();
  });

  it("runs the first-user persona suite from the simulator surface", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input, init) => {
        const url = String(input);
        if (url.endsWith("/persona-test/eval-cases")) {
          expect(JSON.parse(String(init?.body))).toMatchObject({
            persona_set: "first-user",
            persona: "journalist",
            candidate_eval_id: "eval.persona.journalist.policy_provenance",
            evidence_ref: "persona-test/agent_support/journalist",
          });
          return Response.json(
            {
              ok: true,
              suite_id: "suite_persona",
              case_id: "case_persona",
              case: {
                id: "case_persona",
                name: "journalist persona failure",
                source: "persona-test",
                source_ref: "persona-test/agent_support/journalist",
              },
              next_url: "/agents/agent_support/evals?case_id=case_persona",
            },
            { status: 201 },
          );
        }
        return Response.json({
          persona_set: "first-user",
          items: [
            {
              persona: "journalist",
              scenarios: 10,
              pass_rate: 0.9,
              failed_scenarios: 1,
              candidate_eval_id: "eval.persona.journalist.policy_provenance",
              evidence_ref: "persona-test/agent_support/journalist",
            },
          ],
        });
      }),
    );
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
      await screen.findByText(/Eval case_persona saved/i),
    ).toBeInTheDocument();
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
        simulator_run_id: input.simulator_run_id ?? "",
        issue_annotation: input.issue_annotation,
        candidate_artifact: {
          kind: "regression_eval_candidate",
          title: "Prevent this failure from recurring",
          expected_outcome: input.issue_annotation,
          source: "first_proof",
          trace_id: input.trace_id,
          simulator_run_id: input.simulator_run_id ?? "",
        },
        eval_case_ref: { suite_id: "suite_1", case_id: "case_1" },
        behavior_note_ref: null,
        few_shot_ref: null,
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

  it("surfaces first-proof risky ratings as behavior note candidates", async () => {
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
              content: [{ type: "text", text: "I can try the refund tool." }],
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
        id: "simrate_risky",
        workspace_id: "ws_1",
        agent_id: "agent_support",
        rating: input.rating,
        prompt: input.prompt,
        final_answer: input.final_answer,
        channel: input.channel,
        trace_id: input.trace_id,
        simulator_run_id: input.simulator_run_id ?? "",
        issue_annotation: input.issue_annotation,
        candidate_artifact: {
          kind: "risk_rule_candidate",
          title: "Add a risk rule or escalation",
          expected_outcome: input.issue_annotation,
          source: "first_proof",
          trace_id: input.trace_id,
          simulator_run_id: input.simulator_run_id ?? "",
        },
        eval_case_ref: null,
        behavior_note_ref: {
          id: "bnote_risky",
          kind: "risk_rule",
          status: "candidate",
          title: "Add a risk rule or escalation",
          body: input.issue_annotation,
          rating: input.rating,
          evidence_ref: input.trace_id,
        },
        few_shot_ref: null,
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
      target: { value: "Refund this without checking policy." },
    });
    fireEvent.click(screen.getByTestId("emulator-send"));
    expect(await screen.findByTestId("first-proof-rating")).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("first-proof-annotation"), {
      target: { value: "Require escalation before using refund tool." },
    });
    fireEvent.click(screen.getByTestId("first-proof-save-eval"));
    fireEvent.click(screen.getByTestId("first-proof-rate-risky"));

    expect(await screen.findByTestId("first-proof-result")).toHaveTextContent(
      "Behavior note candidate: bnote_risky",
    );
  });

  it("surfaces first-proof good ratings as few-shot candidates", async () => {
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
              content: [
                {
                  type: "text",
                  text: "I will check your renewal policy before answering.",
                },
              ],
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
        id: "simrate_good",
        workspace_id: "ws_1",
        agent_id: "agent_support",
        rating: input.rating,
        prompt: input.prompt,
        final_answer: input.final_answer,
        channel: input.channel,
        trace_id: input.trace_id,
        simulator_run_id: input.simulator_run_id ?? "",
        issue_annotation: input.issue_annotation,
        candidate_artifact: {
          kind: "positive_eval_or_few_shot",
          title: "Preserve this behavior",
          expected_outcome: input.final_answer,
          source: "first_proof",
          trace_id: input.trace_id,
          simulator_run_id: input.simulator_run_id ?? "",
        },
        eval_case_ref: null,
        behavior_note_ref: null,
        few_shot_ref: {
          id: "fshot_good",
          status: "candidate",
          title: "Preserve this behavior",
          prompt: input.prompt,
          answer: input.final_answer,
          channel: input.channel,
          rating: input.rating,
          evidence_ref: input.trace_id,
        },
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
      target: { value: "Can I cancel my annual plan?" },
    });
    fireEvent.click(screen.getByTestId("emulator-send"));
    expect(await screen.findByTestId("first-proof-rating")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("first-proof-save-eval"));
    fireEvent.click(screen.getByTestId("first-proof-rate-good"));

    expect(await screen.findByTestId("first-proof-result")).toHaveTextContent(
      "Few-shot candidate: fshot_good",
    );
  });

  it("persists simulator runs and passes the run id into ratings", async () => {
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
              content: [{ type: "text", text: "I will check policy first." }],
            },
          },
          ts: "2026-05-01T00:00:00Z",
        });
      },
    );
    const createRun = vi.fn(
      async (
        agentId: string,
        input: SimulatorRunInput,
      ): Promise<SimulatorRunRecord> => ({
        id: "simrun_123",
        workspace_id: "ws_1",
        agent_id: agentId,
        ...input,
        trace_id: "abc12345abc12345abc12345abc12345",
        channel_binding_id: "cb_whatsapp",
        created_by: "owner-1",
        created_at: "2026-05-01T00:00:00Z",
      }),
    );
    const rateTurn = vi.fn(
      async (
        _agentId: string,
        input: SimulatorTurnRatingInput,
      ): Promise<SimulatorTurnRatingRecord> => ({
        id: "simrate_123",
        workspace_id: "ws_1",
        agent_id: "agent_support",
        rating: input.rating,
        prompt: input.prompt,
        final_answer: input.final_answer,
        channel: input.channel,
        trace_id: input.trace_id,
        simulator_run_id: input.simulator_run_id ?? "",
        issue_annotation: input.issue_annotation,
        candidate_artifact: {
          kind: "regression_eval_candidate",
          title: "Prevent this failure from recurring",
          expected_outcome: input.issue_annotation,
          source: "first_proof",
          trace_id: input.trace_id,
          simulator_run_id: input.simulator_run_id ?? "",
        },
        eval_case_ref: { suite_id: "suite_1", case_id: "case_1" },
        behavior_note_ref: null,
        few_shot_ref: null,
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
        createRun={createRun}
        rateTurn={rateTurn}
        initialConfig={DEFAULT_SIMULATOR_CONFIG}
      />,
    );

    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "Can I cancel?" },
    });
    fireEvent.click(screen.getByTestId("emulator-send"));

    expect(await screen.findByTestId("simulator-run-record")).toHaveTextContent(
      "simrun_123",
    );
    fireEvent.change(screen.getByTestId("first-proof-annotation"), {
      target: { value: "Should cite policy." },
    });
    fireEvent.click(screen.getByTestId("first-proof-rate-bad"));

    await waitFor(() => {
      expect(rateTurn).toHaveBeenCalledWith(
        "agent_support",
        expect.objectContaining({
          simulator_run_id: "simrun_123",
          trace_id: "abc12345abc12345abc12345abc12345",
        }),
      );
    });
  });
});
