import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FIXTURE_VOICE_CONFIG, type VoiceConfig } from "@/lib/voice-config";

import { VoiceConfigPanel } from "./voice-config-panel";

function clone(): VoiceConfig {
  return JSON.parse(JSON.stringify(FIXTURE_VOICE_CONFIG));
}

describe("VoiceConfigPanel", () => {
  it("renders connected numbers", () => {
    render(
      <VoiceConfigPanel
        config={clone()}
        save={async () => ({ ok: true })}
      />,
    );
    expect(screen.getByTestId("voice-number-vn-1").textContent).toMatch(
      /\+18005551234/,
    );
    expect(screen.getByTestId("voice-number-vn-2").textContent).toMatch(
      /\+442071838750/,
    );
  });

  it("shows empty state when there are no numbers", () => {
    const config = clone();
    config.numbers = [];
    render(
      <VoiceConfigPanel
        config={config}
        save={async () => ({ ok: true })}
      />,
    );
    expect(screen.getByTestId("voice-numbers-empty")).toBeInTheDocument();
  });

  it("save button is disabled until a provider changes", () => {
    render(
      <VoiceConfigPanel
        config={clone()}
        save={async () => ({ ok: true })}
      />,
    );
    expect(screen.getByTestId("voice-config-save")).toBeDisabled();
    fireEvent.change(screen.getByTestId("voice-asr-select"), {
      target: { value: "whisper" },
    });
    expect(screen.getByTestId("voice-config-save")).not.toBeDisabled();
  });

  it("persists provider selections via the save handler", async () => {
    let received: { asr_provider: string; tts_provider: string } | null = null;
    const save = async (next: {
      asr_provider: string;
      tts_provider: string;
    }) => {
      received = next;
      return { ok: true as const };
    };
    render(<VoiceConfigPanel config={clone()} save={save} />);
    fireEvent.change(screen.getByTestId("voice-asr-select"), {
      target: { value: "google" },
    });
    fireEvent.change(screen.getByTestId("voice-tts-select"), {
      target: { value: "polly" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("voice-config-save"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("voice-config-saved")).toBeInTheDocument();
    });
    expect(received).toEqual({
      asr_provider: "google",
      tts_provider: "polly",
    });
    // After a successful save the form is no longer dirty.
    expect(screen.getByTestId("voice-config-save")).toBeDisabled();
  });

  it("surfaces server-side save errors", async () => {
    render(
      <VoiceConfigPanel
        config={clone()}
        save={async () => ({ ok: false, error: "provider quota exceeded" })}
      />,
    );
    fireEvent.change(screen.getByTestId("voice-asr-select"), {
      target: { value: "whisper" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("voice-config-save"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("voice-config-error").textContent).toMatch(
        /quota/,
      );
    });
  });
});
