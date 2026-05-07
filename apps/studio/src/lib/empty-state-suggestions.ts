import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type EmptyStateSurface = "evals" | "kb" | "inbox";

export interface EmptyStateSuggestion {
  id: string;
  title: string;
  action_label: string;
  evidence_ref: string;
}

export async function fetchEmptyStateSuggestions(
  agentId: string,
  surface: EmptyStateSurface,
  opts: UxWireupClientOptions = {},
): Promise<EmptyStateSuggestion[]> {
  const result = await cpJson<{ items: EmptyStateSuggestion[] }>(
    `/agents/${encodeURIComponent(
      agentId,
    )}/empty-state-suggestions?surface=${encodeURIComponent(surface)}`,
    {
      ...opts,
      fallback: {
        items: [
          {
            id: `${surface}_starter`,
            title:
              surface === "evals"
                ? "Save these 12 turns from yesterday as a starter eval suite."
                : surface === "kb"
                  ? "Three KB chunks were cited often but failed two evals."
                  : "Turn the last operator resolution into an eval and a runbook.",
            action_label:
              surface === "evals"
                ? "Create starter suite"
                : surface === "kb"
                  ? "Review KB gaps"
                  : "Create resolution eval",
            evidence_ref: `empty-state/${agentId}/${surface}`,
          },
        ],
      },
    },
  );
  return result.items;
}
