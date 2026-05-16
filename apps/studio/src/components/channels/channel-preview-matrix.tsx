"use client";

import { useMemo, useState } from "react";

import {
  CHANNEL_ORDER,
  type ChannelBinding,
  type ChannelBindingType,
  type ChannelPreviewEvalCaseSeed,
  type ChannelPreviewMatrixRequest,
  type ChannelPreviewMatrixResponse,
  channelLabel,
  createChannelPreviewEvalCase as defaultCreateChannelPreviewEvalCase,
  previewChannelMatrix as defaultPreviewChannelMatrix,
} from "@/lib/channel-bindings";
import { cn } from "@/lib/utils";

interface ChannelPreviewMatrixProps {
  agentId: string;
  bindings: ChannelBinding[];
  previewChannelMatrix?: (
    agentId: string,
    input: ChannelPreviewMatrixRequest,
  ) => Promise<ChannelPreviewMatrixResponse>;
  createChannelPreviewEvalCase?: (
    agentId: string,
    input: ChannelPreviewEvalCaseSeed,
  ) => Promise<{ case_id: string }>;
}

function initialSelected(bindings: ChannelBinding[]) {
  const configured = bindings
    .filter((binding) => binding.status !== "not_configured")
    .map((binding) => binding.channel_type);
  return configured.length > 0 ? configured : [...CHANNEL_ORDER];
}

function rowClass(state: string) {
  if (state === "ready") return "border-success/40 bg-success/10";
  if (state === "blocked") return "border-destructive/40 bg-destructive/10";
  if (state === "needs_readiness") return "border-warning/40 bg-warning/10";
  return "border-border bg-background";
}

export function ChannelPreviewMatrix({
  agentId,
  bindings,
  previewChannelMatrix = defaultPreviewChannelMatrix,
  createChannelPreviewEvalCase = defaultCreateChannelPreviewEvalCase,
}: ChannelPreviewMatrixProps) {
  const [scenarioTitle, setScenarioTitle] = useState("Duplicate charge");
  const [userMessage, setUserMessage] = useState(
    "I was charged twice for my annual renewal. What happens now?",
  );
  const [expectedOutcome, setExpectedOutcome] = useState(
    "Acknowledge the duplicate charge, verify the account, explain the refund path, and offer escalation if the account lookup does not resolve it.",
  );
  const [selected, setSelected] = useState<ChannelBindingType[]>(() =>
    initialSelected(bindings),
  );
  const [matrix, setMatrix] = useState<ChannelPreviewMatrixResponse | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [savedCaseId, setSavedCaseId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const bindingsByType = useMemo(
    () => new Map(bindings.map((binding) => [binding.channel_type, binding])),
    [bindings],
  );

  function toggleChannel(channelType: ChannelBindingType) {
    setSelected((current) =>
      current.includes(channelType)
        ? current.filter((item) => item !== channelType)
        : [...current, channelType],
    );
  }

  async function renderMatrix() {
    setBusy(true);
    setSavedCaseId(null);
    setError(null);
    try {
      const result = await previewChannelMatrix(agentId, {
        scenario_title: scenarioTitle,
        user_message: userMessage,
        expected_outcome: expectedOutcome,
        channel_types: selected,
      });
      setMatrix(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Channel preview requires cp-api.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function saveEval(seed: ChannelPreviewEvalCaseSeed) {
    setError(null);
    try {
      const response = await createChannelPreviewEvalCase(agentId, seed);
      setSavedCaseId(response.case_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Saving the eval case requires cp-api.",
      );
    }
  }

  return (
    <section
      className="space-y-4 instrument-panel rounded-2xl p-4"
      data-testid="channel-preview-matrix"
      aria-labelledby="channel-preview-matrix-heading"
    >
      <header className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h3
            id="channel-preview-matrix-heading"
            className="text-sm font-semibold"
          >
            Channel preview matrix
          </h3>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Render the same scenario across peer channels and turn formatting
            failures into eval coverage.
          </p>
        </div>
        <p className="rounded-md border bg-background px-3 py-2 text-xs text-muted-foreground">
          {selected.length} selected · readiness shown per binding
        </p>
      </header>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.7fr)]">
        <label className="space-y-1 text-sm">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Scenario
          </span>
          <input
            value={scenarioTitle}
            onChange={(event) => setScenarioTitle(event.target.value)}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
          />
        </label>
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Channels
          </p>
          <div className="flex flex-wrap gap-2">
            {CHANNEL_ORDER.map((channelType) => {
              const binding = bindingsByType.get(channelType);
              const active = selected.includes(channelType);
              return (
                <button
                  key={channelType}
                  type="button"
                  onClick={() => toggleChannel(channelType)}
                  className={cn(
                    "rounded-md border px-2.5 py-1.5 text-xs transition-colors",
                    active
                      ? "border-primary bg-primary text-primary-foreground"
                      : "bg-background text-muted-foreground hover:bg-muted",
                  )}
                  aria-pressed={active}
                >
                  {channelLabel(channelType)}
                  <span className="ml-1 opacity-75">
                    {binding?.status.replace("_", " ") ?? "missing"}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <label className="space-y-1 text-sm">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          User message
        </span>
        <textarea
          value={userMessage}
          onChange={(event) => setUserMessage(event.target.value)}
          rows={2}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
        />
      </label>

      <label className="space-y-1 text-sm">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Expected outcome
        </span>
        <textarea
          value={expectedOutcome}
          onChange={(event) => setExpectedOutcome(event.target.value)}
          rows={3}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
        />
      </label>

      <button
        type="button"
        onClick={() => void renderMatrix()}
        disabled={busy || selected.length === 0}
        className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-transform hover:-translate-y-0.5 disabled:pointer-events-none disabled:opacity-50"
      >
        {busy ? "Rendering..." : "Render preview matrix"}
      </button>

      {error ? (
        <p
          className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </p>
      ) : null}

      {matrix ? (
        <div className="space-y-3" data-testid="channel-preview-matrix-results">
          <div className="grid gap-2 text-xs md:grid-cols-3">
            <div className="rounded-md border bg-background p-3">
              <span className="text-muted-foreground">Channels</span>
              <strong className="ml-2">{matrix.summary.channels}</strong>
            </div>
            <div className="rounded-md border bg-background p-3">
              <span className="text-muted-foreground">Ready</span>
              <strong className="ml-2">{matrix.summary.ready_channels}</strong>
            </div>
            <div className="rounded-md border bg-background p-3">
              <span className="text-muted-foreground">Format failures</span>
              <strong className="ml-2">
                {matrix.summary.formatting_failures}
              </strong>
            </div>
          </div>

          <div className="grid gap-3 xl:grid-cols-2">
            {matrix.rows.map((row) => (
              <article
                key={row.channel_type}
                className={cn(
                  "rounded-md border p-3",
                  rowClass(row.readiness_state),
                )}
                data-testid={`channel-preview-row-${row.channel_type}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold">
                      {row.display_name}
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      {row.provider} · {row.readiness_state.replace("_", " ")}
                    </p>
                  </div>
                  <span className="rounded-md border bg-background px-2 py-0.5 text-[0.7rem]">
                    {row.binding_status.replace("_", " ")}
                  </span>
                </div>

                <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-md border bg-background p-3 text-xs leading-relaxed">
                  {row.rendered_preview}
                </pre>

                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Adaptation
                    </p>
                    <ul className="mt-1 space-y-1 text-xs">
                      {row.adaptation_notes.map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Constraints
                    </p>
                    <ul className="mt-1 space-y-1 text-xs">
                      {row.constraints.slice(0, 3).map((constraint) => (
                        <li key={constraint}>{constraint}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                {row.formatting_failures.length > 0 ? (
                  <div className="mt-3 rounded-md border bg-background p-3">
                    <p className="text-xs font-medium">Formatting failures</p>
                    <ul className="mt-2 space-y-2">
                      {row.formatting_failures.map((failure) => (
                        <li key={failure.id} className="text-xs">
                          <span className="font-medium">
                            {failure.severity}:
                          </span>{" "}
                          {failure.message}
                        </li>
                      ))}
                    </ul>
                    <button
                      type="button"
                      className="mt-3 rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted"
                      onClick={() =>
                        void saveEval({
                          ...row.eval_case_seed,
                          failure_reason:
                            row.formatting_failures[0]?.message ??
                            row.eval_case_seed.failure_reason,
                        })
                      }
                    >
                      Save as eval case
                    </button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      ) : (
        <p className="rounded-md border bg-background p-3 text-sm text-muted-foreground">
          No preview rendered yet. Select channels and render a scenario to see
          channel-specific constraints before rollout.
        </p>
      )}

      {savedCaseId ? (
        <p className="rounded-md border border-success/40 bg-success/10 p-3 text-sm text-success">
          Eval case saved: {savedCaseId}
        </p>
      ) : null}
    </section>
  );
}
