"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import { VoiceStage } from "@/components/voice/voice-stage";
import {
  fetchVoiceStageModel,
  type VoiceStageModel,
} from "@/lib/voice-stage";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function VoicePage(): JSX.Element {
  return (
    <RequireAuth>
      <VoicePageBody />
    </RequireAuth>
  );
}

function VoicePageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const activeWorkspaceId = active?.id;
  const [model, setModel] = useState<VoiceStageModel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    setModel(null);
    setError(null);
    void fetchVoiceStageModel(activeWorkspaceId)
      .then((next) => {
        if (cancelled) return;
        setModel(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load voice");
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId]);

  if (wsLoading) {
    return (
      <p className="p-6 text-sm text-muted-foreground" data-testid="voice-loading">
        Loading voice stage…
      </p>
    );
  }
  if (!activeWorkspaceId) return <WorkspaceRequiredState title="Voice Stage" />;
  if (!model && !error) {
    return (
      <p className="p-6 text-sm text-muted-foreground" data-testid="voice-loading">
        Loading voice stage…
      </p>
    );
  }
  if (error) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <SectionDegraded
          title="Voice Stage"
          description="Voice channel evidence is unavailable. Studio will not replace missing phone, ASR, TTS, or latency data with a local voice fixture."
          evidence={error}
        />
      </main>
    );
  }
  return <VoiceStage model={model!} workspaceId={activeWorkspaceId} />;
}
