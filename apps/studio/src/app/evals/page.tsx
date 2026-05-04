import { EvalSuiteList } from "@/components/evals/eval-suite-list";
import { NewSuiteModal } from "@/components/evals/new-suite-modal";
import { listEvalSuites } from "@/lib/evals";

export const dynamic = "force-dynamic";

export default async function EvalsIndexPage() {
  const { items } = await listEvalSuites().catch(() => ({ items: [] }));
  const existingNames = items.map((s) => s.name);
  return (
    <main className="flex flex-col gap-4 p-6" data-testid="evals-page">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Evals</h1>
          <p className="text-sm text-muted-foreground">
            Suites of test cases that grade your agents on every change.
          </p>
        </div>
        <NewSuiteModal existingNames={existingNames} />
      </header>
      <EvalSuiteList suites={items} />
    </main>
  );
}
