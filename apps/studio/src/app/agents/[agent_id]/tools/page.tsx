export default function AgentToolsPage() {
  return (
    <div className="flex flex-col gap-2" data-testid="agent-tools">
      <h2 className="text-lg font-medium">Tools</h2>
      <p className="text-sm text-muted-foreground">
        Tool catalog wired through MCP and HTTP servers. Tool browsing
        and binding land in follow-up stories.
      </p>
    </div>
  );
}
