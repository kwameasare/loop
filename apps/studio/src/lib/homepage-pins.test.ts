import { describe, expect, it, vi } from "vitest";

import {
  createHomepagePin,
  fetchHomepagePins,
} from "@/lib/homepage-pins";

describe("homepage pins client", () => {
  it("fetches user-scoped homepage pins from cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      expect(String(input)).toBe(
        "https://cp.test/v1/workspaces/ws_1/homepage/pins",
      );
      expect(init?.method).toBe("GET");
      return Response.json({
        items: [
          {
            id: "pin_trace",
            source_type: "trace",
            source_id: "trace_1",
            title: "Worst trace",
            href: "/traces/trace_1",
            created_at: "2026-05-10T12:00:00.000Z",
          },
        ],
      });
    });

    const result = await fetchHomepagePins("ws_1", {
      baseUrl: "https://cp.test",
      fetcher,
    });

    expect(result.degradedReason).toBeUndefined();
    expect(result.items).toHaveLength(1);
    expect(result.items[0]?.title).toBe("Worst trace");
  });

  it("returns an empty degraded result instead of fake pins without cp-api", async () => {
    const result = await fetchHomepagePins("ws_1", { baseUrl: "" });

    expect(result.items).toEqual([]);
    expect(result.degradedReason).toMatch(/Homepage pins unavailable/i);
  });

  it("creates pins through the workspace endpoint", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      expect(String(input)).toBe(
        "https://cp.test/v1/workspaces/ws_1/homepage/pins",
      );
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        source_type: "observatory_metric",
        source_id: "quality",
        title: "Quality",
        href: "/observe?metric=quality",
      });
      return Response.json(
        {
          id: "pin_quality",
          source_type: "observatory_metric",
          source_id: "quality",
          title: "Quality",
          href: "/observe?metric=quality",
          created_at: "2026-05-10T12:00:00.000Z",
        },
        { status: 201 },
      );
    });

    const pin = await createHomepagePin(
      "ws_1",
      {
        source_type: "observatory_metric",
        source_id: "quality",
        title: "Quality",
        href: "/observe?metric=quality",
      },
      { baseUrl: "https://cp.test", fetcher },
    );

    expect(pin.id).toBe("pin_quality");
  });
});
