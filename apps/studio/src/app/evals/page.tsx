import { EvalSuiteList } from "@/components/evals/eval-suite-list";
import { listEvalSuites } from "@/lib/evals";

export const dynamic = "force-dynamic";

export default async function EvalsIndexPage() {
  const { items } = await listEvalSuites();
  return (
    <main className="flex flex-col gap-4 p-6" data-testid="evals-page">
      <header>
        <h1 className="text-xl font-semibold">Evals</h1>
        <p className="text-sm text-muted-foreground">
          Suites of test cases that grade your agents on every change.
        </p>
      </header>
      <EvalSuiteList suites={items} />
    </main>
  );
}
