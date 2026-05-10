"use client";

/**
 * P0.3: ``/voice/config`` — voice channel configuration.
 *
 * Wires the panel to ``GET/PATCH /v1/workspaces/{id}/voice/config``.
 * If an older cp-api deployment returns 404, the panel marks the
 * evidence as degraded instead of pretending a real voice setup is
 * empty.
 */

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { WorkspaceRequiredState } from "@/components/section-states";
import { VoiceConfigPanel } from "@/components/voice/voice-config-panel";
import {
  createDegradedVoiceConfig,
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
  const activeWorkspaceId = active?.id;
  const [config, setConfig] = useState<VoiceConfig | null>(null);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    void fetchVoiceConfig(activeWorkspaceId)
      .then((c) => {
        if (cancelled) return;
        setConfig(c);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setConfig(
          createDegradedVoiceConfig(
            activeWorkspaceId,
            err instanceof Error ? err.message : "Could not load voice config",
          ),
        );
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId]);

  async function handleSave(
    next: Pick<VoiceConfig, "asr_provider" | "tts_provider">,
  ) {
    if (!activeWorkspaceId) return { ok: false, error: "No active workspace" };
    return saveVoiceConfig(activeWorkspaceId, next);
  }

  if (wsLoading) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-muted-foreground">Loading voice config…</p>
      </main>
    );
  }
  if (!activeWorkspaceId) return <WorkspaceRequiredState title="Voice Config" />;
  if (!config) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-muted-foreground">Loading voice config…</p>
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
