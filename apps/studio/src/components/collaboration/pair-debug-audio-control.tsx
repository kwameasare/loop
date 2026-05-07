"use client";

import { Mic, MicOff } from "lucide-react";
import { useState } from "react";

import {
  createPairDebugAudioSession,
  hasPairDebugPeerSupport,
  type PairDebugAudioSession,
} from "@/lib/pair-debug-audio";

interface PairDebugAudioControlProps {
  workspaceId: string;
  agentId: string;
  teammateCount: number;
  participantId?: string;
}

export function PairDebugAudioControl({
  workspaceId,
  agentId,
  teammateCount,
  participantId,
}: PairDebugAudioControlProps) {
  const [session, setSession] = useState<PairDebugAudioSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const peerSupported = hasPairDebugPeerSupport();
  const enabled = teammateCount > 0 && peerSupported;

  async function start(): Promise<void> {
    if (!enabled || session) return;
    setBusy(true);
    setError(null);
    try {
      setSession(
        await createPairDebugAudioSession(
          workspaceId,
          agentId,
          participantId ? { participantId } : {},
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pair audio failed.");
    } finally {
      setBusy(false);
    }
  }

  function stop(): void {
    setSession(null);
  }

  const label = session
    ? "Pair audio live"
    : teammateCount === 0
      ? "Pair audio waits for a teammate"
      : peerSupported
        ? "Start pair audio"
        : "Pair audio unavailable";

  return (
    <div className="relative" data-testid="pair-debug-audio">
      <button
        type="button"
        className="inline-flex h-8 items-center gap-2 rounded-md border bg-card px-2 text-xs font-medium target-transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
        onClick={() => (session ? stop() : void start())}
        disabled={!enabled || busy}
        aria-pressed={session !== null}
        aria-label={label}
        title={label}
      >
        {session ? (
          <MicOff className="h-3.5 w-3.5" aria-hidden />
        ) : (
          <Mic className="h-3.5 w-3.5" aria-hidden />
        )}
        <span className="hidden lg:inline">{busy ? "Joining" : label}</span>
      </button>
      {session ? (
        <p className="absolute right-0 mt-2 w-72 rounded-md border bg-popover p-2 text-xs shadow-sm">
          Human pair-debug audio is live for this agent. Session{" "}
          <span className="font-mono">{session.id}</span> expires at{" "}
          {new Date(session.expires_at).toLocaleTimeString()}.
        </p>
      ) : null}
      {error ? (
        <p className="absolute right-0 mt-2 w-72 rounded-md border bg-popover p-2 text-xs text-destructive shadow-sm">
          {error}
        </p>
      ) : null}
    </div>
  );
}
