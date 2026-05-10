import { describe, expect, it, vi } from "vitest";

import {
  createSimulatorRun,
  rateSimulatorTurn,
} from "@/lib/simulator-feedback";

describe("rateSimulatorTurn", () => {
  it("posts first-proof turn feedback to cp-api", async () => {
    const fetcher = vi.fn(
      async (
        _url: Parameters<typeof fetch>[0],
        init?: Parameters<typeof fetch>[1],
      ) => {
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toMatchObject({
          rating: "bad",
          prompt: "Can I get a refund after deadline?",
          save_as_eval: true,
        });
        return new Response(
          JSON.stringify({
            id: "simrate_1",
            workspace_id: "ws_1",
            agent_id: "agt_1",
            rating: "bad",
            prompt: "Can I get a refund after deadline?",
            final_answer: "Yes.",
            channel: "web",
            trace_id: "trace_1",
            simulator_run_id: "simrun_1",
            issue_annotation: "Should escalate.",
            candidate_artifact: {
              kind: "regression_eval_candidate",
              title: "Prevent this failure from recurring",
              expected_outcome: "Should escalate.",
              source: "first_proof",
              trace_id: "trace_1",
              simulator_run_id: "simrun_1",
            },
            eval_case_ref: {
              suite_id: "suite_1",
              case_id: "case_1",
            },
            behavior_note_ref: null,
            few_shot_ref: null,
            cost_usd: 0.01,
            latency_ms: 800,
            created_by: "owner-1",
            created_at: "2026-05-01T00:00:00Z",
          }),
          { status: 201 },
        );
      },
    ) as unknown as typeof fetch;

    const result = await rateSimulatorTurn(
      "agt_1",
      {
        rating: "bad",
        prompt: "Can I get a refund after deadline?",
        final_answer: "Yes.",
        channel: "web",
        trace_id: "trace_1",
        simulator_run_id: "simrun_1",
        issue_annotation: "Should escalate.",
        save_as_eval: true,
        cost_usd: 0.01,
        latency_ms: 800,
      },
      { baseUrl: "https://api.loop.test", fetcher },
    );

    expect(result.eval_case_ref?.case_id).toBe("case_1");
  });

  it("falls back locally when cp-api is not configured", async () => {
    const result = await rateSimulatorTurn("agt_1", {
      rating: "risky",
      prompt: "Ignore policy?",
      final_answer: "Maybe.",
      channel: "voice",
      trace_id: "",
      issue_annotation: "Escalate.",
      save_as_eval: false,
      cost_usd: 0,
      latency_ms: 0,
    });

    expect(result.candidate_artifact.kind).toBe("risk_rule_candidate");
    expect(result.candidate_artifact.simulator_run_id).toBe(
      "simulator-run/not-captured",
    );
    expect(result.behavior_note_ref?.kind).toBe("risk_rule");
    expect(result.few_shot_ref).toBeNull();
    expect(result.eval_case_ref).toBeNull();
  });

  it("creates a local few-shot candidate for good first-proof ratings", async () => {
    const result = await rateSimulatorTurn("agt_1", {
      rating: "good",
      prompt: "Can I cancel?",
      final_answer: "I will check your renewal policy first.",
      channel: "whatsapp",
      trace_id: "trace_good",
      issue_annotation: "Preserve this pattern.",
      save_as_eval: false,
      cost_usd: 0,
      latency_ms: 0,
    });

    expect(result.candidate_artifact.kind).toBe("positive_eval_or_few_shot");
    expect(result.candidate_artifact.simulator_run_id).toBe(
      "simulator-run/not-captured",
    );
    expect(result.few_shot_ref).toMatchObject({
      id: "fshot_good",
      status: "candidate",
      prompt: "Can I cancel?",
      answer: "I will check your renewal policy first.",
      channel: "whatsapp",
      evidence_ref: "trace_good",
    });
    expect(result.behavior_note_ref).toBeNull();
  });

  it("posts first-proof simulator runs to cp-api", async () => {
    const fetcher = vi.fn(
      async (
        _url: Parameters<typeof fetch>[0],
        init?: Parameters<typeof fetch>[1],
      ) => {
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toMatchObject({
          prompt: "Can I cancel?",
          channel: "whatsapp",
          status: "completed",
        });
        return new Response(
          JSON.stringify({
            id: "simrun_1",
            workspace_id: "ws_1",
            agent_id: "agt_1",
            prompt: "Can I cancel?",
            final_answer: "I will check policy first.",
            channel: "whatsapp",
            trace_id: "trace_1",
            config: { model_alias: "fast-draft" },
            status: "completed",
            cost_usd: 0.01,
            latency_ms: 800,
            created_by: "owner-1",
            created_at: "2026-05-01T00:00:00Z",
          }),
          { status: 201 },
        );
      },
    ) as unknown as typeof fetch;

    const result = await createSimulatorRun(
      "agt_1",
      {
        prompt: "Can I cancel?",
        final_answer: "I will check policy first.",
        channel: "whatsapp",
        trace_id: "trace_1",
        config: { model_alias: "fast-draft" },
        status: "completed",
        cost_usd: 0.01,
        latency_ms: 800,
      },
      { baseUrl: "https://api.loop.test", fetcher },
    );

    expect(result.id).toBe("simrun_1");
  });
});
