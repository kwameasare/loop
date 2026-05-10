"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { MemoryStudio } from "@/components/memory/memory-studio";
import {
  createDegradedMemoryStudioData,
  deleteMemoryStudioEntry,
  fetchMemoryStudioData,
  type MemoryStudioData,
  type MemoryStudioEntry,
} from "@/lib/memory-studio";
import {
  approveMemoryPolicy,
  upsertMemoryPolicy,
} from "@/lib/memory-policies";
import { useUser } from "@/lib/use-user";

interface AgentMemoryPageProps {
  params: { agent_id: string };
  searchParams?: { policy_id?: string | string[] | undefined } | undefined;
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default function AgentMemoryPage({
  params,
  searchParams,
}: AgentMemoryPageProps) {
  return (
    <RequireAuth>
      <AgentMemoryPageBody
        agentId={params.agent_id}
        initialPolicyId={firstParam(searchParams?.policy_id)}
      />
    </RequireAuth>
  );
}

function AgentMemoryPageBody({
  agentId,
  initialPolicyId,
}: {
  agentId: string;
  initialPolicyId?: string | undefined;
}): JSX.Element {
  const { user } = useUser();
  const [data, setData] = useState<MemoryStudioData | null>(null);

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
        setData(
          createDegradedMemoryStudioData(
            agentId,
            err instanceof Error ? err.message : "Could not load memory",
          ),
        );
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
  if (!data) {
    return (
      <p
        className="p-6 text-sm text-muted-foreground"
        data-testid="memory-loading"
      >
        Loading memory…
      </p>
    );
  }
  return (
    <MemoryStudio
      data={data}
      initialPolicyId={initialPolicyId}
      onDeleteEntry={(entry: MemoryStudioEntry) =>
        deleteMemoryStudioEntry(agentId, entry, user.sub)
      }
      onSavePolicy={(policy) => upsertMemoryPolicy(agentId, policy)}
      onApprovePolicy={(scope) => approveMemoryPolicy(agentId, scope)}
    />
  );
}
