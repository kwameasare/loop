"use client";

import { Button } from "@/components/ui/button";

export default function AgentVersionsError({ reset }: { reset: () => void }) {
  return (
    <div className="rounded-lg border border-border p-4" role="alert">
      <h2 className="text-base font-medium">Versions could not load</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Refresh the agent version history and try again.
      </p>
      <Button className="mt-4" onClick={reset} variant="outline">
        Retry
      </Button>
    </div>
  );
}
