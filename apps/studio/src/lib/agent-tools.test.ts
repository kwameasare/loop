import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { listAgentTools } from "./agent-tools";

const ORIG_BASE = process.env.LOOP_CP_API_BASE_URL;

describe("listAgentTools", () => {
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("returns the items array on 200", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [{ id: "t1", name: "kb.search", kind: "mcp" }],
      }),
    });
    const res = await listAgentTools("agt1", { fetcher });
    expect(res).toHaveLength(1);
    expect(res[0].kind).toBe("mcp");
    const [url] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/agents/agt1/tools");
  });

  it("returns an empty array on 404 (route blocked)", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });
    const res = await listAgentTools("agt1", { fetcher });
    expect(res).toEqual([]);
  });

  it("propagates non-404 errors", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    await expect(listAgentTools("agt1", { fetcher })).rejects.toThrow(/500/);
  });
});
