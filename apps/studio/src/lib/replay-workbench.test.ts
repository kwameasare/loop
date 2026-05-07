import { describe, expect, it, vi } from "vitest";

import { fetchReplayWorkbenchModel } from "./replay-workbench";

describe("fetchReplayWorkbenchModel", () => {
  it("builds risky replay candidates from live traces", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      new Response(
        JSON.stringify({
          items: [
            {
              workspace_id: "ws-1",
              trace_id: "e".repeat(32),
              turn_id: "11111111-1111-4111-8111-111111111111",
              conversation_id: "22222222-2222-4222-8222-222222222222",
              agent_id: "33333333-3333-4333-8333-333333333333",
              started_at: "2026-05-07T12:00:00Z",
              duration_ms: 300,
              span_count: 5,
              error: true,
            },
            {
              workspace_id: "ws-1",
              trace_id: "a".repeat(32),
              turn_id: "44444444-4444-4444-8444-444444444444",
              conversation_id: "55555555-5555-4555-8555-555555555555",
              agent_id: "66666666-6666-4666-8666-666666666666",
              started_at: "2026-05-07T12:01:00Z",
              duration_ms: 220,
              span_count: 3,
              error: false,
            },
          ],
          next_cursor: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const model = await fetchReplayWorkbenchModel("ws-1", {
      baseUrl: "https://cp.example.test/v1",
      fetcher,
    });

    expect(model.conversations[0]).toMatchObject({
      traceId: "e".repeat(32),
      risk: "high",
    });
    expect(model.selectedReplay.diffRows[1].status).toBe("regressed");
    expect(model.scenes[0].linkedTraceId).toBe("e".repeat(32));
  });
});
