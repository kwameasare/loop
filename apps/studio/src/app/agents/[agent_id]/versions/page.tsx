export default function AgentVersionsPage() {
  return (
    <div className="flex flex-col gap-2" data-testid="agent-versions">
      <h2 className="text-lg font-medium">Versions</h2>
      <p className="text-sm text-muted-foreground">
        Version history, deploy state, and rollback controls land here in
        a follow-up story.
      </p>
    </div>
  );
}
