import { describe, expect, it, vi } from "vitest";

import {
  resolveAdversarialCatch,
  runAdversarialProbe,
} from "./adversarial-catches";

describe("adversarial catches client", () => {
  it("returns a local calm catch without a cp-api base URL", async () => {
    const response = await runAdversarialProbe(
      "agent_support",
      {
        rule_id: "sentence_refund_cap",
        rule_text: "Never approve refunds over $500.",
        risk_class: "high",
      },
      { baseUrl: "" },
    );

    expect(response.run.status).toBe("completed");
    expect(response.catches[0]).toMatchObject({
      status: "open",
      risk_class: "high",
    });
    expect(response.catches[0]?.question).toContain("cumulatively");
  });

  it("posts probe runs and catch resolutions to agent-scoped endpoints", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/adversarial-probes/run")) {
        return Response.json({
          run: {
            id: "probe_1",
            workspace_id: "workspace_1",
            agent_id: "agent_support",
            rule_id: "sentence_refund_cap",
            risk_class: "high",
            budget_tokens: 2000,
            budget_tokens_used: 640,
            status: "completed",
            created_by: "owner",
            created_at: "2026-05-09T00:00:00Z",
          },
          catches: [],
        });
      }
      return Response.json({
        id: "catch_1",
        workspace_id: "workspace_1",
        agent_id: "agent_support",
        probe_run_id: "probe_1",
        rule_id: "sentence_refund_cap",
        rule_text: "Never approve refunds over $500.",
        question: "Should this cap apply cumulatively?",
        generated_scenario: "Two refund calls.",
        evidence_ref: "adversarial_probe/probe_1/sentence_refund_cap",
        risk_class: "high",
        status: "resolved",
        resolution: null,
        eval_case_refs: [{ suite_id: "suite_1", case_id: "case_1" }],
        created_at: "2026-05-09T00:00:00Z",
        updated_at: "2026-05-09T00:00:00Z",
      });
    });

    await runAdversarialProbe(
      "agent_support",
      {
        rule_id: "sentence_refund_cap",
        rule_text: "Never approve refunds over $500.",
      },
      { baseUrl: "https://cp.test", fetcher, token: "tok" },
    );
    const resolved = await resolveAdversarialCatch(
      "agent_support",
      "catch_1",
      {
        intended_interpretation: "Cap applies cumulatively.",
        rejected_interpretation: "Cap applies per tool call.",
        create_eval_cases: true,
      },
      { baseUrl: "https://cp.test", fetcher, token: "tok" },
    );

    expect(resolved.status).toBe("resolved");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_support/adversarial-probes/run",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ authorization: "Bearer tok" }),
      }),
    );
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_support/catches/catch_1/resolve",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ authorization: "Bearer tok" }),
      }),
    );
  });
});
