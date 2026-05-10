import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import VoiceDemoPage from "./page";

vi.mock("@/lib/voice-demo", () => ({
  fetchVoiceDemoLink: vi.fn(async () => ({
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
  })),
  startVoiceDemoSession: vi.fn(),
}));

describe("VoiceDemoPage", () => {
  it("renders public voice demo access instead of leaving generated links dead", async () => {
    render(await VoiceDemoPage({ params: { token: "token_1" } }));

    expect(screen.getByText("Short-lived stakeholder voice access")).toBeInTheDocument();
    expect(screen.getByText("snap_1")).toBeInTheDocument();
    expect(screen.getByText("PII redacted.")).toBeInTheDocument();
  });
});
