import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_review", name: "Review Workspace" },
    isLoading: false,
  }),
}));

describe("CollaborateReviewPage", () => {
  const fetchMock = vi.fn<typeof fetch>();
  let CollaborateReviewPage: typeof import("./page").default;

  beforeEach(async () => {
    vi.stubEnv("NEXT_PUBLIC_LOOP_API_URL", "https://cp.example.test");
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    CollaborateReviewPage = (await import("./page")).default;
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("shows degraded collaboration evidence while preserving the review workspace", async () => {
    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/comment-threads")) {
        return new Response(JSON.stringify({ items: [] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ detail: "unavailable" }), {
        status: 503,
        headers: { "content-type": "application/json" },
      });
    });

    render(<CollaborateReviewPage />);

    await waitFor(() => {
      const state = screen.getByTestId("target-state");
      expect(state).toHaveAttribute("data-state", "degraded");
      expect(state).toHaveTextContent(/Collaboration evidence is degraded/i);
      expect(state).toHaveTextContent(/changeset, comment, and pair-debug/i);
      expect(state).toHaveTextContent(/cp-api GET \/traces/i);
    });
    expect(screen.getByTestId("collaborate-review-page")).toBeInTheDocument();
    expect(screen.getByTestId("changeset-empty")).toBeInTheDocument();
    expect(screen.getByTestId("comments-empty")).toBeInTheDocument();
  });

  it("renders live workspace comment threads from the control plane", async () => {
    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/comment-threads")) {
        return new Response(
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
                comments: [
                  {
                    id: "cmt_live_refund",
                    threadId: "th_live_refund",
                    authorId: "reviewer-1",
                    authorDisplay: "Reviewer",
                    body: "The agent should refund premium customers directly.",
                    createdAt: "2026-05-09T00:00:00Z",
                    anchor: {
                      objectId: "trace-prod-1",
                      kind: "transcript_turn",
                      authoredAt: "v23",
                    },
                    evidenceRef: "audit/comments/cmt_live_refund",
                  },
                ],
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      if (url.includes("/audit/events")) {
        return new Response(JSON.stringify({ items: [], total: 0 }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(
        JSON.stringify({
          items: [],
          next_cursor: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });

    render(<CollaborateReviewPage />);

    await waitFor(() => {
      expect(
        screen.getByTestId("comment-thread-th_live_refund"),
      ).toBeInTheDocument();
    });
    expect(screen.queryByTestId("comments-empty")).not.toBeInTheDocument();
    expect(
      screen.getByText(/refund premium customers directly/i),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "https://cp.example.test/v1/workspaces/ws_review/comment-threads",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
