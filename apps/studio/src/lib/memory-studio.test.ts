import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
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

  it("fetches and normalizes live memory entries", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            id: "user:alice:preferred_language",
            scope: "user",
            key: "preferred_language",
            before: "unknown",
            after: "English",
            source: "runtime memory store",
            source_trace: "not-attached",
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
    });

    const data = await fetchMemoryStudioData("agent-1", "alice", { fetcher });

    expect(data.entries).toHaveLength(1);
    expect(data.entries[0]).toMatchObject({
      key: "preferred_language",
      after: "English",
      scope: "user",
    });
    const [url] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/agents/agent-1/memory?user_id=alice");
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
        sourceTrace: "not-attached",
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
