import { describe, expect, it, vi } from "vitest";

import {
  addAgentSecret,
  listAgentSecrets,
  rotateAgentSecret,
} from "./agent-secrets";

describe("listAgentSecrets", () => {
  it("returns the fixture rows with name + ref + rotated_at", async () => {
    const { items } = await listAgentSecrets("agt_1");
    expect(items.length).toBeGreaterThan(0);
    for (const s of items) {
      expect(s.name).toMatch(/^[A-Z][A-Z0-9_]*$/);
      expect(s.ref).toMatch(/^kms:\/\//);
      expect(s).not.toHaveProperty("value");
    }
  });
});

describe("addAgentSecret", () => {
  it("rejects names that are not SCREAMING_SNAKE_CASE", async () => {
    await expect(
      addAgentSecret({ agentId: "agt_1", name: "lowercase", ref: "kms://x" }),
    ).rejects.toThrow(/SCREAMING_SNAKE_CASE/);
  });

  it("POSTs to /v1/agents/{id}/secrets with name + ref", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "sec_new",
          agent_id: "agt_1",
          name: "STRIPE_KEY",
          ref: "kms://prod/stripe",
          created_at: "2026-05-01T00:00:00Z",
          rotated_at: null,
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      ),
    );
    const result = await addAgentSecret(
      { agentId: "agt_1", name: "STRIPE_KEY", ref: "kms://prod/stripe" },
      {
        fetcher: fetcher as unknown as typeof fetch,
        baseUrl: "https://cp.example.com",
      },
    );
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.example.com/v1/agents/agt_1/secrets");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      name: "STRIPE_KEY",
      ref: "kms://prod/stripe",
    });
    expect(result.name).toBe("STRIPE_KEY");
  });
});

describe("rotateAgentSecret", () => {
  it("POSTs to /v1/secrets/{id}/rotate and returns the new rotated_at", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          secretId: "sec_1",
          rotated_at: "2026-05-01T00:00:00Z",
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    const result = await rotateAgentSecret(
      { secretId: "sec_1" },
      {
        fetcher: fetcher as unknown as typeof fetch,
        baseUrl: "https://cp.example.com",
      },
    );
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.example.com/v1/secrets/sec_1/rotate");
    expect(init.method).toBe("POST");
    expect(result.rotated_at).toBe("2026-05-01T00:00:00Z");
  });

  it("throws on non-2xx so callers can render an error toast", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response("nope", { status: 500 }));
    await expect(
      rotateAgentSecret(
        { secretId: "sec_x" },
        {
          fetcher: fetcher as unknown as typeof fetch,
          baseUrl: "https://cp.example.com",
        },
      ),
    ).rejects.toThrow(/500/);
  });
});
