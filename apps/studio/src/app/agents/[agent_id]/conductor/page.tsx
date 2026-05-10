"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ConductorStudio } from "@/components/conductor/conductor-studio";
import {
  createEmptyConductorData,
  fetchConductorData,
  type ConductorData,
} from "@/lib/conductor";

interface AgentConductorPageProps {
  params: { agent_id: string };
}

export default function AgentConductorPage({
  params,
}: AgentConductorPageProps) {
  return (
    <RequireAuth>
      <AgentConductorPageBody agentId={params.agent_id} />
    </RequireAuth>
  );
}

function AgentConductorPageBody({ agentId }: { agentId: string }): JSX.Element {
  const [data, setData] = useState<ConductorData | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchConductorData(agentId)
      .then((next) => {
        if (cancelled) return;
        setData(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setData(
          createEmptyConductorData(
            agentId,
            err instanceof Error ? err.message : "Could not load conductor",
          ),
        );
      });
    return () => {
      cancelled = true;
    };
  }, [agentId]);

  if (!data) {
    return (
      <p className="p-6 text-sm text-muted-foreground" data-testid="conductor-loading">
        Loading conductor…
      </p>
    );
  }
  return <ConductorStudio data={data} />;
}
