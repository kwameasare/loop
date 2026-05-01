import { AgentsList } from "@/components/agents/agents-list";
import { listAgents } from "@/lib/cp-api";

export const dynamic = "force-dynamic";

/**
 * /agents -- read-only landing page for the agent registry.
 *
 * Server component: the generated cp-api client calls GET /v1/agents
 * at request time so the page reflects the caller's active workspace.
 */
export default async function AgentsPage() {
  const { agents } = await listAgents();
  return (
    <main className="container mx-auto flex max-w-3xl flex-col gap-6 py-10">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight">Agents</h1>
        <p className="text-muted-foreground">
          Browse the agents in this workspace. Click an agent to inspect
          its conversations, tools, and recent traces.
        </p>
      </header>
      <AgentsList agents={agents} />
    </main>
  );
}
