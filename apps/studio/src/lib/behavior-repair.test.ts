import { describe, expect, it, vi } from "vitest";

import { saveObservedFailureEval } from "./behavior-repair";

const INPUT = {
  sentence_id: "sentence_purpose_cancel",
  sentence_text: "Cite the May 2026 policy before refund windows.",
  trace_id: "trace_refund_742",
  failure_reason: "The production answer cited the archived policy.",
  expected_outcome: "The answer cites the current May 2026 refund policy.",
  proposed_fix:
    "Require current policy citation before quoting refund windows.",
  replay_ref: "replay/run/trace_refund_742/fixed",
};

describe("behavior repair client", () => {
  it("returns a local observed-failure eval case without a cp-api base URL", async () => {
    const response = await saveObservedFailureEval("agt_1", INPUT, {
      baseUrl: "",
    });

    expect(response.ok).toBe(true);
    expect(response.case_id).toBe("case_sentence_purpose_cancel");
    expect(response.case?.source).toBe("behavior-fix");
    expect(response.case?.expected).toMatchObject({
      proposed_fix: INPUT.proposed_fix,
    });
  });

  it("posts observed failures to the agent-scoped eval endpoint", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        ok: true,
        suite_id: "suite_1",
        case_id: "case_1",
      }),
    );

    const response = await saveObservedFailureEval("agt_1", INPUT, {
      baseUrl: "https://cp.test",
      fetcher,
      token: "tok",
    });

    expect(response.case_id).toBe("case_1");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/eval-cases/from-observed-failure",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ authorization: "Bearer tok" }),
      }),
    );
    const [, init] = fetcher.mock.calls[0]!;
    expect(JSON.parse(String(init?.body))).toMatchObject({
      sentence_id: INPUT.sentence_id,
      trace_id: INPUT.trace_id,
      proposed_fix: INPUT.proposed_fix,
    });
  });
});
