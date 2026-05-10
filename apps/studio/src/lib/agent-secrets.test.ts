import { describe, expect, it, vi } from "vitest";

import {
  addAgentSecret,
  listAgentSecrets,
  rotateAgentSecret,
} from "./agent-secrets";

describe("listAgentSecrets", () => {
  it("returns an explicit degraded response instead of fixture secret refs without cp-api", async () => {
    const result = await listAgentSecrets("agt_1");
    expect(result.items).toEqual([]);
    expect(result.degraded_reason).toMatch(/control-plane vault endpoint/i);
  });

  it("returns fixture rows only when explicitly requested", async () => {
    const { items, degraded_reason } = await listAgentSecrets("agt_1", {
      allowFixture: true,
    });
    expect(degraded_reason).toBeUndefined();
    expect(items.length).toBeGreaterThan(0);
    for (const s of items) {
      expect(s.name).toMatch(/^[A-Z][A-Z0-9_]*$/);
      expect(s.ref).toMatch(/^kms:\/\//);
      expect(s).not.toHaveProperty("value");
    }
  });

  it("loads live secret refs from cp-api when configured", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      Response.json({
        items: [
          {
            id: "sec_live",
            agent_id: "agt_1",
            name: "OPENAI_API_KEY",
            ref: "kms://prod/openai-key",
            created_at: "2026-05-01T00:00:00Z",
            rotated_at: null,
          },
        ],
      }),
    );

    const { items } = await listAgentSecrets("agt_1", {
      baseUrl: "https://cp.example.com/v1",
      fetcher: fetcher as unknown as typeof fetch,
      token: "tok-123",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.example.com/v1/agents/agt_1/secrets",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({ authorization: "Bearer tok-123" }),
      }),
    );
    expect(items[0]).toMatchObject({ id: "sec_live", ref: "kms://prod/openai-key" });
    expect(items[0]).not.toHaveProperty("value");
  });

  it("marks a missing vault route as degraded instead of showing an empty secret list", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response("missing", { status: 404 }),
    );

    const { items, degraded_reason } = await listAgentSecrets("agt_1", {
      baseUrl: "https://cp.example.com/v1",
      fetcher: fetcher as unknown as typeof fetch,
    });

    expect(items).toEqual([]);
    expect(degraded_reason).toMatch(/vault route returned 404/i);
  });
});

describe("addAgentSecret", () => {
  it("rejects names that are not SCREAMING_SNAKE_CASE", async () => {
    await expect(
      addAgentSecret({ agentId: "agt_1", name: "lowercase", ref: "kms://x" }),
    ).rejects.toThrow(/SCREAMING_SNAKE_CASE/);
  });

  it("requires cp-api before claiming a secret was added", async () => {
    await expect(
      addAgentSecret({
        agentId: "agt_1",
        name: "STRIPE_KEY",
        ref: "kms://prod/stripe",
      }),
    ).rejects.toThrow(/required to add a secret/);
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
  it("requires cp-api before claiming a secret was rotated", async () => {
    await expect(
      rotateAgentSecret({ secretId: "sec_1" }),
    ).rejects.toThrow(/required to rotate a secret/);
  });

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
