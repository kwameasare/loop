import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createToolsRoomData,
  draftToolFromRequest,
  listAgentTools,
} from "./agent-tools";

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

describe("Tools Room data", () => {
  it("builds safety-rich tool data from target fixtures", () => {
    const data = createToolsRoomData("agent_support");
    expect(data.tools).toHaveLength(2);
    expect(data.tools[0].schema[0].name).toBe("order_id");
    expect(data.tools[1].productionGrant).toBe("blocked");
    expect(data.tools[1].secretRef).toContain(
      "vault/data/workspace/ws_acme/agent/agent_support",
    );
  });

  it("drafts a tool from curl without retaining auth values", () => {
    const draft = draftToolFromRequest(
      [
        "curl -X POST https://api.example.test/refunds",
        "-H 'Authorization: Bearer hidden'",
        '-d \'{"order_id":"ord_123","amount_cents":5000}\'',
      ].join(" "),
    );
    expect(draft.method).toBe("POST");
    expect(draft.sideEffect).toBe("money-movement");
    expect(draft.authNeeds.join(" ")).toContain("redacted");
    expect(draft.authNeeds.join(" ")).not.toContain("hidden");
    expect(draft.schema.map((field) => field.name)).toContain("order_id");
  });
});
