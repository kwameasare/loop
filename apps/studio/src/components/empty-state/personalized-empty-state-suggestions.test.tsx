import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PersonalizedEmptyStateSuggestions } from "./personalized-empty-state-suggestions";

describe("PersonalizedEmptyStateSuggestions", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    vi.unstubAllGlobals();
  });

  it("renders backend-sourced personalized starting points", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        items: [
          {
            id: "evals_starter",
            title: "Save these 12 turns from yesterday as a starter eval suite.",
            action_label: "Create starter suite",
            evidence_ref: "empty-state/agent_support/evals",
          },
        ],
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    render(
      <PersonalizedEmptyStateSuggestions
        agentId="agent_support"
        surface="evals"
      />,
    );

    expect(
      await screen.findByTestId("personalized-empty-evals"),
    ).toHaveTextContent("Save these 12 turns from yesterday");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_support/empty-state-suggestions?surface=evals",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("does not fabricate suggestions when workspace evidence is unavailable", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    render(
      <PersonalizedEmptyStateSuggestions agentId="agent_support" surface="kb" />,
    );

    expect(
      await screen.findByText("Personalized suggestions unavailable"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Three KB chunks/i)).not.toBeInTheDocument();
  });
});
