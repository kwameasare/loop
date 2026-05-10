import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ReplayWorkbench } from "@/components/replay/replay-workbench";
import {
  getReplayWorkbenchModel,
  type ReplayWorkbenchModel,
} from "@/lib/replay-workbench";

describe("ReplayWorkbench", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    if (previousBaseUrl === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    }
  });

  async function waitForContextSliderToSettle() {
    await screen.findByText(/LOOP_CP_API_BASE_URL is required/i);
  }

  it("renders replay, persona, property, and scene surfaces", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    render(<ReplayWorkbench model={getReplayWorkbenchModel()} />);

    expect(screen.getByTestId("replay-workbench")).toBeInTheDocument();
    expect(screen.getByTestId("production-replay")).toHaveTextContent(
      "Production Replay Against The Future",
    );
    expect(screen.getByTestId("persona-simulator")).toHaveTextContent(
      "First User Persona Simulator",
    );
    expect(screen.getByTestId("conversation-property-tester")).toHaveTextContent(
      "Simulate 100 like this",
    );
    expect(screen.getByTestId("scene-library")).toHaveTextContent(
      "Canonical production conversations",
    );
    expect(screen.getByTestId("cost-of-context-slider")).toBeInTheDocument();
    await waitForContextSliderToSettle();
  });

  it("lets a builder promote replay evidence into evals", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    render(<ReplayWorkbench model={getReplayWorkbenchModel()} />);

    fireEvent.click(screen.getByRole("button", { name: /save as eval/i }));

    expect(screen.getByText(/queued as a regression eval/i)).toBeInTheDocument();
    await waitForContextSliderToSettle();
  });

  it("shows backend-required errors instead of local replay-against-draft diffs", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    render(<ReplayWorkbench model={getReplayWorkbenchModel()} />);

    fireEvent.click(
      screen.getByRole("button", { name: /replay against my draft/i }),
    );

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Local replay compares/i),
    ).not.toBeInTheDocument();
  });

  it("renders degraded replay evidence when production conversations cannot load", () => {
    const model: ReplayWorkbenchModel = {
      conversations: [],
      selectedReplay: {
        conversationId: "no_trace_loaded",
        behavioralDistance: 0,
        changedFrames: 0,
        latencyDeltaMs: 0,
        costDeltaPct: 0,
        mostLikelyBreak: "No production traces loaded.",
        diffRows: [],
      },
      personas: [],
      properties: [],
      clusters: [],
      scenes: [],
      degradedReason:
        "LOOP_CP_API_BASE_URL is required to search production traces.",
    };

    render(<ReplayWorkbench model={model} />);

    expect(screen.getByText("Replay evidence is unavailable")).toBeInTheDocument();
    expect(screen.getByText(/LOOP_CP_API_BASE_URL/i)).toBeInTheDocument();
  });
});
