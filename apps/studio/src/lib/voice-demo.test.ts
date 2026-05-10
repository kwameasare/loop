import { describe, expect, it, vi } from "vitest";

import {
  createVoiceDemoLink,
  fetchVoiceDemoLink,
  startVoiceDemoSession,
} from "@/lib/voice-demo";

describe("voice demo client", () => {
  it("creates, reads, and starts audited voice demo links through cp-api", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/workspaces/ws_1/voice/demo-links")) {
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toEqual({
          snapshot_id: "snap_1",
          expires_in_minutes: 5,
        });
        return new Response(
          JSON.stringify({
            id: "voice_demo_1",
            token: "token_1",
            workspace_id: "ws_1",
            snapshot_id: "snap_1",
            url: "/voice-demo/token_1",
            expires_at: "2026-05-10T12:00:00+00:00",
            rate_limit: "5 minutes / 20 turns",
            duration_cap_minutes: 5,
            mic_test_required: true,
            redaction_policy: "PII redacted.",
            trace_capture_policy: "Trace captured.",
            whitelabel: true,
            status: "active",
            session_count: 0,
          }),
        );
      }
      if (url.endsWith("/voice-demo/token_1/sessions")) {
        expect(init?.method).toBe("POST");
        return new Response(
          JSON.stringify({
            id: "session_1",
            room: "voice-demo-token",
            identity: "stakeholder-abcd",
            livekit_url: "wss://voice.test",
            expires_at: "2026-05-10T12:00:00+00:00",
            trace_capture_policy: "Trace captured.",
          }),
        );
      }
      expect(url).toBe("https://cp.test/v1/voice-demo/token_1");
      return new Response(
        JSON.stringify({
          id: "voice_demo_1",
          workspace_id: "ws_1",
          snapshot_id: "snap_1",
          url: "/voice-demo/token_1",
          expires_at: "2026-05-10T12:00:00+00:00",
          rate_limit: "5 minutes / 20 turns",
          duration_cap_minutes: 5,
          mic_test_required: true,
          redaction_policy: "PII redacted.",
          trace_capture_policy: "Trace captured.",
          whitelabel: true,
          status: "active",
          session_count: 0,
        }),
      );
    });

    await expect(
      createVoiceDemoLink("ws_1", "snap_1", {
        baseUrl: "https://cp.test",
        fetcher,
      }),
    ).resolves.toMatchObject({ url: "/voice-demo/token_1" });
    await expect(
      fetchVoiceDemoLink("token_1", { baseUrl: "https://cp.test", fetcher }),
    ).resolves.toMatchObject({ snapshot_id: "snap_1" });
    await expect(
      startVoiceDemoSession("token_1", { baseUrl: "https://cp.test", fetcher }),
    ).resolves.toMatchObject({ room: "voice-demo-token" });
  });
});
