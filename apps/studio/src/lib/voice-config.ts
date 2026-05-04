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

// ---------------------------------------------------------------- cp-api

export interface VoiceConfigClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function _voiceConfigBase(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw)
    throw new Error("LOOP_CP_API_BASE_URL is required for voice-config calls");
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

/**
 * Fetch the voice config for a workspace.
 *
 * Blocked on cp-api PR. Until the route ships, returns a default
 * empty config so the panel renders cleanly.
 */
export async function fetchVoiceConfig(
  workspace_id: string,
  opts: VoiceConfigClientOptions = {},
): Promise<VoiceConfig> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const url = `${_voiceConfigBase(opts.baseUrl)}/workspaces/${encodeURIComponent(
    workspace_id,
  )}/voice/config`;
  const res = await fetcher(url, {
    method: "GET",
    headers,
    cache: "no-store",
  });
  if (res.status === 404) {
    return {
      workspace_id,
      numbers: [],
      asr_provider: "deepgram",
      tts_provider: "elevenlabs",
    };
  }
  if (!res.ok) throw new Error(`cp-api GET voice/config -> ${res.status}`);
  return (await res.json()) as VoiceConfig;
}

/** Save provider selections. Returns the updated config. Blocked on cp-api PR. */
export async function saveVoiceConfig(
  workspace_id: string,
  next: Pick<VoiceConfig, "asr_provider" | "tts_provider">,
  opts: VoiceConfigClientOptions = {},
): Promise<{ ok: boolean; error?: string }> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const url = `${_voiceConfigBase(opts.baseUrl)}/workspaces/${encodeURIComponent(
    workspace_id,
  )}/voice/config`;
  const res = await fetcher(url, {
    method: "PATCH",
    headers,
    body: JSON.stringify(next),
    cache: "no-store",
  });
  if (res.status === 404) {
    return { ok: false, error: "Voice config API not yet available" };
  }
  if (!res.ok) {
    return { ok: false, error: `cp-api PATCH voice/config -> ${res.status}` };
  }
  return { ok: true };
}
