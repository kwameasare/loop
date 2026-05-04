export default function MembersLoading() {
  return (
    <main className="container mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <div className="h-8 w-40 rounded bg-muted" />
      <div className="space-y-2" data-testid="members-loading">
        <div className="h-10 rounded border bg-muted" />
        <div className="h-10 rounded border bg-muted" />
        <div className="h-10 rounded border bg-muted" />
      </div>
    </main>
  );
}
