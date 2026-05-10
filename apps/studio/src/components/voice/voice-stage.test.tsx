import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VoiceStage } from "@/components/voice/voice-stage";
import { VOICE_STAGE_FIXTURE, voiceStageFromConfig } from "@/lib/voice-stage";

describe("VoiceStage", () => {
  it("shows waveform, latency, evals, queued speech, and demo links", () => {
    render(<VoiceStage model={VOICE_STAGE_FIXTURE} />);

    expect(screen.getByTestId("voice-stage")).toHaveTextContent("Voice Receptionist");
    expect(screen.getByTestId("voice-latency-budget")).toHaveTextContent(
      "Latency budget",
    );
    expect(screen.getByText("Queued speech preview")).toBeInTheDocument();
    expect(screen.getByTestId("voice-queued-speech-preview")).toHaveTextContent(
      "500 ms before speech",
    );
    expect(screen.getByTestId("voice-evals-and-links")).toHaveTextContent(
      "Audited demo links",
    );
  });

  it("generates audited voice demo links through cp-api", async () => {
    const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;
    const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({
        id: "voice_demo_1",
        token: "token_1",
        workspace_id: "ws_1",
        snapshot_id: "demo_exec",
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
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    render(<VoiceStage model={VOICE_STAGE_FIXTURE} workspaceId="ws_1" />);

    fireEvent.click(screen.getAllByRole("button", { name: /generate link/i })[0]!);

    await waitFor(() =>
      expect(fetcher).toHaveBeenCalledWith(
        "https://cp.test/v1/workspaces/ws_1/voice/demo-links",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(screen.getByText("Audited link ready")).toBeInTheDocument();
    expect(screen.getByText("/voice-demo/token_1")).toBeInTheDocument();
    fetcher.mockRestore();
    if (previousBaseUrl === undefined) delete process.env.LOOP_CP_API_BASE_URL;
    else process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
  });

  it("renders provider labels from live voice config", () => {
    render(
      <VoiceStage
        model={voiceStageFromConfig({
          workspace_id: "ws_live",
          numbers: [
            {
              id: "n1",
              e164: "+15551234567",
              label: "Care",
              region: "na-east",
              provisioned_at_ms: 1,
            },
          ],
          asr_provider: "google",
          tts_provider: "polly",
        })}
      />,
    );

    expect(screen.getByTestId("voice-config-summary")).toHaveTextContent(
      "Google Speech-to-Text v2",
    );
    expect(screen.getByTestId("voice-config-summary")).toHaveTextContent(
      "+15551234567",
    );
  });
});
