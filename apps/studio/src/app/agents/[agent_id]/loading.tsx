export default function AgentDetailLoading() {
  return (
    <main
      className="container mx-auto flex max-w-4xl flex-col gap-6 py-10"
      data-testid="agent-detail-loading"
    >
      <p className="text-sm text-muted-foreground">Loading agent…</p>
    </main>
  );
}
