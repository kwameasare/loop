import { describe, expect, it, vi } from "vitest";

import {
  assertSnapshotSignature,
  bisectStepsBetween,
  branchSnapshot,
  fetchDeploySafetyModel,
  FIXTURE_BEHAVIOR_CHANGES,
  FIXTURE_BISECT,
  FIXTURE_SNAPSHOTS,
  SnapshotSignatureError,
  topLikelyChanges,
  verifySnapshotSignature,
} from "./snapshots";

describe("topLikelyChanges", () => {
  it("returns top-k ordered by tier then confidence", () => {
    const top = topLikelyChanges(FIXTURE_BEHAVIOR_CHANGES, 3);
    expect(top.map((c) => c.id)).toEqual(["bc_1", "bc_2", "bc_3"]);
  });

  it("does not mutate the input", () => {
    const before = FIXTURE_BEHAVIOR_CHANGES.map((c) => c.id);
    topLikelyChanges(FIXTURE_BEHAVIOR_CHANGES, 2);
    expect(FIXTURE_BEHAVIOR_CHANGES.map((c) => c.id)).toEqual(before);
  });
});

describe("fetchDeploySafetyModel", () => {
  it("builds what-could-break rows from live traces", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.includes("/workspaces/ws-1/traces")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                workspace_id: "ws-1",
                trace_id: "c".repeat(32),
                turn_id: "11111111-1111-4111-8111-111111111111",
                conversation_id: "22222222-2222-4222-8222-222222222222",
                agent_id: "33333333-3333-4333-8333-333333333333",
                started_at: "2026-05-07T12:00:00Z",
                duration_ms: 500,
                span_count: 4,
                error: true,
              },
            ],
            next_cursor: null,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          items: [
            {
              id: "ev-1",
              occurred_at: "2026-05-07T12:00:00Z",
              workspace_id: "ws-1",
              actor_sub: "sam@example.com",
              action: "agent.version.promoted",
              resource_type: "agent_version",
              resource_id: "v1",
              outcome: "success",
            },
          ],
          total: 1,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });

    const model = await fetchDeploySafetyModel("ws-1", {
      baseUrl: "https://cp.example.test/v1",
      fetcher,
    });

    expect(model.changes[0]).toMatchObject({
      exemplarTranscriptId: "c".repeat(32),
      likelihood: "high",
    });
    expect(model.snapshots[0].signature).toBe(
      `sig:${model.snapshots[0].sha256}`,
    );
    expect(model.bisect.culpritCommit).toBe("agentve");
  });
});

describe("bisectStepsBetween", () => {
  it("includes both endpoints regardless of order", () => {
    const steps = bisectStepsBetween(FIXTURE_BISECT.steps, "5e6f7a8", "c4d5e6f");
    expect(steps.map((s) => s.commit)).toEqual(["5e6f7a8", "9a3f1b2", "c4d5e6f"]);
    const reverse = bisectStepsBetween(FIXTURE_BISECT.steps, "c4d5e6f", "5e6f7a8");
    expect(reverse.map((s) => s.commit)).toEqual([
      "5e6f7a8",
      "9a3f1b2",
      "c4d5e6f",
    ]);
  });

  it("returns empty when an endpoint is unknown", () => {
    expect(bisectStepsBetween(FIXTURE_BISECT.steps, "unknown", "5e6f7a8")).toEqual(
      [],
    );
  });
});

describe("snapshot signature verification", () => {
  it("verifies fixture snapshots", () => {
    for (const snap of FIXTURE_SNAPSHOTS) {
      expect(verifySnapshotSignature(snap)).toBe(true);
    }
  });

  it("rejects a tampered signature", () => {
    const [snap] = FIXTURE_SNAPSHOTS;
    expect(
      verifySnapshotSignature({ ...snap, signature: "sig:tampered" }),
    ).toBe(false);
    expect(() =>
      assertSnapshotSignature({ ...snap, signature: "sig:tampered" }),
    ).toThrow(SnapshotSignatureError);
  });

  it("rejects an empty signing key alias", () => {
    const [snap] = FIXTURE_SNAPSHOTS;
    expect(verifySnapshotSignature({ ...snap, signingKey: "" })).toBe(false);
  });
});

describe("branchSnapshot", () => {
  it("creates a branch from a verified parent", () => {
    const parent = FIXTURE_SNAPSHOTS[0];
    const branch = branchSnapshot(parent, {
      id: "snap_demo_2025_02_22",
      createdAt: "2025-02-22T12:00:00Z",
      purpose: "demo",
      evidenceRef: "audit/snapshot/snap_demo_2025_02_22",
    });
    expect(branch.parent).toBe(parent.id);
    expect(branch.purpose).toBe("demo");
  });

  it("refuses to branch from an unsigned snapshot", () => {
    const parent = FIXTURE_SNAPSHOTS[0];
    expect(() =>
      branchSnapshot(
        { ...parent, signature: "sig:tampered" },
        {
          id: "snap_bad",
          createdAt: "2025-02-22T12:00:00Z",
          purpose: "demo",
          evidenceRef: "audit/snapshot/snap_bad",
        },
      ),
    ).toThrow(SnapshotSignatureError);
  });
});

describe("fixture audit shape", () => {
  it("every behavior change is evidenced", () => {
    for (const c of FIXTURE_BEHAVIOR_CHANGES) {
      expect(c.evidenceRef).toMatch(/^audit\/wcb\//);
      expect(c.confidence).toBeGreaterThanOrEqual(0);
      expect(c.confidence).toBeLessThanOrEqual(100);
    }
  });

  it("bisect identifies a single culprit and confidence is bounded", () => {
    expect(FIXTURE_BISECT.steps.some((s) => s.commit === FIXTURE_BISECT.culpritCommit)).toBe(
      true,
    );
    expect(FIXTURE_BISECT.confidence).toBeGreaterThan(0);
    expect(FIXTURE_BISECT.confidence).toBeLessThanOrEqual(100);
  });
});
