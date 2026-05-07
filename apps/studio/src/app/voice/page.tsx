"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
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
  const [model, setModel] = useState<VoiceStageModel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setModel(null);
    setError(null);
    void fetchVoiceStageModel(active.id)
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
  }, [active]);

  if (wsLoading || !active || (!model && !error)) {
    return (
      <p className="p-6 text-sm text-muted-foreground" data-testid="voice-loading">
        Loading voice stage…
      </p>
    );
  }
  if (error) {
    return (
      <p className="p-6 text-sm text-red-600" role="alert">
        {error}
      </p>
    );
  }
  return <VoiceStage model={model!} workspaceId={active.id} />;
}
