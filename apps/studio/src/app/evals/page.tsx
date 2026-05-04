import { EvalSuiteList } from "@/components/evals/eval-suite-list";
import { NewSuiteModal } from "@/components/evals/new-suite-modal";
import { listAgents } from "@/lib/cp-api";
import { listEvalSuites } from "@/lib/evals";

export const dynamic = "force-dynamic";

export default async function EvalsIndexPage() {
  // Fetch the suite list and the agent registry in parallel — the
  // form needs the agents to populate the picker.
  const [{ items }, { agents }] = await Promise.all([
    listEvalSuites(),
    listAgents().catch(() => ({ agents: [] })),
  ]);
  const existingNames = items.map((s) => s.name);
  const agentIds = agents.map((a) => a.id).filter(Boolean);
  return (
    <main className="flex flex-col gap-4 p-6" data-testid="evals-page">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Evals</h1>
          <p className="text-sm text-muted-foreground">
            Suites of test cases that grade your agents on every change.
          </p>
        </div>
        <NewSuiteModal existingNames={existingNames} agentIds={agentIds} />
      </header>
      <EvalSuiteList suites={items} />
    </main>
  );
}
