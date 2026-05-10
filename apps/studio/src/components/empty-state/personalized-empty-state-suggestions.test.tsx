import { fireEvent, render, screen } from "@testing-library/react";
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

  it("persists accepted suggestions through the backend action", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        Response.json({
          items: [
            {
              id: "starter_eval_from_traces",
              title: "Save 12 recent turns as a starter eval suite.",
              action_label: "Create starter suite",
              evidence_ref: "empty-state/agent_support/evals/recent-traces",
            },
          ],
        }),
      ),
    );
    const acceptSuggestion = vi.fn(async () => ({
      ok: true as const,
      suggestion_id: "starter_eval_from_traces",
      surface: "evals" as const,
      title: "Created starter eval suite with 12 case(s).",
      created_refs: ["eval-suite/suite_1", "eval/case_1"],
      next_url: "/agents/agent_support/evals?suite_id=suite_1",
      evidence_ref: "empty-state/agent_support/evals/starter_eval_from_traces",
    }));

    render(
      <PersonalizedEmptyStateSuggestions
        agentId="agent_support"
        surface="evals"
        acceptSuggestion={acceptSuggestion}
      />,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: /create starter suite/i }),
    );

    expect(
      await screen.findByText(/Created starter eval suite/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open result/i })).toHaveAttribute(
      "href",
      "/agents/agent_support/evals?suite_id=suite_1",
    );
    expect(acceptSuggestion).toHaveBeenCalledWith(
      "agent_support",
      "evals",
      "starter_eval_from_traces",
    );
  });

  it("routes no-trace eval states to the simulator instead of claiming eval creation", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        Response.json({
          items: [
            {
              id: "collect_first_proof_traces",
              title:
                "Run first proof or production turns before Studio can create a starter eval suite.",
              action_label: "Open simulator",
              evidence_ref: "empty-state/agent_support/evals/no-traces",
            },
          ],
        }),
      ),
    );
    const acceptSuggestion = vi.fn();

    render(
      <PersonalizedEmptyStateSuggestions
        agentId="agent_support"
        surface="evals"
        acceptSuggestion={acceptSuggestion}
      />,
    );

    expect(
      await screen.findByRole("link", { name: /open simulator/i }),
    ).toHaveAttribute("href", "/agents/agent_support/simulator");
    expect(
      screen.queryByRole("button", { name: /open simulator/i }),
    ).not.toBeInTheDocument();
    expect(acceptSuggestion).not.toHaveBeenCalled();
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
