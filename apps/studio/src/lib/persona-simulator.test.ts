import { describe, expect, it, vi } from "vitest";

import { runPersonaSimulation } from "./persona-simulator";

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
});
