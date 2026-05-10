import Link from "next/link";

import { SectionDegraded, SectionEmpty } from "@/components/section-states";
import { TraceList } from "@/components/trace/trace-list";
import { searchTraces, type TraceSummary } from "@/lib/traces";
import { getAgentDetailData } from "../agent-detail-data";

interface PageProps {
  params: { agent_id: string };
}

function messageFromError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export default async function AgentTracesPage({ params }: PageProps) {
  const { agent, degradedReason: agentDegradedReason } =
    await getAgentDetailData(params.agent_id);
  let traces: TraceSummary[] = [];
  let tracesDegradedReason: string | undefined;

  if (!agent.workspace_id || agent.workspace_id === "unavailable") {
    tracesDegradedReason =
      agentDegradedReason === undefined
        ? "Workspace context is unavailable, so Studio cannot request agent-scoped trace evidence."
        : undefined;
  } else {
    try {
      const result = await searchTraces(agent.workspace_id, {
        agent_id: params.agent_id,
        page_size: 100,
      });
      traces = result.traces;
    } catch (error) {
      tracesDegradedReason = messageFromError(
        error,
        "Could not load agent traces.",
      );
    }
  }

  const degradedEvidence = [agentDegradedReason, tracesDegradedReason]
    .filter(Boolean)
    .join(" ");

  return (
    <section className="space-y-5" data-testid="agent-traces-page">
      <header className="rounded-md border bg-card p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Agent Workbench · Traces
        </p>
        <div className="mt-2 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-normal">
              Trace evidence for {agent.name || params.agent_id}
            </h2>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Inspect the selected agent&apos;s production turns without leaving
              the workbench. Trace rows link to Trace Theater for span context,
              tool calls, retrieval, policy checks, cost, latency, and replay.
            </p>
          </div>
          <Link
            href={`/traces?agent_id=${encodeURIComponent(params.agent_id)}`}
            className="inline-flex w-fit rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            Open Trace Theater
          </Link>
        </div>
      </header>

      {degradedEvidence ? (
        <SectionDegraded
          title="Agent traces"
          description="Agent-scoped trace evidence could not fully load from the control plane. Studio will not substitute fixture turns for this agent."
          evidence={degradedEvidence}
        />
      ) : null}

      {traces.length > 0 ? (
        <TraceList traces={traces} initialPageSize={10} />
      ) : !degradedEvidence ? (
        <SectionEmpty
          title="Agent traces"
          description="No persisted traces were returned for this agent yet. Send a preview or production turn, then return here to inspect span evidence."
          evidence={`workspace=${agent.workspace_id}; agent=${params.agent_id}`}
          primaryAction={{
            label: "Open simulator",
            href: `/agents/${encodeURIComponent(params.agent_id)}/simulator`,
          }}
          secondaryAction={{ label: "Open all traces", href: "/traces" }}
        />
      ) : null}
    </section>
  );
}
