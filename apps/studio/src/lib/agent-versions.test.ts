import { describe, expect, it, vi } from "vitest";

import {
  listAgentVersions,
  priorVersion,
  promoteAgentVersion,
} from "./agent-versions";

describe("listAgentVersions", () => {
  it("paginates the fixture with the requested page size", async () => {
    const first = await listAgentVersions("agt_1", { pageSize: 5 });
    expect(first.items).toHaveLength(5);
    expect(first.next_cursor).toBe("5");

    const second = await listAgentVersions("agt_1", {
      pageSize: 5,
      cursor: first.next_cursor!,
    });
    expect(second.items).toHaveLength(5);
    expect(second.next_cursor).toBe("10");

    const tail = await listAgentVersions("agt_1", {
      pageSize: 5,
      cursor: second.next_cursor!,
    });
    expect(tail.items).toHaveLength(2);
    expect(tail.next_cursor).toBeNull();
  });

  it("orders versions newest-first", async () => {
    const { items } = await listAgentVersions("agt_1", { pageSize: 100 });
    const numbers = items.map((v) => v.version);
    expect(numbers).toEqual([...numbers].sort((a, b) => b - a));
  });

  it("loads live versions from cp-api when configured", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "ver-live-1",
              agent_id: "agt_1",
              version: 1,
              spec: {
                system_prompt: "You are live.",
                deploy_state: "active",
                eval_status: "passed",
              },
              created_at: "2026-05-07T12:00:00Z",
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const { items } = await listAgentVersions("agt_1", {
      baseUrl: "https://cp.example.com/v1",
      fetcher: fetcher as unknown as typeof fetch,
      pageSize: 10,
    });

    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.example.com/v1/agents/agt_1/versions",
      expect.objectContaining({ method: "GET" }),
    );
    expect(items[0]).toMatchObject({
      id: "ver-live-1",
      deploy_state: "active",
      eval_status: "passed",
    });
    expect(items[0]?.config_json).toContain("You are live.");
  });
});

describe("priorVersion", () => {
  it("returns the version with version-1 against the target", async () => {
    const { items } = await listAgentVersions("agt_1", { pageSize: 100 });
    const v5 = items.find((v) => v.version === 5)!;
    const prior = priorVersion(items, v5);
    expect(prior?.version).toBe(4);
  });

  it("returns null for the first-ever version", async () => {
    const { items } = await listAgentVersions("agt_1", { pageSize: 100 });
    const v1 = items.find((v) => v.version === 1)!;
    expect(priorVersion(items, v1)).toBeNull();
  });
});

describe("promoteAgentVersion", () => {
  it("POSTs to /v1/agents/{agent_id}/versions/{id}/promote with the stage", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          versionId: "ver_42",
          promoted_to: "production",
          promoted_at: "2026-05-01T00:00:00Z",
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    const result = await promoteAgentVersion(
      { agentId: "agt_1", versionId: "ver_42" },
      {
        fetcher: fetcher as unknown as typeof fetch,
        baseUrl: "https://cp.example.com",
        token: "tok-123",
      },
    );
    expect(fetcher).toHaveBeenCalledTimes(1);
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe(
      "https://cp.example.com/v1/agents/agt_1/versions/ver_42/promote",
    );
    expect(init.method).toBe("POST");
    expect(init.headers.authorization).toBe("Bearer tok-123");
    expect(JSON.parse(init.body)).toEqual({ stage: "production" });
    expect(result.promoted_to).toBe("production");
  });

  it("throws on non-2xx so the caller can render an error toast", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response("nope", { status: 404 }));
    await expect(
      promoteAgentVersion(
        { agentId: "agt_1", versionId: "ver_x" },
        {
          fetcher: fetcher as unknown as typeof fetch,
          baseUrl: "https://cp.example.com",
        },
      ),
    ).rejects.toThrow(/404/);
  });
});
