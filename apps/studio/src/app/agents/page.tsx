import { AgentsList } from "@/components/agents/agents-list";
import { NewAgentModal } from "@/components/agents/new-agent-modal";
import { listAgents } from "@/lib/cp-api";
import { listWorkspaces } from "@/lib/workspaces";

export const dynamic = "force-dynamic";

/**
 * /agents -- the agent registry index.
 *
 * Server component: the generated cp-api client calls GET /v1/agents
 * at request time so the page reflects the caller's active workspace.
 * Existing slugs are passed to the client-side NewAgentModal so it can
 * validate uniqueness before round-tripping POST /v1/agents.
 */
export default async function AgentsPage() {
  const { agents } = await listAgents().catch(() => ({ agents: [] }));
  const { workspaces } = await listWorkspaces().catch(() => ({
    workspaces: [],
  }));
  const existingSlugs = agents.map((a) => a.slug).filter(Boolean);
  const workspaceId =
    agents[0]?.workspace_id ||
    workspaces[0]?.id ||
    process.env.LOOP_DEFAULT_WORKSPACE_ID;
  return (
    <main className="container mx-auto flex max-w-3xl flex-col gap-6 py-10">
      <header className="flex flex-col gap-2">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-3xl font-semibold tracking-tight">Agents</h1>
          <NewAgentModal
            existingSlugs={existingSlugs}
            workspaceId={workspaceId}
          />
        </div>
        <p className="text-muted-foreground">
          Browse the agents in this workspace. Click an agent to inspect its
          conversations, tools, and recent traces.
        </p>
      </header>
      <AgentsList agents={agents} />
    </main>
  );
}
