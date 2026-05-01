import { AgentsLoadingState } from "@/components/agents/agents-states";

export default function AgentsLoading() {
  return (
    <main className="container mx-auto flex max-w-3xl flex-col gap-6 py-10">
      <AgentsLoadingState />
    </main>
  );
}
