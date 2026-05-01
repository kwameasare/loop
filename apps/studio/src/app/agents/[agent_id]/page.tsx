interface AgentOverviewPageProps {
  params: { agent_id: string };
}

/**
 * Default tab — high-level summary of the agent. Real content lands in
 * follow-up stories (active version, latest deploys, recent traces).
 */
export default function AgentOverviewPage({ params }: AgentOverviewPageProps) {
  return (
    <div className="flex flex-col gap-2" data-testid="agent-overview">
      <h2 className="text-lg font-medium">Overview</h2>
      <p className="text-sm text-muted-foreground">
        Agent <code>{params.agent_id}</code>. The overview tab will surface the
        active version, latest deploys, and recent activity in upcoming
        stories.
      </p>
    </div>
  );
}
