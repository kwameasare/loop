import { EvalFoundry } from "@/components/evals/eval-foundry";
import { NewSuiteModal } from "@/components/evals/new-suite-modal";
import { getEvalFoundryModel, listEvalSuites } from "@/lib/evals";

export const dynamic = "force-dynamic";

export default async function EvalsIndexPage() {
  const evalSuitesResult = await listEvalSuites().catch((error: unknown) => ({
    items: [],
    degraded_reason:
      error instanceof Error ? error.message : "Could not load eval suites.",
    evidence_mode: "degraded" as const,
  }));
  const { items, degraded_reason: degradedReason } = evalSuitesResult;
  const existingNames = items.map((s) => s.name);
  const model = evalSuitesResult.evidence_mode
    ? getEvalFoundryModel(items, {
        evidenceMode: evalSuitesResult.evidence_mode,
      })
    : getEvalFoundryModel(items);
  const suggestionsAgentId = items[0]?.agentId;
  return (
    <EvalFoundry
      createAction={<NewSuiteModal existingNames={existingNames} />}
      degradedReason={degradedReason}
      model={model}
      suggestionsAgentId={suggestionsAgentId}
      suites={items}
    />
  );
}
