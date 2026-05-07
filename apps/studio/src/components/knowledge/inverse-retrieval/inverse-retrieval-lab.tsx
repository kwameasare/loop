"use client";

import { useState } from "react";
import { Hammer, SearchCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ConfidenceMeter, EvidenceCallout, LiveBadge } from "@/components/target";
import type {
  InverseRetrievalMiss,
  InverseRetrievalModel,
} from "@/lib/knowledge-diagnostics";

const REPAIR_LABEL: Record<InverseRetrievalMiss["repair"], string> = {
  "re-chunk": "Re-chunk",
  "re-rank": "Re-rank",
  metadata: "Add metadata",
  instruction: "Instruction nudge",
};

export function InverseRetrievalLab({
  model,
}: {
  model: InverseRetrievalModel;
}) {
  const [repairs, setRepairs] = useState<string[]>([]);
  return (
    <section
      aria-labelledby="inverse-retrieval-heading"
      className="space-y-3"
      data-testid="inverse-retrieval-lab"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            Inverse Retrieval Lab
          </p>
          <h2 className="mt-1 text-lg font-semibold" id="inverse-retrieval-heading">
            What queries should have found this chunk?
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The lab starts from a chunk, finds production queries that should
            have retrieved it, explains each miss, and offers one-click repairs.
          </p>
        </div>
        <LiveBadge tone="staged">{model.misses.length} misses</LiveBadge>
      </div>

      <EvidenceCallout
        title={model.selectedChunkId}
        source={model.intendedCitation}
        tone="info"
        confidence={82}
      >
        {model.chunkPreview}
      </EvidenceCallout>

      <div className="grid gap-3 lg:grid-cols-3">
        {model.misses.map((miss) => {
          const repaired = repairs.includes(miss.id);
          return (
            <article key={miss.id} className="rounded-md border bg-card p-4">
              <div className="flex items-start justify-between gap-3">
                <SearchCheck className="mt-0.5 h-5 w-5 text-info" aria-hidden={true} />
                <LiveBadge tone={miss.closeness >= 85 ? "canary" : "staged"}>
                  {miss.closeness}% close
                </LiveBadge>
              </div>
              <h3 className="mt-3 text-sm font-semibold">{miss.productionQuery}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{miss.missReason}</p>
              <ConfidenceMeter
                className="mt-3"
                value={miss.closeness}
                label="Should-have-matched confidence"
                evidence={miss.evidenceRef}
              />
              <Button
                type="button"
                variant={repaired ? "subtle" : "outline"}
                size="sm"
                className="mt-3 w-full"
                onClick={() =>
                  setRepairs((current) =>
                    current.includes(miss.id) ? current : [...current, miss.id],
                  )
                }
              >
                <Hammer className="mr-2 h-4 w-4" />
                {repaired ? "Repair queued" : REPAIR_LABEL[miss.repair]}
              </Button>
            </article>
          );
        })}
      </div>
    </section>
  );
}
