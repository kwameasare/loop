import type { AgentSummary } from "@/lib/cp-api";

/**
 * Pure presentational list. Splitting the rendering away from the page's
 * data fetch keeps Vitest tests simple -- the test mounts AgentsList
 * directly with a fixture; the App Router page does the IO.
 */
export function AgentsList({ agents }: { agents: AgentSummary[] }) {
  if (agents.length === 0) {
    return (
      <p
        className="text-muted-foreground text-sm"
        data-testid="agents-empty"
      >
        No agents yet. Create one in the studio to get started.
      </p>
    );
  }
  return (
    <ul className="divide-y divide-border rounded-lg border" data-testid="agents-list">
      {agents.map((agent) => (
        <li
          key={agent.id}
          className="flex items-start justify-between gap-4 p-4"
          data-testid="agents-item"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-medium">{agent.name}</h3>
              <span
                className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
              >
                v{agent.active_version ?? "draft"}
              </span>
            </div>
            <p className="text-muted-foreground mt-1 text-sm">
              {agent.description || "No description yet."}
            </p>
            <p className="mt-1 text-xs text-zinc-500">slug: {agent.slug}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
