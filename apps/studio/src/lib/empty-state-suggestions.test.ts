import { describe, expect, it, vi } from "vitest";

import {
  acceptEmptyStateSuggestion,
  fetchEmptyStateSuggestions,
} from "./empty-state-suggestions";

describe("empty-state suggestion client", () => {
  it("fetches personalized suggestions from cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        items: [
          {
            id: "starter_eval_from_traces",
            title: "Save 12 recent turns as a starter eval suite.",
            action_label: "Create starter suite",
            evidence_ref: "empty-state/agent_1/evals/recent-traces",
          },
        ],
      }),
    );

    const result = await fetchEmptyStateSuggestions("agent_1", "evals", {
      baseUrl: "https://cp.test",
      fetcher,
    });

    expect(result[0]?.id).toBe("starter_eval_from_traces");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_1/empty-state-suggestions?surface=evals",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("does not fabricate suggestions without cp-api unless fixture mode is explicit", async () => {
    await expect(
      fetchEmptyStateSuggestions("agent_1", "kb", { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      fetchEmptyStateSuggestions("agent_1", "kb", {
        baseUrl: "",
        allowFixture: true,
      }),
    ).resolves.toEqual([
      expect.objectContaining({
        id: "kb_starter",
        action_label: "Review KB gaps",
      }),
    ]);
  });

  it("accepts suggestions through a mutating cp-api call", async () => {
    const fetcher = vi.fn<typeof fetch>(async (_input, init) => {
      expect(JSON.parse(String(init?.body))).toEqual({ surface: "evals" });
      return Response.json({
        ok: true,
        suggestion_id: "starter_eval_from_traces",
        surface: "evals",
        title: "Created starter eval suite with 2 case(s).",
        created_refs: ["eval-suite/suite_1", "eval/case_1"],
        next_url: "/agents/agent_1/evals?suite_id=suite_1",
        evidence_ref: "empty-state/agent_1/evals/starter_eval_from_traces",
      });
    });

    const result = await acceptEmptyStateSuggestion(
      "agent_1",
      "evals",
      "starter_eval_from_traces",
      { baseUrl: "https://cp.test/v1", fetcher },
    );

    expect(result.created_refs).toContain("eval/case_1");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_1/empty-state-suggestions/starter_eval_from_traces/accept",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("never falls back for accepted actions", async () => {
    await expect(
      acceptEmptyStateSuggestion("agent_1", "evals", "starter_eval_from_traces", {
        baseUrl: "",
      }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });
});
