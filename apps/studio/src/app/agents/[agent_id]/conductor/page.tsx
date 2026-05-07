"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ConductorStudio } from "@/components/conductor/conductor-studio";
import {
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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchConductorData(agentId)
      .then((next) => {
        if (cancelled) return;
        setData(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load conductor");
      });
    return () => {
      cancelled = true;
    };
  }, [agentId]);

  if (error) {
    return (
      <p className="p-6 text-sm text-red-600" role="alert">
        {error}
      </p>
    );
  }
  if (!data) {
    return (
      <p className="p-6 text-sm text-muted-foreground" data-testid="conductor-loading">
        Loading conductor…
      </p>
    );
  }
  return <ConductorStudio data={data} />;
}
