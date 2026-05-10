import { describe, expect, it, vi } from "vitest";

import {
  fetchReplayWorkbenchModel,
  forkReplayFrame,
  replayAgainstDraft,
  saveReplayAsEvalCase,
} from "./replay-workbench";

describe("fetchReplayWorkbenchModel", () => {
  it("does not serve fixture production conversations when cp-api is unconfigured", async () => {
    const model = await fetchReplayWorkbenchModel("ws-1");

    expect(model.conversations).toEqual([]);
    expect(model.personas).toEqual([]);
    expect(model.properties).toEqual([]);
    expect(model.clusters).toEqual([]);
    expect(model.scenes).toEqual([]);
    expect(model.selectedReplay.mostLikelyBreak).toBe(
      "No production traces loaded.",
    );
    expect(model.degradedReason).toMatch(/LOOP_CP_API_BASE_URL is required/i);
  });

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
    expect(model.scenes).toEqual([]);
    expect(model.personas).toEqual([]);
  });

  it("runs replay-against-draft through the live cp-api contract", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      new Response(
        JSON.stringify({
          items: [
            {
              trace_id: "trace-prod-1",
              status: "changed",
              behavioral_distance: 34,
              latency_delta_ms: 80,
              cost_delta_pct: 4,
              token_aligned_rows: [
                {
                  frame: "answer",
                  baseline: "old",
                  draft: "new",
                  status: "changed",
                },
              ],
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const replay = await replayAgainstDraft(
      "agent-1",
      {
        traceIds: ["trace-prod-1"],
        draftBranchRef: "draft/refund",
        compareVersionRef: "v22",
      },
      {
        baseUrl: "https://cp.example.test/v1",
        fetcher,
      },
    );

    expect(replay.items[0]?.conversationId).toBe("trace-prod-1");
    expect(replay.items[0]?.diffRows[0]?.baseline).toBe("old");
    const [url, init] = fetcher.mock.calls[0]!;
    expect(url).toBe("https://cp.example.test/v1/agents/agent-1/replay/against-draft");
    expect(JSON.parse(String(init?.body))).toMatchObject({
      trace_ids: ["trace-prod-1"],
      draft_branch_ref: "draft/refund",
      compare_version_ref: "v22",
    });
  });

  it("forks a replay frame through the live cp-api contract", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      new Response(
        JSON.stringify({
          ok: true,
          branch: {
            id: "br_replay",
            name: "fork/trace-prod-1-answer",
            base_version_id: "v23",
            status: "active",
          },
          change_set: {
            id: "cs_replay",
            name: "Replay fork from answer",
            source_type: "trace_replay_frame",
            source_refs: ["trace-prod-1", "answer"],
            status: "draft",
          },
          evidence_refs: ["trace-prod-1", "answer", "trace-prod-1/answer"],
          next_url: "/agents/agent-1/workflow?branch_id=br_replay",
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      ),
    );

    const result = await forkReplayFrame(
      "agent-1",
      {
        traceId: "trace-prod-1",
        frameId: "answer",
        sourceVersionRef: "v23",
        snapshotId: "snap-prod",
        evidenceRef: "trace-prod-1/answer",
        purpose: "Investigate legal escalation wording.",
      },
      {
        baseUrl: "https://cp.example.test/v1",
        fetcher,
      },
    );

    expect(result.branch.id).toBe("br_replay");
    const [url, init] = fetcher.mock.calls[0]!;
    expect(url).toBe("https://cp.example.test/v1/agents/agent-1/replay/forks");
    expect(JSON.parse(String(init?.body))).toMatchObject({
      trace_id: "trace-prod-1",
      frame_id: "answer",
      source_version_ref: "v23",
      snapshot_id: "snap-prod",
      evidence_ref: "trace-prod-1/answer",
    });
  });

  it("saves replay evidence as a provenance-rich eval case", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      new Response(
        JSON.stringify({
          ok: true,
          suite_id: "suite_replay",
          case_id: "case_replay",
          case: {
            id: "case_replay",
            name: "Cancellation replay regression",
            source: "production-replay",
            source_ref: "trace-prod-1",
          },
          evidence_refs: ["trace-prod-1", "answer", "replay/trace-prod-1/answer"],
          next_url: "/agents/agent-1/evals?case_id=case_replay",
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      ),
    );

    const result = await saveReplayAsEvalCase(
      "agent-1",
      {
        title: "Cancellation replay regression",
        traceId: "trace-prod-1",
        frameId: "answer",
        sourceVersionRef: "v23",
        draftBranchRef: "draft/refund",
        channel: "whatsapp",
        snapshotId: "snap-prod",
        expectedBehavior: "Escalate legal threats before quoting refund policy.",
        failureReason: "Draft missed attorney synonym.",
        replayRef: "replay/trace-prod-1/answer",
        riskTags: ["production-replay", "high", "whatsapp"],
      },
      {
        baseUrl: "https://cp.example.test/v1",
        fetcher,
      },
    );

    expect(result.case_id).toBe("case_replay");
    const [url, init] = fetcher.mock.calls[0]!;
    expect(url).toBe("https://cp.example.test/v1/agents/agent-1/replay/eval-cases");
    expect(JSON.parse(String(init?.body))).toMatchObject({
      trace_id: "trace-prod-1",
      source_version_ref: "v23",
      draft_branch_ref: "draft/refund",
      channel: "whatsapp",
      expected_behavior: "Escalate legal threats before quoting refund policy.",
      risk_tags: ["production-replay", "high", "whatsapp"],
    });
  });

  it("requires cp-api for replay-against-draft", async () => {
    await expect(
      replayAgainstDraft(
        "agent-1",
        {
          traceIds: ["trace-prod-1"],
          draftBranchRef: "draft/refund",
        },
        { baseUrl: "" },
      ),
    ).rejects.toThrow(/LOOP_CP_API_BASE_URL is required/i);
  });
});
