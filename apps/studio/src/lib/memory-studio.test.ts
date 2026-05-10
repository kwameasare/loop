import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createDegradedMemoryStudioData,
  deleteMemoryStudioEntry,
  fetchMemoryStudioData,
} from "./memory-studio";

describe("memory studio cp-api client", () => {
  const ORIG_BASE = process.env.LOOP_CP_API_BASE_URL;
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("requires cp-api configuration instead of returning fixture memory", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;

    await expect(fetchMemoryStudioData("agent-1", "alice")).rejects.toThrow(
      "LOOP_CP_API_BASE_URL is required for memory calls",
    );
  });

  it("builds an explicit degraded Memory Studio model from load failures", () => {
    const data = createDegradedMemoryStudioData(
      "agent-1",
      "LOOP_CP_API_BASE_URL is required for memory calls",
    );

    expect(data.entries).toEqual([]);
    expect(data.agentName).toBe("Agent agent-1");
    expect(data.degradedReason).toContain("LOOP_CP_API_BASE_URL");
    expect(data.retentionEvidence).toContain("LOOP_CP_API_BASE_URL");
  });

  it("fetches and normalizes live memory entries", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/memory-policies")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: "mp_user",
                workspace_id: "workspace-1",
                agent_id: "agent-1",
                scope: "user",
                allowed_memory_types: ["preference"],
                retention: "365 days",
                consent_requirement: "Explicit consent required.",
                pii_policy: "No payment data.",
                delete_behavior: "Delete on request.",
                privacy_implications: ["Affects future turns."],
                source_trace_required: true,
                approval_status: "review_required",
                content_hash: "hash_user",
                approval_invalidated_at: null,
                created_at: "2026-05-01T10:00:00Z",
                updated_at: "2026-05-01T10:00:00Z",
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          items: [
            {
              id: "user:alice:preferred_language",
              scope: "user",
              key: "preferred_language",
              before: "unknown",
              after: "English",
              source: "runtime memory store",
              source_trace: "trace_live_42",
              source_turn_id: "turn_7",
              source_span_id: "span_memory_write_preferred_language",
              policy_ref: "mp_user",
              retention_policy: "durable user memory",
              updated_at: "2026-05-01T10:00:00Z",
              writer_version: "live",
              confidence: "medium",
              safety_flags: ["none"],
              deletion_state: "available",
              deletion_reason: "delete with audit",
              replay_impact: "removes preference",
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });

    const data = await fetchMemoryStudioData("agent-1", "alice", { fetcher });

    expect(data.entries).toHaveLength(1);
    expect(data.policies).toHaveLength(1);
    expect(data.entries[0]).toMatchObject({
      key: "preferred_language",
      after: "English",
      scope: "user",
      sourceTrace: "trace_live_42",
      sourceTurnId: "turn_7",
      sourceSpanId: "span_memory_write_preferred_language",
      policyRef: "mp_user",
    });
    const [url] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/agents/agent-1/memory?user_id=alice");
  });

  it("keeps cp-api policies when the memory store has no entries", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/memory-policies")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: "mp_user",
                workspace_id: "workspace-1",
                agent_id: "agent-1",
                scope: "user",
                allowed_memory_types: ["preference"],
                retention: "365 days",
                consent_requirement: "Explicit consent required.",
                pii_policy: "No payment data.",
                delete_behavior: "Delete on request.",
                privacy_implications: ["Affects future turns."],
                source_trace_required: true,
                approval_status: "review_required",
                content_hash: "hash_user",
                approval_invalidated_at: null,
                created_at: "2026-05-01T10:00:00Z",
                updated_at: "2026-05-01T10:00:00Z",
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response("", { status: 404 });
    });

    const data = await fetchMemoryStudioData("agent-1", "alice", { fetcher });

    expect(data.entries).toEqual([]);
    expect(data.policies).toHaveLength(1);
    expect(data.retentionEvidence).toMatch(/Loaded memory policy records/i);
    expect(data.degradedReason).toMatch(/No memory writes/i);
  });

  it("deletes durable user memory by key", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => ({}),
    });

    await deleteMemoryStudioEntry(
      "agent-1",
      {
        id: "user:alice:preferred_language",
        scope: "user",
        key: "preferred_language",
        before: "unknown",
        after: "English",
        source: "runtime memory store",
        sourceTrace: "trace_live_42",
        sourceTurnId: "turn_7",
        sourceSpanId: "span_memory_write_preferred_language",
        policyRef: "mp_user",
        retentionPolicy: "durable user memory",
        lastWrite: "2026-05-01T10:00:00Z",
        writerVersion: "live",
        confidence: "medium",
        safetyFlags: ["none"],
        deletionState: "available",
        deletionReason: "delete with audit",
        replayImpact: "removes preference",
      },
      "alice",
      { fetcher },
    );

    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe(
      "https://cp.test/v1/agents/agent-1/memory/user/preferred_language?user_id=alice",
    );
    expect(init.method).toBe("DELETE");
  });
});
