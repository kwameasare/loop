/**
 * Voice channel configuration types and fixture data for the studio.
 */

export type AsrProvider = "deepgram" | "whisper" | "google";
export type TtsProvider = "elevenlabs" | "openai" | "polly";

export interface VoiceNumber {
  id: string;
  e164: string;
  label: string;
  region: string;
  /** ISO timestamp (ms) when the number was provisioned. */
  provisioned_at_ms: number;
}

export interface VoiceConfig {
  workspace_id: string;
  numbers: VoiceNumber[];
  asr_provider: AsrProvider;
  tts_provider: TtsProvider;
}

export const ASR_PROVIDERS: { id: AsrProvider; label: string }[] = [
  { id: "deepgram", label: "Deepgram (Nova-2)" },
  { id: "whisper", label: "OpenAI Whisper-large-v3" },
  { id: "google", label: "Google Speech-to-Text v2" },
];

export const TTS_PROVIDERS: { id: TtsProvider; label: string }[] = [
  { id: "elevenlabs", label: "ElevenLabs Turbo v2" },
  { id: "openai", label: "OpenAI tts-1-hd" },
  { id: "polly", label: "Amazon Polly Neural" },
];

export const FIXTURE_VOICE_CONFIG: VoiceConfig = {
  workspace_id: "ws-fixture",
  asr_provider: "deepgram",
  tts_provider: "elevenlabs",
  numbers: [
    {
      id: "vn-1",
      e164: "+18005551234",
      label: "Care line",
      region: "us-east-1",
      provisioned_at_ms: Date.UTC(2026, 1, 12, 14, 0, 0),
    },
    {
      id: "vn-2",
      e164: "+442071838750",
      label: "UK billing",
      region: "eu-west-1",
      provisioned_at_ms: Date.UTC(2026, 2, 3, 9, 30, 0),
    },
  ],
};

export type SaveVoiceConfigFn = (
  next: Pick<VoiceConfig, "asr_provider" | "tts_provider">,
) => Promise<{ ok: boolean; error?: string }>;
