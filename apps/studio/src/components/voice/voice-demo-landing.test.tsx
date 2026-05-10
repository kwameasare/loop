import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VoiceDemoLanding } from "@/components/voice/voice-demo-landing";

vi.mock("@/lib/voice-demo", async () => {
  const actual = await vi.importActual<typeof import("@/lib/voice-demo")>(
    "@/lib/voice-demo",
  );
  return {
    ...actual,
    startVoiceDemoSession: vi.fn(async () => ({
      id: "session_1",
      room: "voice-demo-token",
      identity: "stakeholder-abcd",
      livekit_url: "wss://voice.test",
      expires_at: "2026-05-10T12:00:00+00:00",
      trace_capture_policy: "Trace captured.",
    })),
  };
});

const demo = {
  id: "voice_demo_1",
  workspace_id: "ws_1",
  snapshot_id: "snap_1",
  url: "/voice-demo/token_1",
  expires_at: "2026-05-10T12:00:00+00:00",
  rate_limit: "5 minutes / 20 turns",
  duration_cap_minutes: 5,
  mic_test_required: true,
  redaction_policy: "PII and secret-like values redacted.",
  trace_capture_policy: "Every demo turn is captured.",
  whitelabel: true,
  status: "active" as const,
  session_count: 0,
};

describe("VoiceDemoLanding", () => {
  it("requires a mic check before starting the audited voice session", async () => {
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn(async () => ({
          getTracks: () => [{ stop: vi.fn() }],
        })),
      },
    });

    render(<VoiceDemoLanding demo={demo} token="token_1" />);

    expect(screen.getByRole("button", { name: /start voice demo/i })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /run mic test/i }));

    await screen.findByRole("button", { name: /microphone ready/i });
    fireEvent.click(screen.getByRole("button", { name: /start voice demo/i }));

    await waitFor(() =>
      expect(screen.getByTestId("voice-demo-session")).toHaveTextContent(
        "voice-demo-token",
      ),
    );
  });
});
