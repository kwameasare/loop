"use client";

import { useState } from "react";
import { Mic, ShieldCheck, Volume2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EvidenceCallout, LiveBadge } from "@/components/target";
import {
  startVoiceDemoSession,
  type VoiceDemoLinkAccess,
  type VoiceDemoSession,
} from "@/lib/voice-demo";

export function VoiceDemoLanding({
  demo,
  token,
}: {
  demo: VoiceDemoLinkAccess;
  token: string;
}): JSX.Element {
  const [micState, setMicState] = useState<"idle" | "checking" | "ready" | "failed">(
    "idle",
  );
  const [session, setSession] = useState<VoiceDemoSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runMicTest(): Promise<void> {
    setMicState("checking");
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setMicState("ready");
    } catch {
      setMicState("failed");
      setError("Microphone permission is required before this voice demo can start.");
    }
  }

  async function startSession(): Promise<void> {
    setError(null);
    try {
      setSession(await startVoiceDemoSession(token));
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Could not start the voice demo session.",
      );
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 p-6">
      <header className="instrument-panel rounded-2xl p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase text-muted-foreground">
              Voice demo
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">
              Short-lived stakeholder voice access
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              This link is scoped to one snapshot, expires automatically, and
              records demo traces under the workspace audit policy.
            </p>
          </div>
          <LiveBadge tone={demo.status === "active" ? "live" : "paused"}>
            {demo.status}
          </LiveBadge>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <article className="instrument-panel rounded-2xl p-4">
          <p className="text-xs uppercase text-muted-foreground">Snapshot</p>
          <p className="mt-2 font-mono text-sm">{demo.snapshot_id}</p>
        </article>
        <article className="instrument-panel rounded-2xl p-4">
          <p className="text-xs uppercase text-muted-foreground">Expires</p>
          <p className="mt-2 text-sm">{new Date(demo.expires_at).toLocaleString()}</p>
        </article>
        <article className="instrument-panel rounded-2xl p-4">
          <p className="text-xs uppercase text-muted-foreground">Rate limit</p>
          <p className="mt-2 text-sm">{demo.rate_limit}</p>
        </article>
      </section>

      <section className="grid gap-4 md:grid-cols-[0.9fr_1.1fr]">
        <div className="instrument-panel rounded-2xl p-4">
          <div className="flex items-center gap-3">
            <Mic className="h-5 w-5 text-info" aria-hidden={true} />
            <div>
              <h2 className="text-sm font-semibold">Browser mic test</h2>
              <p className="text-xs text-muted-foreground">
                Required before the voice room can open.
              </p>
            </div>
          </div>
          <Button
            className="mt-4 w-full"
            type="button"
            variant={micState === "ready" ? "subtle" : "default"}
            onClick={() => void runMicTest()}
          >
            {micState === "ready"
              ? "Microphone ready"
              : micState === "checking"
                ? "Checking microphone"
                : "Run mic test"}
          </Button>
          <Button
            className="mt-3 w-full"
            type="button"
            variant="outline"
            disabled={micState !== "ready"}
            onClick={() => void startSession()}
          >
            <Volume2 className="mr-2 h-4 w-4" />
            Start voice demo
          </Button>
          {error ? (
            <p className="mt-3 text-xs text-destructive" role="alert">
              {error}
            </p>
          ) : null}
        </div>

        <div className="space-y-4">
          <EvidenceCallout
            title="Redaction policy"
            tone="neutral"
            source="voice-demo/redaction"
          >
            {demo.redaction_policy}
          </EvidenceCallout>
          <EvidenceCallout
            title="Trace capture policy"
            tone="info"
            source="voice-demo/trace-capture"
          >
            {demo.trace_capture_policy}
          </EvidenceCallout>
        </div>
      </section>

      {session ? (
        <section className="instrument-panel rounded-2xl p-4" data-testid="voice-demo-session">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-success" aria-hidden={true} />
            <div>
              <h2 className="text-sm font-semibold">Voice room ready</h2>
              <p className="text-xs text-muted-foreground">
                Session {session.id} expires with this link.
              </p>
            </div>
          </div>
          <dl className="mt-4 grid gap-3 text-sm md:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Room</dt>
              <dd className="font-mono">{session.room}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Identity</dt>
              <dd className="font-mono">{session.identity}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">LiveKit</dt>
              <dd className="truncate font-mono">{session.livekit_url}</dd>
            </div>
          </dl>
        </section>
      ) : null}
    </main>
  );
}
