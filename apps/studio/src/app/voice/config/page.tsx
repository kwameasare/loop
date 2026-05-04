"use client";

/**
 * P0.3: ``/voice/config`` — voice channel configuration.
 *
 * Wires the panel to ``GET/PATCH /v1/workspaces/{id}/voice/config``.
 * The cp shim hasn't shipped yet; until then GET 404s and we render
 * a default config (no numbers, sensible provider defaults), and
 * PATCH surfaces the "blocked on cp-api PR" error to the user.
 */

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { VoiceConfigPanel } from "@/components/voice/voice-config-panel";
import {
  fetchVoiceConfig,
  saveVoiceConfig,
  type VoiceConfig,
} from "@/lib/voice-config";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function VoiceConfigPage(): JSX.Element {
  return (
    <RequireAuth>
      <VoiceConfigBody />
    </RequireAuth>
  );
}

function VoiceConfigBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [config, setConfig] = useState<VoiceConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    void fetchVoiceConfig(active.id)
      .then((c) => {
        if (cancelled) return;
        setConfig(c);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load voice config");
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  async function handleSave(
    next: Pick<VoiceConfig, "asr_provider" | "tts_provider">,
  ) {
    if (!active) return { ok: false, error: "No active workspace" };
    return saveVoiceConfig(active.id, next);
  }

  if (wsLoading || !active || (!config && !error)) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-muted-foreground">Loading voice config…</p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      </main>
    );
  }
  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          Voice channel configuration
        </h1>
        <p className="text-muted-foreground text-sm">
          Connect phone numbers and choose ASR / TTS providers for the voice
          channel.
        </p>
      </header>
      <VoiceConfigPanel config={config!} save={handleSave} />
    </main>
  );
}
