import { EvalFoundry } from "@/components/evals/eval-foundry";
import { NewSuiteModal } from "@/components/evals/new-suite-modal";
import { getEvalFoundryModel, listEvalSuites } from "@/lib/evals";
import { listWorkspaces, type Workspace } from "@/lib/workspaces";

export const dynamic = "force-dynamic";

export function resolveEvalWorkspaceId(
  workspaces: readonly Workspace[],
  fallback: string | undefined = process.env.LOOP_DEFAULT_WORKSPACE_ID,
): string | null {
  return workspaces[0]?.id || fallback || null;
}

export default async function EvalsIndexPage() {
  const { workspaces, degraded_reason: workspacesDegradedReason } =
    await listWorkspaces().catch((error: unknown) => ({
      workspaces: [],
      degraded_reason:
        error instanceof Error
          ? error.message
          : "Could not load workspace context.",
    }));
  const workspaceId = resolveEvalWorkspaceId(workspaces);
  const evalSuitesResult = workspaceId
    ? await listEvalSuites({ workspaceId }).catch((error: unknown) => ({
        items: [],
        degraded_reason:
          error instanceof Error
            ? error.message
            : "Could not load eval suites.",
        evidence_mode: "degraded" as const,
      }))
    : {
        items: [],
        degraded_reason:
          "Workspace context is required before loading eval suites.",
        evidence_mode: "degraded" as const,
      };
  const { items, degraded_reason: degradedReason } = evalSuitesResult;
  const combinedDegradedReason = [workspacesDegradedReason, degradedReason]
    .filter(Boolean)
    .join(" ");
  const existingNames = items.map((s) => s.name);
  const model = evalSuitesResult.evidence_mode
    ? getEvalFoundryModel(items, {
        evidenceMode: evalSuitesResult.evidence_mode,
      })
    : getEvalFoundryModel(items);
  const suggestionsAgentId = items[0]?.agentId;
  return (
    <EvalFoundry
      createAction={
        <NewSuiteModal
          existingNames={existingNames}
          workspaceId={workspaceId}
        />
      }
      degradedReason={combinedDegradedReason || undefined}
      model={model}
      suggestionsAgentId={suggestionsAgentId}
      suites={items}
    />
  );
}
