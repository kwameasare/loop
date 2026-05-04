import type { AgentTool } from "@/lib/agent-tools";

export function ToolsList({ tools }: { tools: AgentTool[] }) {
  if (tools.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="tools-empty">
        No tools bound to this agent yet.
      </p>
    );
  }
  return (
    <ul
      className="divide-y divide-border rounded-lg border"
      data-testid="tools-list"
    >
      {tools.map((tool) => (
        <li
          key={tool.id}
          className="flex items-start justify-between gap-4 p-4"
          data-testid="tools-item"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-medium">{tool.name}</h3>
              <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                {tool.kind}
              </span>
            </div>
            {tool.description ? (
              <p className="mt-1 text-sm text-muted-foreground">
                {tool.description}
              </p>
            ) : null}
            {tool.source ? (
              <p className="mt-1 font-mono text-xs text-zinc-500">
                {tool.source}
              </p>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}
