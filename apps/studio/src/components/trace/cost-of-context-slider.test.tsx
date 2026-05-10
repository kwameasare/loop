import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CostOfContextSlider } from "@/components/trace/cost-of-context-slider";

describe("CostOfContextSlider", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    if (previousBaseUrl === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    }
    vi.unstubAllGlobals();
  });

  it("does not advertise local ablations when cp-api is unavailable", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    render(<CostOfContextSlider agentId="agent_support" turnId="turn_1" />);

    expect(await screen.findByText(/LOOP_CP_API_BASE_URL is required/i)).toBeInTheDocument();
    expect(screen.getByTestId("cost-of-context-slider")).toHaveTextContent(
      "0 ablations",
    );
    expect(screen.queryByText("Long-tail prompt sections")).not.toBeInTheDocument();
  });

  it("marks context deltas unavailable when the backend only has trace summary evidence", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        Response.json({
          turn_id: "trace_1",
          unavailable_reason:
            "Context-section attribution is not mounted for this trace yet.",
          items: [
            {
              id: "prompt_sections",
              label: "Prompt sections",
              enabled: true,
              cost_delta_pct: 0,
              latency_delta_ms: 0,
              quality_delta: 0,
              evidence_ref: "trace/trace_1/context/prompt-unavailable",
            },
          ],
        }),
      ),
    );

    render(<CostOfContextSlider agentId="agent_support" turnId="trace_1" />);

    expect(
      await screen.findByTestId("context-ablation-unavailable"),
    ).toHaveTextContent("Context-section attribution");
    expect(screen.getByTestId("cost-of-context-slider")).toHaveTextContent(
      "1 ablations",
    );
    expect(screen.getByText("Prompt sections")).toBeInTheDocument();
    expect(screen.getByText(/Cost 0% · latency 0 ms · quality 0/i)).toBeInTheDocument();
  });
});
