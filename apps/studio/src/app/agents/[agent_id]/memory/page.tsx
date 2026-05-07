"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { MemoryStudio } from "@/components/memory/memory-studio";
import {
  deleteMemoryStudioEntry,
  fetchMemoryStudioData,
  type MemoryStudioData,
  type MemoryStudioEntry,
} from "@/lib/memory-studio";
import { useUser } from "@/lib/use-user";

interface AgentMemoryPageProps {
  params: { agent_id: string };
}

export default function AgentMemoryPage({ params }: AgentMemoryPageProps) {
  return (
    <RequireAuth>
      <AgentMemoryPageBody agentId={params.agent_id} />
    </RequireAuth>
  );
}

function AgentMemoryPageBody({ agentId }: { agentId: string }): JSX.Element {
  const { user } = useUser();
  const [data, setData] = useState<MemoryStudioData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    void fetchMemoryStudioData(agentId, user.sub)
      .then((next) => {
        if (cancelled) return;
        setData(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load memory");
      });
    return () => {
      cancelled = true;
    };
  }, [agentId, user]);

  if (!user) {
    return (
      <p className="p-6 text-sm text-muted-foreground">
        Sign in to inspect memory.
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
  if (!data) {
    return (
      <p className="p-6 text-sm text-muted-foreground" data-testid="memory-loading">
        Loading memory…
      </p>
    );
  }
  return (
    <MemoryStudio
      data={data}
      onDeleteEntry={(entry: MemoryStudioEntry) =>
        deleteMemoryStudioEntry(agentId, entry, user.sub)
      }
    />
  );
}
