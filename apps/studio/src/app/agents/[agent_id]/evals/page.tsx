import Link from "next/link";

import { EvalSuiteList } from "@/components/evals/eval-suite-list";
import { SectionDegraded, SectionEmpty } from "@/components/section-states";
import { listEvalSuites, type EvalSuite } from "@/lib/evals";
import { getAgentDetailData } from "../agent-detail-data";

interface PageProps {
  params: { agent_id: string };
}

function messageFromError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export default async function AgentEvalsPage({ params }: PageProps) {
  const { agent, degradedReason: agentDegradedReason } =
    await getAgentDetailData(params.agent_id);
  let suites: EvalSuite[] = [];
  let evalsDegradedReason: string | undefined;

  if (!agent.workspace_id || agent.workspace_id === "unavailable") {
    evalsDegradedReason =
      "Workspace context is required before loading agent eval suites.";
  } else {
    try {
      const result = await listEvalSuites({ workspaceId: agent.workspace_id });
      suites = result.items.filter(
        (suite) => suite.agentId === params.agent_id,
      );
      evalsDegradedReason = result.degraded_reason;
    } catch (error) {
      evalsDegradedReason = messageFromError(
        error,
        "Could not load eval suites.",
      );
    }
  }

  const degradedEvidence = [agentDegradedReason, evalsDegradedReason]
    .filter(Boolean)
    .join(" ");

  return (
    <section className="space-y-5" data-testid="agent-evals-page">
      <header className="rounded-md border bg-card p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Agent Workbench · Evals
        </p>
        <div className="mt-2 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-normal">
              Eval coverage for {agent.name || params.agent_id}
            </h2>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Keep deploy gates close to the agent. Preview failures, reviewer
              comments, operator resolutions, migration gaps, and production
              traces should become regression cases with provenance.
            </p>
          </div>
          <Link
            href={`/evals?agent_id=${encodeURIComponent(params.agent_id)}`}
            className="inline-flex w-fit rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            Open Eval Foundry
          </Link>
        </div>
      </header>

      {degradedEvidence ? (
        <SectionDegraded
          title="Agent evals"
          description="Agent-scoped eval evidence could not fully load from the control plane. Studio will not substitute fixture suites or claim this agent has no coverage."
          evidence={degradedEvidence}
        />
      ) : null}

      {suites.length > 0 ? (
        <div className="rounded-md border bg-card p-4">
          <EvalSuiteList suites={suites} />
        </div>
      ) : !degradedEvidence ? (
        <SectionEmpty
          title="Agent evals"
          description="No eval suites are attached to this agent yet. Create a starter suite from traces, simulator runs, operator resolutions, or migration transcripts before promoting."
          evidence={`agent=${params.agent_id}`}
          primaryAction={{
            label: "Create eval suite",
            href: `/evals?agent_id=${encodeURIComponent(params.agent_id)}`,
          }}
          secondaryAction={{
            label: "Open simulator",
            href: `/agents/${encodeURIComponent(params.agent_id)}/simulator`,
          }}
        />
      ) : null}
    </section>
  );
}
