import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EditHistoryScrubber } from "@/components/agents/edit-history-scrubber";

describe("EditHistoryScrubber", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    vi.unstubAllGlobals();
  });

  it("renders edit history loaded from cp-api", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        Response.json({
          items: [
            {
              id: "edit_1",
              at: "2026-05-09T10:00:00Z",
              actor: "maya@acme.test",
              label: "Refund behavior updated",
              object_state: "draft",
              content_hash: "hash_refund_1",
              summary: "Added Spanish refund replay coverage.",
            },
          ],
        }),
      ),
    );

    render(<EditHistoryScrubber agentId="agent_support" />);

    expect(await screen.findByTestId("edit-history-scrubber")).toHaveTextContent(
      "Refund behavior updated",
    );
  });

  it("does not imply there is no edit history when cp-api is unavailable", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    render(<EditHistoryScrubber agentId="agent_support" />);

    await waitFor(() => {
      expect(screen.getByTestId("edit-history-unavailable")).toHaveTextContent(
        /LOOP_CP_API_BASE_URL is required/i,
      );
    });
    expect(
      screen.queryByText(/No edit history has been recorded/i),
    ).not.toBeInTheDocument();
  });
});
