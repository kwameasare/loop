import { ReleaseCandidatePanel } from "@/components/agents/release-candidate-panel";
import { SectionDegraded } from "@/components/section-states";
import { listAgentWorkflow } from "@/lib/agent-workflow";
import { getCpAuthOptions } from "@/lib/server/session";

export const dynamic = "force-dynamic";

interface AgentWorkflowPageProps {
  params: { agent_id: string };
  searchParams?: {
    branch_id?: string;
    change_set_id?: string;
  };
}

export default async function AgentWorkflowPage({
  params,
  searchParams,
}: AgentWorkflowPageProps) {
  const authOptions = getCpAuthOptions();
  const branchId = searchParams?.branch_id;
  const changeSetId = searchParams?.change_set_id;
  const workflow = await listAgentWorkflow(params.agent_id, authOptions).catch((error: unknown) => ({
    branches: [],
    change_sets: [],
    release_candidates: [],
    degraded_reason:
      error instanceof Error ? error.message : "Could not load agent workflow.",
  }));

  const selectedBranch = branchId
    ? workflow.branches.find((branch) => branch.id === branchId)
    : null;
  const selectedChangeSet = changeSetId
    ? workflow.change_sets.find((changeSet) => changeSet.id === changeSetId)
    : branchId
      ? workflow.change_sets.find((changeSet) => changeSet.branch_id === branchId)
      : null;

  return (
    <div className="flex flex-col gap-4" data-testid="agent-workflow-tab">
      <header className="instrument-panel rounded-2xl p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Agent workflow
        </p>
        <h2 className="mt-1 text-lg font-medium">Branches, Change Sets, and release candidates</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Replay forks, manual edits, tests, approvals, and release candidates
          stay on one auditable path before deployment.
        </p>
      </header>

      {branchId ? (
        <section
          className="rounded-md border border-info/40 bg-info/5 p-3 text-sm"
          data-testid="workflow-deep-link-context"
        >
          <p className="font-medium">
            Opened branch{" "}
            <span className="font-mono">
              {selectedBranch?.name ?? branchId}
            </span>
          </p>
          <p className="mt-1 text-muted-foreground">
            {selectedChangeSet
              ? `Change Set ${selectedChangeSet.id}: ${selectedChangeSet.name}`
              : "No Change Set is attached to this branch yet."}
          </p>
        </section>
      ) : null}

      {workflow.degraded_reason ? (
        <SectionDegraded
          title="Workflow evidence unavailable"
          description="Studio will not substitute local branch or Change Set fixtures for this route."
          evidence={workflow.degraded_reason}
        />
      ) : null}

      <ReleaseCandidatePanel
        agentId={params.agent_id}
        initialWorkflow={workflow}
      />
    </div>
  );
}
