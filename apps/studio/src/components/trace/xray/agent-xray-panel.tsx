import { EvidenceCallout, StatePanel } from "@/components/target";
import { buildAgentXrayModel, type AgentXrayClaim } from "@/lib/agent-xray";
import type { Trace } from "@/lib/traces";

function toneForClaim(claim: AgentXrayClaim) {
  if (claim.kind === "unsupported") return "warning" as const;
  if (claim.kind === "cost") return "neutral" as const;
  return "info" as const;
}

export function AgentXrayPanel({ trace }: { trace: Trace }) {
  const model = buildAgentXrayModel(trace);

  if (model.unsupportedReason) {
    return (
      <StatePanel state="empty" title="Agent X-Ray unavailable">
        {model.unsupportedReason}
      </StatePanel>
    );
  }

  return (
    <section
      aria-labelledby="agent-xray-heading"
      className="space-y-4"
      data-testid="agent-xray"
    >
      <div>
        <p className="text-xs font-medium uppercase text-muted-foreground">
          Agent X-Ray
        </p>
        <h2 className="mt-1 text-lg font-semibold" id="agent-xray-heading">
          Observed behavior from representative traces
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Claims open to trace and span evidence. Unsupported claims stay
          explicit instead of guessing.
        </p>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        {model.claims.map((claim) => (
          <EvidenceCallout
            key={claim.id}
            title={claim.title}
            source={claim.evidence}
            confidence={claim.confidence}
            confidenceLevel={
              claim.kind === "unsupported" ? "unsupported" : "medium"
            }
            tone={toneForClaim(claim)}
          >
            <div className="space-y-2">
              <p>{claim.statement}</p>
              <dl className="grid gap-1 text-xs">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Metric</dt>
                  <dd className="font-mono">{claim.metric}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">
                    Representative traces
                  </dt>
                  <dd
                    className="font-mono"
                    data-testid="xray-representative-trace"
                  >
                    {claim.representativeTraceIds.join(", ") || "none"}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">
                    Representative spans
                  </dt>
                  <dd className="font-mono">
                    {claim.representativeSpanIds.join(", ") || "unsupported"}
                  </dd>
                </div>
              </dl>
            </div>
          </EvidenceCallout>
        ))}
      </div>
    </section>
  );
}
