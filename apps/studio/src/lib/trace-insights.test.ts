import { describe, expect, it, vi } from "vitest";

import { fetchContextAblation, fetchLatencyBudget } from "./trace-insights";
import type { Trace } from "./traces";

const trace: Trace = {
  id: "trace_1",
  spans: [
    {
      id: "span_model",
      parent_id: null,
      name: "model.generate",
      service: "runtime",
      kind: "server",
      category: "model",
      start_ns: 0,
      end_ns: 800_000_000,
      status: "ok",
      attributes: {},
      events: [],
    },
  ],
};

describe("trace insights client", () => {
  it("loads latency budgets and context ablations through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/latency-budget")) {
        return Response.json({
          trace_id: "trace_1",
          target_latency_ms: 900,
          total_latency_ms: 1200,
          gap_ms: 300,
          spans: [{ id: "span_model", label: "model", ms: 800, kind: "model" }],
          suggestions: [
            {
              id: "swap_model",
              label: "Swap model",
              saves_ms: 280,
              quality_delta: -0.02,
              evidence_ref: "trace_1/span_model",
            },
          ],
        });
      }
      return Response.json({
        turn_id: "turn_1",
        items: [
          {
            id: "prompt_sections",
            label: "Prompt sections",
            enabled: true,
            cost_delta_pct: 0,
            latency_delta_ms: 0,
            quality_delta: 0,
            evidence_ref: "turn_1/context/prompt",
          },
        ],
      });
    });

    const latency = await fetchLatencyBudget("agent_1", trace, 900, {
      baseUrl: "https://cp.test",
      fetcher,
    });
    const ablation = await fetchContextAblation(
      "agent_1",
      "turn_1",
      { prompt_sections: true },
      { baseUrl: "https://cp.test", fetcher },
    );

    expect(latency.gap_ms).toBe(300);
    expect(ablation.items[0]?.id).toBe("prompt_sections");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_1/latency-budget",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_1/context-ablation",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("does not fabricate trace insights without cp-api", async () => {
    await expect(
      fetchLatencyBudget("agent_1", trace, 900, { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      fetchContextAblation(
        "agent_1",
        "turn_1",
        { prompt_sections: true },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic trace insights explicitly opt-in", async () => {
    await expect(
      fetchLatencyBudget("agent_1", trace, 900, {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toMatchObject({
      trace_id: "trace_1",
      suggestions: expect.arrayContaining([
        expect.objectContaining({ id: "swap_model" }),
      ]),
    });

    await expect(
      fetchContextAblation(
        "agent_1",
        "turn_1",
        { prompt_sections: false },
        { baseUrl: "", allowFixture: true },
      ),
    ).resolves.toMatchObject({
      items: expect.arrayContaining([
        expect.objectContaining({
          id: "prompt_sections",
          cost_delta_pct: -14,
        }),
      ]),
    });
  });
});
