import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

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

  it("generates audited voice demo links", () => {
    render(<VoiceStage model={VOICE_STAGE_FIXTURE} />);

    fireEvent.click(screen.getAllByRole("button", { name: /generate link/i })[0]!);

    expect(screen.getByText("Link copied to audit log")).toBeInTheDocument();
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
