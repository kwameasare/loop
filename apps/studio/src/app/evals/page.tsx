import { EvalFoundry } from "@/components/evals/eval-foundry";
import { NewSuiteModal } from "@/components/evals/new-suite-modal";
import { getEvalFoundryModel, listEvalSuites } from "@/lib/evals";

export const dynamic = "force-dynamic";

export default async function EvalsIndexPage() {
  const { items } = await listEvalSuites().catch(() => ({ items: [] }));
  const existingNames = items.map((s) => s.name);
  const model = getEvalFoundryModel(items);
  return (
    <EvalFoundry
      createAction={<NewSuiteModal existingNames={existingNames} />}
      model={model}
      suites={items}
    />
  );
}
