"use client";

/**
 * P0.3: ``/voice`` — voice channel preview.
 *
 * Calls cp-api ``POST /v1/voice/mint_token`` to obtain a LiveKit
 * room token. The cp shim isn't shipped yet
 * (``packages/control-plane/loop_control_plane/app.py`` does not
 * register a voice router). On 404 the page renders a clear
 * "voice unavailable" empty state instead of mounting the fixture
 * transport — so customers don't see a fake working widget.
 */

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { VoiceWidget } from "@/components/voice/voice-widget";
import {
  makeFixtureTransport,
  mintVoiceToken,
  type MintVoiceTokenResponse,
  type VoiceTransport,
} from "@/lib/voice-transport";

const VOICE_AGENT_ID = "00000000-0000-0000-0000-000000000000";

export default function VoicePage(): JSX.Element {
  return (
    <RequireAuth>
      <VoicePageBody />
    </RequireAuth>
  );
}

function VoicePageBody(): JSX.Element {
  const [token, setToken] = useState<MintVoiceTokenResponse | null | undefined>(
    undefined,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void mintVoiceToken({ agent_id: VOICE_AGENT_ID })
      .then((t) => {
        if (cancelled) return;
        setToken(t);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not mint voice token");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      </main>
    );
  }
  if (token === undefined) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-muted-foreground" data-testid="voice-loading">
          Connecting to voice…
        </p>
      </main>
    );
  }
  if (token === null) {
    return (
      <main className="container mx-auto p-6">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">Voice channel</h1>
        </header>
        <div className="rounded-lg border p-4" role="status">
          <h2 className="text-base font-medium">Voice is not yet available.</h2>
          <p className="text-muted-foreground mt-1 text-sm">
            The cp-api voice ``/voice/mint_token`` route hasn&apos;t shipped
            yet. This page lights up automatically once it does.
          </p>
        </div>
      </main>
    );
  }

  // The fixture transport is the only one currently checked into
  // studio; the LiveKit-backed transport is a follow-up since it
  // requires the livekit-client package and webrtc-aware tests. We
  // keep the page wired so the swap is one component change once the
  // cp shim lands.
  const transport: VoiceTransport = makeFixtureTransport();

  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Voice channel</h1>
        <p className="text-muted-foreground text-sm">
          Embed this widget anywhere in the studio to talk to your agent
          directly in the browser. Push-to-talk and always-on modes are both
          supported.
        </p>
        <p className="text-muted-foreground mt-1 text-xs font-mono" data-testid="voice-room">
          room: {token.room}
        </p>
      </header>
      <VoiceWidget agentName="Voice Concierge" transport={transport} />
    </main>
  );
}
