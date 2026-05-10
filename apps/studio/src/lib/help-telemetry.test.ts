import { describe, expect, it, vi } from "vitest";

import {
  fetchHelpClips,
  fetchTelemetryConsent,
  saveTelemetryConsent,
} from "@/lib/help-telemetry";

describe("help and telemetry cp clients", () => {
  it("loads and saves granular telemetry consent", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST") {
        expect(url).toBe("https://cp.test/v1/workspaces/ws-1/telemetry-consent");
        expect(JSON.parse(String(init.body))).toMatchObject({
          product_analytics: false,
          diagnostics: true,
        });
        return new Response(
          JSON.stringify({
            workspace_id: "ws-1",
            user_sub: "sam",
            product_analytics: false,
            diagnostics: true,
            ai_improvement: false,
            crash_reports: false,
            annual_review_due: false,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          workspace_id: "ws-1",
          user_sub: "sam",
          product_analytics: null,
          diagnostics: null,
          ai_improvement: null,
          crash_reports: null,
          annual_review_due: true,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });

    const current = await fetchTelemetryConsent("ws-1", {
      baseUrl: "https://cp.test/v1",
      fetcher,
    });
    expect(current.annual_review_due).toBe(true);

    const saved = await saveTelemetryConsent(
      "ws-1",
      {
        product_analytics: false,
        diagnostics: true,
        ai_improvement: false,
        crash_reports: false,
      },
      { baseUrl: "https://cp.test/v1", fetcher },
    );
    expect(saved.annual_review_due).toBe(false);
  });

  it("requires cp-api before saving telemetry consent", async () => {
    await expect(
      saveTelemetryConsent(
        "ws-1",
        {
          product_analytics: false,
          diagnostics: false,
          ai_improvement: false,
          crash_reports: false,
        },
        { baseUrl: "" },
      ),
    ).rejects.toThrow(/LOOP_CP_API_BASE_URL is required/i);
  });

  it("requires cp-api before loading telemetry consent", async () => {
    await expect(
      fetchTelemetryConsent("ws-1", { baseUrl: "" }),
    ).rejects.toThrow(/LOOP_CP_API_BASE_URL is required/i);
  });

  it("loads contextual show-me clips for the current surface", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      expect(String(input)).toBe("https://cp.test/v1/help-clips?surface=pipeline");
      return new Response(
        JSON.stringify({
          items: [
            {
              clip_id: "clip_canary",
              surface: "pipeline",
              title: "Canary promotion",
              url: "/help/clips/canary",
              duration: 30,
              transcript: "Show me canary.",
              frames: ["Open the release candidate."],
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });

    const clips = await fetchHelpClips("pipeline", {
      baseUrl: "https://cp.test/v1",
      fetcher,
    });
    expect(clips[0]?.clip_id).toBe("clip_canary");
    expect(clips[0]?.frames?.[0]).toBe("Open the release candidate.");
  });

  it("requires cp-api before loading contextual show-me clips", async () => {
    await expect(fetchHelpClips("pipeline", { baseUrl: "" })).rejects.toThrow(
      /LOOP_CP_API_BASE_URL is required/i,
    );
  });
});
