import { describe, expect, it, vi } from "vitest";

import { fetchCommentThreads, FIXTURE_THREADS } from "./comments";

describe("comment thread client", () => {
  it("loads workspace comment threads from cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      new Response(
        JSON.stringify({
          items: [
            {
              id: "th_live_refund",
              agentId: "agent_support",
              anchor: {
                objectId: "trace-prod-1",
                kind: "transcript_turn",
                authoredAt: "v23",
              },
              observedAt: "v23",
              comments: [],
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const result = await fetchCommentThreads("ws_review", {
      baseUrl: "https://cp.example.test/v1",
      fetcher,
    });

    expect(result.items[0]?.id).toBe("th_live_refund");
    const [url, init] = fetcher.mock.calls[0]!;
    expect(url).toBe(
      "https://cp.example.test/v1/workspaces/ws_review/comment-threads",
    );
    expect(init?.method).toBe("GET");
  });

  it("does not fabricate workspace comments without cp-api", async () => {
    await expect(fetchCommentThreads("ws_review", { baseUrl: "" })).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required",
    );
  });

  it("keeps deterministic comment threads explicitly opt-in", async () => {
    await expect(
      fetchCommentThreads("ws_review", { baseUrl: "", allowFixture: true }),
    ).resolves.toEqual({ items: [...FIXTURE_THREADS] });
  });
});
