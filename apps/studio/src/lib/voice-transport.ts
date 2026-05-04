/**
 * Voice channel widget transport contract.
 *
 * The studio mounts a real WebRTC transport in production; the
 * widget itself only ever talks to this interface so tests can
 * inject a deterministic stub. The transport is responsible for:
 *
 *   1. Acquiring the microphone (``connect``).
 *   2. Toggling whether audio is currently sent to the agent
 *      (``setMicEnabled`` — used in PTT mode).
 *   3. Tearing down the call (``disconnect``).
 */

export type VoiceMode = "ptt" | "always_on";

export type VoiceCallState =
  | "idle"
  | "connecting"
  | "connected"
  | "ended"
  | "error";

export interface VoiceTransport {
  connect(opts: {
    mode: VoiceMode;
    onState: (state: VoiceCallState, detail?: string) => void;
    onLevel?: (level: number) => void;
  }): Promise<{ ok: boolean; error?: string }>;
  setMicEnabled(enabled: boolean): void;
  disconnect(): Promise<void>;
}

// ---------------------------------------------------------------- cp-api

export interface MintVoiceTokenResponse {
  /** Short-lived JWT the LiveKit client uses to join the room. */
  token: string;
  /** wss:// URL the LiveKit client connects to. */
  url: string;
  /** Room the agent will be present in. */
  room: string;
  /** Identity to publish under (mirrored back from the request, plus a salt). */
  identity: string;
}

export interface MintVoiceTokenOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function _voiceBase(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) throw new Error("LOOP_CP_API_BASE_URL is required for voice calls");
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

/**
 * Mint a LiveKit access token for the given agent.
 *
 * Blocked on cp-api PR: ``POST /v1/voice/mint_token`` is not yet
 * mounted on cp. Until it ships the call returns null and the page
 * renders the "voice unavailable" empty state. When it lands the
 * studio's WebRTC transport can swap from the fixture to a real
 * LiveKit-room transport.
 */
export async function mintVoiceToken(
  args: { agent_id: string; identity?: string },
  opts: MintVoiceTokenOptions = {},
): Promise<MintVoiceTokenResponse | null> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const url = `${_voiceBase(opts.baseUrl)}/voice/mint_token`;
  const res = await fetcher(url, {
    method: "POST",
    headers,
    body: JSON.stringify(args),
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`cp-api POST voice/mint_token -> ${res.status}`);
  return (await res.json()) as MintVoiceTokenResponse;
}

/**
 * Inert in-process transport used by the studio fixture page and
 * by tests that need a default. It stays in ``connecting`` until
 * the caller manually drives it via the returned controller.
 */
export function makeFixtureTransport(): VoiceTransport & {
  emit: (state: VoiceCallState, detail?: string) => void;
  emitLevel: (level: number) => void;
  micEnabled: boolean;
} {
  let onState: ((state: VoiceCallState, detail?: string) => void) | null =
    null;
  let onLevel: ((level: number) => void) | null = null;
  let micEnabled = true;

  return {
    async connect(opts) {
      onState = opts.onState;
      onLevel = opts.onLevel ?? null;
      micEnabled = opts.mode === "always_on";
      onState("connecting");
      return { ok: true };
    },
    setMicEnabled(enabled: boolean) {
      micEnabled = enabled;
    },
    async disconnect() {
      if (onState) onState("ended");
    },
    emit(state, detail) {
      if (onState) onState(state, detail);
    },
    emitLevel(level) {
      if (onLevel) onLevel(level);
    },
    get micEnabled() {
      return micEnabled;
    },
  };
}
