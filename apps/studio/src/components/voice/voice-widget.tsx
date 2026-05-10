"use client";

import { useEffect, useRef, useState } from "react";

import type {
  VoiceCallState,
  VoiceMode,
  VoiceTransport,
} from "@/lib/voice-transport";

export interface VoiceWidgetProps {
  agentName?: string;
  defaultMode?: VoiceMode;
  transport: VoiceTransport;
}

const STATE_LABEL: Record<VoiceCallState, string> = {
  idle: "Ready",
  connecting: "Connecting…",
  connected: "On call",
  ended: "Call ended",
  error: "Call failed",
};

const STATE_TONE: Record<VoiceCallState, string> = {
  idle: "bg-muted text-muted-foreground",
  connecting: "border border-warning/30 bg-warning/10 text-warning",
  connected: "border border-success/30 bg-success/10 text-success",
  ended: "bg-muted text-muted-foreground",
  error: "border border-destructive/30 bg-destructive/10 text-destructive",
};

export function VoiceWidget(props: VoiceWidgetProps) {
  const [state, setState] = useState<VoiceCallState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<VoiceMode>(props.defaultMode ?? "ptt");
  const [micActive, setMicActive] = useState(false);
  const [level, setLevel] = useState(0);
  const transportRef = useRef<VoiceTransport | null>(null);

  useEffect(() => {
    return () => {
      const t = transportRef.current;
      if (t) {
        t.disconnect().catch(() => undefined);
        transportRef.current = null;
      }
    };
  }, []);

  async function startCall() {
    if (state === "connecting" || state === "connected") return;
    setError(null);
    setState("connecting");
    transportRef.current = props.transport;
    const res = await props.transport.connect({
      mode,
      onState: (s, detail) => {
        setState(s);
        if (s === "error") setError(detail ?? "Call failed.");
      },
      onLevel: (l) => setLevel(l),
    });
    if (!res.ok) {
      setState("error");
      setError(res.error ?? "Microphone unavailable.");
      transportRef.current = null;
      return;
    }
    if (mode === "always_on") {
      props.transport.setMicEnabled(true);
      setMicActive(true);
    } else {
      setMicActive(false);
    }
  }

  async function endCall() {
    const t = transportRef.current;
    if (!t) {
      setState("ended");
      return;
    }
    await t.disconnect();
    transportRef.current = null;
    setMicActive(false);
    setState("ended");
  }

  function applyMicState(enabled: boolean) {
    setMicActive(enabled);
    transportRef.current?.setMicEnabled(enabled);
  }

  const onCall = state === "connecting" || state === "connected";

  return (
    <section
      aria-label="Voice channel widget"
      className="flex w-full max-w-sm flex-col gap-3 rounded-2xl border bg-card p-4 shadow-sm"
      data-testid="voice-widget"
    >
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase text-muted-foreground">Call agent</p>
          <h3 className="text-lg font-semibold tracking-tight">
            {props.agentName ?? "Voice agent"}
          </h3>
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-xs ${STATE_TONE[state]}`}
          data-testid="voice-state"
        >
          {STATE_LABEL[state]}
        </span>
      </header>

      <fieldset
        className="flex gap-2 text-xs"
        data-testid="voice-mode"
        disabled={onCall}
      >
        <legend className="sr-only">Microphone mode</legend>
        <label
          className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded border px-2 py-1 ${
            mode === "ptt" ? "border-info bg-info/10" : "border-border"
          }`}
        >
          <input
            checked={mode === "ptt"}
            data-testid="voice-mode-ptt"
            name="voice-mode"
            onChange={() => setMode("ptt")}
            type="radio"
            value="ptt"
          />
          Push-to-talk
        </label>
        <label
          className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded border px-2 py-1 ${
            mode === "always_on" ? "border-info bg-info/10" : "border-border"
          }`}
        >
          <input
            checked={mode === "always_on"}
            data-testid="voice-mode-always-on"
            name="voice-mode"
            onChange={() => setMode("always_on")}
            type="radio"
            value="always_on"
          />
          Always-on
        </label>
      </fieldset>

      {onCall ? (
        <div
          aria-label="Microphone activity"
          aria-valuemax={1}
          aria-valuemin={0}
          aria-valuenow={level}
          className="h-2 w-full overflow-hidden rounded-full bg-muted"
          data-testid="voice-level"
          role="meter"
        >
          <div
            className={micActive ? "h-full bg-success" : "h-full bg-border"}
            style={{ width: `${Math.min(100, Math.round(level * 100))}%` }}
          />
        </div>
      ) : null}

      {state !== "connected" || mode === "always_on" ? null : (
        <button
          aria-pressed={micActive}
          className={`rounded-lg px-3 py-2 text-sm font-medium ${
            micActive
              ? "bg-success text-success-foreground"
              : "bg-muted text-foreground"
          }`}
          data-testid="voice-ptt"
          onMouseDown={() => applyMicState(true)}
          onMouseLeave={() => applyMicState(false)}
          onMouseUp={() => applyMicState(false)}
          onTouchEnd={() => applyMicState(false)}
          onTouchStart={() => applyMicState(true)}
          type="button"
        >
          {micActive ? "Mic open — release to mute" : "Hold to talk"}
        </button>
      )}

      <div className="flex justify-between gap-2">
        {onCall ? (
          <button
            className="flex-1 rounded-lg bg-destructive px-3 py-2 text-sm font-semibold text-destructive-foreground hover:bg-destructive/90"
            data-testid="voice-end"
            onClick={() => {
              void endCall();
            }}
            type="button"
          >
            End call
          </button>
        ) : (
          <button
            className="flex-1 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            data-testid="voice-call"
            onClick={() => {
              void startCall();
            }}
            type="button"
          >
            Call agent
          </button>
        )}
      </div>

      {error ? (
        <p
          className="rounded border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive"
          data-testid="voice-error"
          role="alert"
        >
          {error}
        </p>
      ) : null}
    </section>
  );
}
