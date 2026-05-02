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
