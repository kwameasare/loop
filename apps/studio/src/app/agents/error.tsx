"use client";

import { AgentsErrorState } from "@/components/agents/agents-states";

export default function AgentsError({ reset }: { reset: () => void }) {
  return (
    <main className="container mx-auto flex max-w-3xl flex-col gap-6 py-10">
      <AgentsErrorState onRetry={reset} />
    </main>
  );
}
