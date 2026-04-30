import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { listAgents } from "./cp-api";

const ORIGINAL = process.env.LOOP_CP_API_BASE_URL;

describe("listAgents", () => {
  beforeEach(() => {
    delete process.env.LOOP_CP_API_BASE_URL;
  });

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIGINAL;
    vi.restoreAllMocks();
  });

  it("returns the in-memory fixture when LOOP_CP_API_BASE_URL is unset", async () => {
    const { agents } = await listAgents();
    expect(agents.length).toBeGreaterThan(0);
    expect(agents[0]).toMatchObject({ id: expect.any(String), name: expect.any(String) });
  });

  it("calls cp-api when LOOP_CP_API_BASE_URL is set", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ agents: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await listAgents();
    expect(result).toEqual({ agents: [] });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://cp.test/v1/agents",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("throws when cp-api returns a non-2xx", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }),
    );
    await expect(listAgents()).rejects.toThrow(/503/);
  });
});
