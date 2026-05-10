import { describe, expect, it, vi } from "vitest";

import {
  runPersonaSimulation,
  savePersonaFailureAsEvalCase,
} from "./persona-simulator";

describe("persona simulator client", () => {
  it("runs persona simulations through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (_input, init) => {
      expect(JSON.parse(String(init?.body))).toMatchObject({
        persona_set: "first-user",
      });
      return Response.json({
        persona_set: "first-user",
        items: [
          {
            persona: "journalist",
            scenarios: 10,
            pass_rate: 0.93,
            failed_scenarios: 1,
            candidate_eval_id: "eval_live_journalist",
            evidence_ref: "persona-test/live/journalist",
          },
        ],
      });
    });

    const result = await runPersonaSimulation("agent_1", "first-user", {
      baseUrl: "https://cp.test",
      fetcher,
    });

    expect(result.items[0]?.candidate_eval_id).toBe("eval_live_journalist");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_1/persona-test",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("does not fabricate persona simulations without cp-api", async () => {
    await expect(
      runPersonaSimulation("agent_1", "first-user", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic persona simulations explicitly opt-in", async () => {
    await expect(
      runPersonaSimulation("agent_1", "first-user", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      items: expect.arrayContaining([
        expect.objectContaining({ persona: "journalist" }),
      ]),
    });
  });

  it("saves persona failures as eval cases with provenance", async () => {
    const fetcher = vi.fn<typeof fetch>(async (_input, init) => {
      expect(JSON.parse(String(init?.body))).toMatchObject({
        persona_set: "first-user",
        persona: "journalist",
        candidate_eval_id: "eval.persona.journalist",
        evidence_ref: "persona-test/agent_1/journalist",
        expected_behavior: "Keep citations grounded for journalist questions.",
        risk_tags: ["persona-test", "journalist"],
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
            source_ref: "persona-test/agent_1/journalist",
          },
          next_url: "/agents/agent_1/evals?case_id=case_persona",
        },
        { status: 201 },
      );
    });

    const result = await savePersonaFailureAsEvalCase(
      "agent_1",
      {
        personaSet: "first-user",
        item: {
          persona: "journalist",
          scenarios: 10,
          pass_rate: 0.9,
          failed_scenarios: 1,
          candidate_eval_id: "eval.persona.journalist",
          evidence_ref: "persona-test/agent_1/journalist",
        },
        expectedBehavior: "Keep citations grounded for journalist questions.",
      },
      {
        baseUrl: "https://cp.test/v1",
        fetcher,
      },
    );

    expect(result.case_id).toBe("case_persona");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_1/persona-test/eval-cases",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
