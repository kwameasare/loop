import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  computeUsageRatio,
  fetchBillingSummary,
  fetchInvoices,
  formatCents,
  projectCycleUsage,
  updatePaymentMethod,
} from "./billing";

describe("computeUsageRatio", () => {
  it("returns ok below 75%", () => {
    const r = computeUsageRatio(500, 1000);
    expect(r.status).toBe("ok");
    expect(r.ratio).toBeCloseTo(0.5);
  });

  it("returns warn at 75%-100%", () => {
    expect(computeUsageRatio(800, 1000).status).toBe("warn");
    expect(computeUsageRatio(999, 1000).status).toBe("warn");
  });

  it("returns over once cap is exceeded", () => {
    const r = computeUsageRatio(1500, 1000);
    expect(r.status).toBe("over");
    expect(r.ratio).toBe(1.5);
  });

  it("treats zero cap as overage when any usage exists", () => {
    expect(computeUsageRatio(0, 0).status).toBe("ok");
    expect(computeUsageRatio(1, 0).status).toBe("over");
  });
});

describe("projectCycleUsage", () => {
  it("scales the run rate to the full cycle", () => {
    const start = Date.UTC(2026, 4, 1);
    const end = Date.UTC(2026, 5, 1);
    const halfway = (start + end) / 2;
    const projected = projectCycleUsage({
      now_ms: halfway,
      cycle_start_ms: start,
      cycle_end_ms: end,
      used: 50_000,
    });
    expect(projected).toBe(100_000);
  });

  it("returns used when before or at cycle start", () => {
    expect(
      projectCycleUsage({
        now_ms: 0,
        cycle_start_ms: 100,
        cycle_end_ms: 200,
        used: 7,
      }),
    ).toBe(7);
  });
});

describe("formatCents", () => {
  it("formats positive and zero values", () => {
    expect(formatCents(0)).toBe("$0.00");
    expect(formatCents(199)).toBe("$1.99");
    expect(formatCents(199_900)).toBe("$1,999.00");
  });

  it("formats negative values with a leading minus", () => {
    expect(formatCents(-50)).toBe("-$0.50");
  });
});

describe("billing cp-api client", () => {
  const ORIG_BASE = process.env.LOOP_CP_API_BASE_URL;
  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });
  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = ORIG_BASE;
    vi.restoreAllMocks();
  });

  it("fetchBillingSummary returns the cp body on 200", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        workspace_id: "ws1",
        plan: { id: "starter" },
        mtd_messages: 100,
      }),
    });
    const res = await fetchBillingSummary("ws1", { fetcher });
    expect(res?.workspace_id).toBe("ws1");
    const [url] = fetcher.mock.calls[0];
    expect(url).toBe("https://cp.test/v1/workspaces/ws1/billing");
  });

  it("fetchBillingSummary returns null on 404 (route not yet shipped)", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });
    const res = await fetchBillingSummary("ws1", { fetcher });
    expect(res).toBeNull();
  });

  it("fetchBillingSummary throws on a non-404 error", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    await expect(fetchBillingSummary("ws1", { fetcher })).rejects.toThrow(
      /500/,
    );
  });

  it("fetchInvoices returns the items array (or empty on 404)", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [{ id: "in_1", number: "INV-1", amount_cents: 1000 }],
      }),
    });
    const list = await fetchInvoices("ws1", { fetcher });
    expect(list).toHaveLength(1);
    const fetcher2 = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });
    expect(await fetchInvoices("ws1", { fetcher: fetcher2 })).toEqual([]);
  });

  it("updatePaymentMethod returns ok+last4 on success", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ last4: "4242" }),
    });
    const res = await updatePaymentMethod(
      "ws1",
      { cardholderName: "Ada Lovelace" },
      { fetcher },
    );
    expect(res).toEqual({ ok: true, last4: "4242" });
    const [, init] = fetcher.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ cardholderName: "Ada Lovelace" });
  });

  it("updatePaymentMethod returns ok=false on 404 (route blocked)", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });
    const res = await updatePaymentMethod(
      "ws1",
      { cardholderName: "Ada" },
      { fetcher },
    );
    expect(res.ok).toBe(false);
  });
});
