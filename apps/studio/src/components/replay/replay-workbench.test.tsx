import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

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
    vi.unstubAllGlobals();
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

  it("persists replay forks and eval cases through cp-api", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.example.test/v1";
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/context-ablation")) {
        return new Response(JSON.stringify({ turn_id: "trace_refund_742", items: [] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.endsWith("/replay/forks")) {
        return new Response(
          JSON.stringify({
            ok: true,
            branch: {
              id: "br_replay",
              name: "fork/trace-refund",
              base_version_id: "v23.1.4",
              status: "active",
            },
            change_set: {
              id: "cs_replay",
              name: "Replay fork from frame",
              source_type: "trace_replay_frame",
              source_refs: ["trace_refund_742"],
              status: "draft",
            },
            evidence_refs: ["trace_refund_742"],
            next_url: "/agents/agent/workflow?branch_id=br_replay",
          }),
          { status: 201, headers: { "content-type": "application/json" } },
        );
      }
      if (url.endsWith("/replay/eval-cases")) {
        return new Response(
          JSON.stringify({
            ok: true,
            suite_id: "suite_replay",
            case_id: "case_replay",
            case: {
              id: "case_replay",
              name: "Cancellation replay regression",
              source: "production-replay",
              source_ref: "trace_refund_742",
            },
            evidence_refs: ["trace_refund_742"],
            next_url: "/agents/agent/evals?case_id=case_replay",
          }),
          { status: 201, headers: { "content-type": "application/json" } },
        );
      }
      return new Response("not found", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);
    render(<ReplayWorkbench model={getReplayWorkbenchModel()} />);

    fireEvent.click(screen.getByRole("button", { name: /fork from frame/i }));
    fireEvent.click(screen.getByRole("button", { name: /save as eval/i }));

    expect(await screen.findByText(/Branch br_replay/i)).toBeInTheDocument();
    expect(await screen.findByText(/Eval case case_replay/i)).toBeInTheDocument();
    const bodies = fetcher.mock.calls.map(([, init]) =>
      init?.body ? JSON.parse(String(init.body)) : null,
    );
    expect(bodies).toContainEqual(
      expect.objectContaining({
        trace_id: "trace_refund_742",
        source_version_ref: "v23.1.4",
        evidence_ref: expect.stringContaining("trace_refund_742"),
      }),
    );
    expect(bodies).toContainEqual(
      expect.objectContaining({
        trace_id: "trace_refund_742",
        draft_branch_ref: "draft/refund-clarity",
        risk_tags: expect.arrayContaining(["production-replay", "high", "web_chat"]),
      }),
    );
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
