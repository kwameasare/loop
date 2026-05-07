import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VoiceStage } from "@/components/voice/voice-stage";
import { VOICE_STAGE_FIXTURE } from "@/lib/voice-stage";

describe("VoiceStage", () => {
  it("shows waveform, latency, evals, queued speech, and demo links", () => {
    render(<VoiceStage model={VOICE_STAGE_FIXTURE} />);

    expect(screen.getByTestId("voice-stage")).toHaveTextContent("Voice Receptionist");
    expect(screen.getByTestId("voice-latency-budget")).toHaveTextContent(
      "Latency budget",
    );
    expect(screen.getByText("Queued speech preview")).toBeInTheDocument();
    expect(screen.getByTestId("voice-evals-and-links")).toHaveTextContent(
      "Audited demo links",
    );
  });

  it("generates audited voice demo links", () => {
    render(<VoiceStage model={VOICE_STAGE_FIXTURE} />);

    fireEvent.click(screen.getAllByRole("button", { name: /generate link/i })[0]!);

    expect(screen.getByText("Link copied to audit log")).toBeInTheDocument();
  });
});
