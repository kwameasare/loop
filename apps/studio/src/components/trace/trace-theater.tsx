import {
  ConfidenceMeter,
  EvidenceCallout,
  LiveBadge,
  StatePanel,
} from "@/components/target";
import { TraceWaterfall } from "@/components/trace/waterfall";
import { formatDurationNs, formatUsd, type Trace } from "@/lib/traces";

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <div className="rounded-md border bg-card p-3" data-testid="trace-metric">
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-lg font-semibold">{value}</dd>
      {detail ? (
        <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
      ) : null}
    </div>
  );
}

function environmentTone(environment: string): "draft" | "staged" | "live" {
  if (environment === "production") return "live";
  if (environment === "staging") return "staged";
  return "draft";
}

export function TraceTheater({ trace }: { trace: Trace }) {
  const summary = trace.summary;
  const explanations = trace.explanations ?? [];
  const totalCost = summary?.total_cost_usd ?? 0;

  return (
    <div className="space-y-6" data-testid="trace-theater">
      {summary ? (
        <section
          aria-labelledby="trace-summary-heading"
          className="rounded-md border bg-surface p-4"
          data-testid="trace-summary"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase text-muted-foreground">
                Trace summary
              </p>
              <h2
                className="mt-1 text-xl font-semibold"
                id="trace-summary-heading"
              >
                {summary.outcome}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {summary.agent_name} on {summary.channel} in{" "}
                {summary.environment}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <LiveBadge tone={environmentTone(summary.environment)}>
                {summary.environment}
              </LiveBadge>
              <LiveBadge tone="canary">{summary.deploy_version}</LiveBadge>
            </div>
          </div>

          <dl className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Metric
              label="Latency"
              value={formatDurationNs(summary.total_latency_ns)}
              detail="End-to-end turn time"
            />
            <Metric
              label="Cost"
              value={formatUsd(totalCost)}
              detail="Line items in span inspector"
            />
            <Metric
              label="Model"
              value={summary.model}
              detail={summary.provider}
            />
            <Metric
              label="Tools"
              value={String(summary.tool_count)}
              detail={`${summary.retrieval_count} retrieval chunks`}
            />
            <Metric
              label="Memory writes"
              value={String(summary.memory_writes)}
              detail="Open memory span for before/after"
            />
            <Metric
              label="Eval"
              value={
                summary.eval_score === null
                  ? "Not attached"
                  : `${summary.eval_score}%`
              }
              detail={summary.eval_suite ?? "No eval suite linked"}
            />
            <Metric
              label="Snapshot"
              value={summary.snapshot_id}
              detail="Prompt, tools, KB, and deploy state"
            />
            <Metric
              label="Trace"
              value={trace.id}
              detail="Evidence source for this view"
            />
          </dl>
        </section>
      ) : (
        <StatePanel state="degraded" title="Trace metadata unavailable">
          The waterfall is available, but outcome, model, cost, eval, and deploy
          metadata were not returned. Inspect individual spans before making a
          production decision.
        </StatePanel>
      )}

      <section
        aria-labelledby="trace-explanations-heading"
        className="space-y-3"
        data-testid="trace-explanations"
      >
        <div>
          <h2 className="text-lg font-semibold" id="trace-explanations-heading">
            Explain without inventing
          </h2>
          <p className="text-sm text-muted-foreground">
            Every explanation cites a span fact, source chunk, eval result, or
            unsupported state.
          </p>
        </div>
        {explanations.length === 0 ? (
          <StatePanel state="empty" title="No explanations generated">
            No evidence-backed explanations are available. Open spans directly
            and use raw payloads, normalized payloads, and linked logs instead.
          </StatePanel>
        ) : (
          <div className="grid gap-3 lg:grid-cols-3">
            {explanations.map((explanation) => (
              <EvidenceCallout
                confidence={explanation.confidence}
                confidenceLevel={explanation.confidence_level}
                key={explanation.id}
                source={`${explanation.source_span_id}: ${explanation.evidence}`}
                title={explanation.title}
                tone={
                  explanation.confidence_level === "unsupported"
                    ? "warning"
                    : "info"
                }
              >
                {explanation.statement}
              </EvidenceCallout>
            ))}
          </div>
        )}
      </section>

      {summary ? (
        <ConfidenceMeter
          className="max-w-xl"
          evidence="Confidence is based on trace spans, retrieved chunks, eval metadata, and cost line items shown on this page."
          label="Trace evidence confidence"
          level={trace.explanations?.[0]?.confidence_level ?? "medium"}
          value={trace.explanations?.[0]?.confidence ?? 65}
        />
      ) : null}

      <TraceWaterfall trace={trace} />
    </div>
  );
}
