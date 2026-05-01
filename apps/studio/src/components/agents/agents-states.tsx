import { Button } from "@/components/ui/button";

export function AgentsLoadingState() {
  return (
    <div className="space-y-3" data-testid="agents-loading">
      <div className="h-20 rounded-lg border bg-muted" />
      <div className="h-20 rounded-lg border bg-muted" />
      <div className="h-20 rounded-lg border bg-muted" />
    </div>
  );
}

export function AgentsErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-border p-4" role="alert">
      <h2 className="text-base font-medium">Agents could not load</h2>
      <p className="text-muted-foreground mt-1 text-sm">
        Refresh the workspace data and try again.
      </p>
      <Button className="mt-4" onClick={onRetry} variant="outline">
        Retry
      </Button>
    </div>
  );
}
