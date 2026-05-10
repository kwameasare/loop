import Link from "next/link";

import { EvalSuiteList } from "@/components/evals/eval-suite-list";
import { SectionDegraded, SectionEmpty } from "@/components/section-states";
import { listEvalSuites, type EvalSuite } from "@/lib/evals";
import { getAgentDetailData } from "../agent-detail-data";

interface PageProps {
  params: { agent_id: string };
  searchParams?:
    | {
        suite_id?: string | string[] | undefined;
        case_id?: string | string[] | undefined;
        filter?: string | string[] | undefined;
        source?: string | string[] | undefined;
        view?: string | string[] | undefined;
      }
    | undefined;
}

function messageFromError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function focusedEvalQuery(
  searchParams: PageProps["searchParams"],
): { label: string; detail: string; testId: string } | null {
  const filter = firstParam(searchParams?.filter);
  if (filter === "affected") {
    return {
      label: "Affected evals",
      detail:
        "Opened from Workbench evidence. Review suites and cases likely to move under the current behavior, knowledge, memory, or deploy change before promotion.",
      testId: "agent-evals-focused-affected",
    };
  }

  const source = firstParam(searchParams?.source);
  if (source === "knowledge") {
    return {
      label: "Knowledge-sourced evals",
      detail:
        "Opened from knowledge evidence. Cases should preserve source chunk, retrieval query, expected citation behavior, and risk tags before they gate deploys.",
      testId: "agent-evals-focused-knowledge",
    };
  }

  const view = firstParam(searchParams?.view);
  if (view === "gates") {
    return {
      label: "Deploy gates",
      detail:
        "Opened from release evidence. Confirm every blocking gate points to a real eval result ref before approving a Change Package.",
      testId: "agent-evals-focused-gates",
    };
  }

  return null;
}

export default async function AgentEvalsPage({
  params,
  searchParams,
}: PageProps) {
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
  const focusedSuiteId = firstParam(searchParams?.suite_id);
  const focusedCaseId = firstParam(searchParams?.case_id);
  const focusedQuery = focusedEvalQuery(searchParams);

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

      {focusedCaseId ? (
        <section
          className="rounded-md border border-info/40 bg-info/5 p-4 text-sm text-info"
          data-testid="agent-evals-focused-case"
        >
          <p className="font-medium">Opened eval case from evidence link.</p>
          <p className="mt-1 font-mono text-xs">{focusedCaseId}</p>
          <Link
            href={`/evals?agent_id=${encodeURIComponent(
              params.agent_id,
            )}&case_id=${encodeURIComponent(focusedCaseId)}`}
            className="mt-3 inline-flex rounded-md border border-info/40 bg-background px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            Open case in Eval Foundry
          </Link>
        </section>
      ) : null}

      {focusedQuery ? (
        <section
          className="rounded-md border border-info/40 bg-info/5 p-4 text-sm text-info"
          data-testid={focusedQuery.testId}
        >
          <p className="font-medium">{focusedQuery.label}</p>
          <p className="mt-1">{focusedQuery.detail}</p>
          <Link
            href={`/evals?agent_id=${encodeURIComponent(params.agent_id)}`}
            className="mt-3 inline-flex rounded-md border border-info/40 bg-background px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            Open in Eval Foundry
          </Link>
        </section>
      ) : null}

      {suites.length > 0 ? (
        <div className="rounded-md border bg-card p-4">
          <EvalSuiteList suites={suites} focusedSuiteId={focusedSuiteId} />
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
