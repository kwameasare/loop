export default function AgentSecretsPage() {
  return (
    <div className="flex flex-col gap-2" data-testid="agent-secrets">
      <h2 className="text-lg font-medium">Secrets</h2>
      <p className="text-sm text-muted-foreground">
        Per-agent secret references (provider keys, webhook signing
        secrets) appear here. Workspace-scoped secrets are managed under
        Settings.
      </p>
    </div>
  );
}
