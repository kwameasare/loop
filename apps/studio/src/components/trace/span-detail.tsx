"use client";

import { useState } from "react";

import {
  formatDurationNs,
  formatUsd,
  type Span,
  type TracePayload,
} from "@/lib/traces";

type Tab =
  | "attributes"
  | "io"
  | "payloads"
  | "redactions"
  | "cost"
  | "links"
  | "events"
  | "raw";

const TABS: { id: Tab; label: string }[] = [
  { id: "attributes", label: "Attributes" },
  { id: "io", label: "Inputs and outputs" },
  { id: "payloads", label: "Payloads" },
  { id: "redactions", label: "Redactions" },
  { id: "cost", label: "Cost and retries" },
  { id: "links", label: "Links" },
  { id: "events", label: "Events" },
  { id: "raw", label: "Raw" },
];

const STATUS_CLASS: Record<Span["status"], string> = {
  ok: "text-success",
  error: "text-destructive",
  unset: "text-muted-foreground",
};

function JsonBlock({
  label,
  value,
}: {
  label: string;
  value: TracePayload | Span | undefined;
}) {
  if (!value || Object.keys(value).length === 0) {
    return (
      <p className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
        No {label.toLowerCase()} recorded for this span.
      </p>
    );
  }
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
        {label}
      </h3>
      <pre className="max-h-72 overflow-auto rounded-md border bg-muted/30 p-3 text-xs">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

export function SpanDetail({ span }: { span: Span }) {
  const [tab, setTab] = useState<Tab>("attributes");
  const retryHistory = span.retry_history ?? [];
  const redactions = span.redactions ?? [];
  const links = span.links;

  return (
    <section
      aria-label="Span inspector"
      className="rounded-md border bg-card p-4"
      data-testid="span-detail"
    >
      <header className="mb-4 space-y-2">
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">
            Span inspector
          </p>
          <h2 className="mt-1 break-words text-base font-semibold">
            {span.name}
          </h2>
        </div>
        <dl className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <dt className="text-muted-foreground">Service</dt>
            <dd className="font-mono">{span.service}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Kind</dt>
            <dd>
              {span.category} / {span.kind}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Duration</dt>
            <dd>{formatDurationNs(span.end_ns - span.start_ns)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Status</dt>
            <dd className={`font-medium ${STATUS_CLASS[span.status]}`}>
              {span.status}
            </dd>
          </div>
        </dl>
      </header>

      <div className="mb-4 flex flex-wrap gap-1 border-b" role="tablist">
        {TABS.map((item) => {
          const isActive = tab === item.id;
          return (
            <button
              aria-selected={isActive}
              className={`rounded-t-md px-3 py-1.5 text-sm target-transition ${
                isActive
                  ? "border-b-2 border-primary font-medium"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              data-testid={`span-tab-${item.id}`}
              key={item.id}
              onClick={() => setTab(item.id)}
              role="tab"
              type="button"
            >
              {item.label}
            </button>
          );
        })}
      </div>

      <div role="tabpanel" data-testid={`span-panel-${tab}`}>
        {tab === "attributes" ? (
          <dl className="grid grid-cols-1 gap-2 text-sm">
            {Object.entries(span.attributes).length === 0 ? (
              <p className="text-muted-foreground">No attributes recorded.</p>
            ) : (
              Object.entries(span.attributes).map(([k, v]) => (
                <div className="flex justify-between gap-3" key={k}>
                  <dt className="font-mono text-xs text-muted-foreground">
                    {k}
                  </dt>
                  <dd className="break-all font-mono text-xs">{String(v)}</dd>
                </div>
              ))
            )}
          </dl>
        ) : null}

        {tab === "io" ? (
          <div className="space-y-3">
            <JsonBlock label="Inputs" value={span.input} />
            <JsonBlock label="Outputs" value={span.output} />
          </div>
        ) : null}

        {tab === "payloads" ? (
          <div className="space-y-3">
            <JsonBlock label="Raw payload" value={span.raw_payload} />
            <JsonBlock
              label="Normalized payload"
              value={span.normalized_payload}
            />
          </div>
        ) : null}

        {tab === "redactions" ? (
          <div className="space-y-3">
            {redactions.length === 0 ? (
              <p className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
                No redactions reported for this span. If payloads contain PII,
                open the raw payload and verify the redaction policy.
              </p>
            ) : (
              redactions.map((redaction) => (
                <article
                  className="rounded-md border p-3"
                  key={redaction.field}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-mono text-sm">{redaction.field}</h3>
                    <span className="rounded-md border bg-muted px-2 py-0.5 text-xs">
                      {redaction.reason}
                    </span>
                  </div>
                  <p className="mt-2 text-sm">
                    Replaced with <code>{redaction.replacement}</code>.
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Evidence: {redaction.evidence}
                  </p>
                </article>
              ))
            )}
          </div>
        ) : null}

        {tab === "cost" ? (
          <div className="space-y-4">
            {span.cost ? (
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-muted-foreground">Prompt tokens</dt>
                  <dd>{span.cost.prompt_tokens.toLocaleString("en-US")}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Completion tokens</dt>
                  <dd>{span.cost.completion_tokens.toLocaleString("en-US")}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Input cost</dt>
                  <dd>{formatUsd(span.cost.input_usd)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Output cost</dt>
                  <dd>{formatUsd(span.cost.output_usd)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Tool cost</dt>
                  <dd>{formatUsd(span.cost.tool_usd)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Total</dt>
                  <dd className="font-semibold">
                    {formatUsd(span.cost.total_usd)}
                  </dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-muted-foreground">Budget source</dt>
                  <dd>{span.cost.budget_source}</dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">
                No cost math recorded for this span.
              </p>
            )}

            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
                Retry history
              </h3>
              {retryHistory.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No retries recorded for this span.
                </p>
              ) : (
                <ul className="space-y-2">
                  {retryHistory.map((retry) => (
                    <li
                      className="rounded-md border p-2 text-sm"
                      key={retry.attempt}
                    >
                      Attempt {retry.attempt}: {retry.status},{" "}
                      {formatDurationNs(retry.latency_ns)}. {retry.evidence}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ) : null}

        {tab === "links" ? (
          <div className="space-y-3 text-sm">
            <div>
              <h3 className="text-xs font-semibold uppercase text-muted-foreground">
                Linked logs
              </h3>
              {links && links.logs.length > 0 ? (
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {links.logs.map((log) => (
                    <li className="font-mono text-xs" key={log}>
                      {log}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-muted-foreground">No linked logs.</p>
              )}
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase text-muted-foreground">
                Eval cases
              </h3>
              {links && links.eval_cases.length > 0 ? (
                <p className="mt-2 font-mono text-xs">
                  {links.eval_cases.join(", ")}
                </p>
              ) : (
                <p className="mt-2 text-muted-foreground">
                  No linked eval cases.
                </p>
              )}
            </div>
            <dl className="grid gap-2">
              <div>
                <dt className="text-xs font-semibold uppercase text-muted-foreground">
                  Migration source
                </dt>
                <dd className="font-mono text-xs">
                  {links?.migration_source ?? "none"}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase text-muted-foreground">
                  Deploy version
                </dt>
                <dd className="font-mono text-xs">
                  {links?.deploy_version ?? "none"}
                </dd>
              </div>
            </dl>
          </div>
        ) : null}

        {tab === "events" ? (
          <ul className="space-y-2 text-sm">
            {span.events.length === 0 ? (
              <p className="text-muted-foreground">No events recorded.</p>
            ) : (
              span.events.map((event, i) => (
                <li
                  className="rounded-md border p-2"
                  key={`${event.name}-${i}`}
                >
                  <div className="flex justify-between gap-3 text-xs">
                    <span className="font-medium">{event.name}</span>
                    <span className="text-muted-foreground">
                      {formatDurationNs(event.timestamp_ns - span.start_ns)} in
                    </span>
                  </div>
                  {event.attributes ? (
                    <pre className="mt-2 overflow-auto rounded bg-muted/30 p-2 text-xs">
                      {JSON.stringify(event.attributes, null, 2)}
                    </pre>
                  ) : null}
                </li>
              ))
            )}
          </ul>
        ) : null}

        {tab === "raw" ? <JsonBlock label="Raw span" value={span} /> : null}
      </div>
    </section>
  );
}
