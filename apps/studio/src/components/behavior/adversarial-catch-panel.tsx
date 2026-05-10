"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  SearchCheck,
  XCircle,
} from "lucide-react";

import { LiveBadge, StatePanel } from "@/components/target";
import {
  listAdversarialCatches,
  resolveAdversarialCatch,
  runAdversarialProbe,
  type AdversarialCatch,
  type AdversarialProbeRunInput,
  type AdversarialProbeRunResponse,
  type AdversarialRiskClass,
  type CatchResolutionInput,
  type ListAdversarialCatchesResponse,
} from "@/lib/adversarial-catches";
import type { BehaviorSentence } from "@/lib/behavior";

export interface AdversarialCatchPanelProps {
  agentId: string;
  sentence: BehaviorSentence | null;
  initialCatchId?: string | undefined;
  runProbe?: (
    agentId: string,
    input: AdversarialProbeRunInput,
  ) => Promise<AdversarialProbeRunResponse>;
  resolveCatch?: (
    agentId: string,
    catchId: string,
    input: CatchResolutionInput,
  ) => Promise<AdversarialCatch>;
  listCatches?: (agentId: string) => Promise<ListAdversarialCatchesResponse>;
}

function riskForSentence(sentence: BehaviorSentence): AdversarialRiskClass {
  if (sentence.riskIds.length > 0) return "high";
  if (sentence.telemetry.contradictedTraces > 0) return "medium";
  return "low";
}

function defaultBudgetForRisk(risk: AdversarialRiskClass): number {
  return risk === "high" ? 4000 : risk === "medium" ? 2000 : 1000;
}

function defaultIntended(catchItem: AdversarialCatch | null): string {
  if (!catchItem) return "";
  if (catchItem.question.toLowerCase().includes("cumulatively")) {
    return "Apply the cap cumulatively across the whole conversation.";
  }
  return "Preserve the safer interpretation and require explicit escalation when uncertain.";
}

function defaultRejected(catchItem: AdversarialCatch | null): string {
  if (!catchItem) return "";
  if (catchItem.question.toLowerCase().includes("cumulatively")) {
    return "Do not allow multiple tool calls to bypass a refund cap.";
  }
  return "Do not let the agent silently pick an ambiguous interpretation.";
}

export function AdversarialCatchPanel({
  agentId,
  sentence,
  initialCatchId,
  runProbe = runAdversarialProbe,
  resolveCatch = resolveAdversarialCatch,
  listCatches = listAdversarialCatches,
}: AdversarialCatchPanelProps) {
  const [running, setRunning] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [loadingExisting, setLoadingExisting] = useState(false);
  const [catchItem, setCatchItem] = useState<AdversarialCatch | null>(null);
  const [resolved, setResolved] = useState<AdversarialCatch | null>(null);
  const [intended, setIntended] = useState("");
  const [rejected, setRejected] = useState("");
  const [dismissReason, setDismissReason] = useState("");
  const [createEvalCases, setCreateEvalCases] = useState(true);
  const [budgetTokens, setBudgetTokens] = useState(2000);
  const [error, setError] = useState<string | null>(null);
  const sentenceId = sentence?.id ?? null;

  useEffect(() => {
    if (!sentence) return;
    setBudgetTokens(defaultBudgetForRisk(riskForSentence(sentence)));
  }, [sentenceId]);

  useEffect(() => {
    let cancelled = false;
    setCatchItem(null);
    setResolved(null);
    setIntended("");
    setRejected("");
    setDismissReason("");
    setError(null);
    if (!sentenceId) return;

    setLoadingExisting(true);
    void listCatches(agentId)
      .then((response) => {
        if (cancelled) return;
        const matching =
          (initialCatchId
            ? response.items.find((item) => item.id === initialCatchId)
            : null) ??
          response.items.find(
            (item) => item.rule_id === sentenceId && item.status === "open",
          ) ??
          response.items.find((item) => item.rule_id === sentenceId) ??
          null;
        setCatchItem(matching);
        setResolved(
          matching && matching.status !== "open" ? matching : null,
        );
        setIntended(defaultIntended(matching));
        setRejected(defaultRejected(matching));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message =
          err instanceof Error
            ? err.message
            : "Could not load existing adversarial catches.";
        if (!message.includes("LOOP_CP_API_BASE_URL is required")) {
          setError(message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingExisting(false);
      });
    return () => {
      cancelled = true;
    };
  }, [agentId, initialCatchId, listCatches, sentenceId]);

  const probeInput = useMemo<AdversarialProbeRunInput | null>(() => {
    if (!sentence) return null;
    const riskClass = riskForSentence(sentence);
    return {
      rule_id: sentence.id,
      rule_text: sentence.text,
      risk_class: riskClass,
      budget_tokens: budgetTokens,
    };
  }, [budgetTokens, sentence]);

  async function handleRunProbe() {
    if (!probeInput) return;
    setRunning(true);
    setResolved(null);
    setError(null);
    try {
      const response = await runProbe(agentId, probeInput);
      const nextCatch = response.catches[0] ?? null;
      setCatchItem(nextCatch);
      setIntended(defaultIntended(nextCatch));
      setRejected(defaultRejected(nextCatch));
      setDismissReason("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not run the adversarial probe.",
      );
    } finally {
      setRunning(false);
    }
  }

  async function handleResolve(kind: "resolve" | "dismiss") {
    if (!catchItem) return;
    setResolving(true);
    setError(null);
    try {
      const response = await resolveCatch(agentId, catchItem.id, {
        intended_interpretation: kind === "resolve" ? intended : "",
        rejected_interpretation: kind === "resolve" ? rejected : "",
        dismiss_reason:
          kind === "dismiss"
            ? dismissReason.trim() || "Builder dismissed this catch as covered."
            : "",
        create_eval_cases: kind === "resolve" ? createEvalCases : false,
      });
      setResolved(response);
      setCatchItem(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not resolve this adversarial catch.",
      );
    } finally {
      setResolving(false);
    }
  }

  if (!sentence) {
    return (
      <StatePanel
        state="empty"
        title="Select a sentence to probe"
        className="rounded-md border bg-card"
      >
        Pick a behavior sentence before asking the platform to catch ambiguous
        edge cases.
      </StatePanel>
    );
  }

  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="adversarial-catch-panel"
      aria-labelledby="adversarial-catch-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Catch mechanic
          </p>
          <h3
            className="mt-1 text-sm font-semibold"
            id="adversarial-catch-heading"
          >
            Ask the calm adversarial question
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            The probe tries to find a plausible edge case, asks for the intended
            interpretation, then turns that answer into regression coverage.
          </p>
        </div>
        <LiveBadge tone={resolved ? "staged" : catchItem ? "draft" : "paused"}>
          {catchItem ? catchItem.status : "ready"}
        </LiveBadge>
      </div>

      <div className="mt-4 rounded-md border bg-background px-3 py-2 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Selected rule:</span>{" "}
        {sentence.text}
        <span className="mt-2 block">
          {loadingExisting
            ? "Checking persisted catches for this rule..."
            : catchItem
              ? `Persisted catch loaded from ${catchItem.evidence_ref}.`
              : "No persisted catch is open for this rule."}
        </span>
      </div>

      <label className="mt-4 block text-xs font-medium text-muted-foreground">
        Probe budget tokens
        <input
          className="mt-1 h-9 w-full rounded-md border bg-background px-2 text-sm text-foreground"
          type="number"
          min={100}
          max={20000}
          step={100}
          value={budgetTokens}
          onChange={(event) =>
            setBudgetTokens(Number(event.currentTarget.value))
          }
          data-testid="adversarial-probe-budget"
        />
      </label>

      <button
        type="button"
        className="mt-4 inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
        onClick={() => void handleRunProbe()}
        disabled={running}
        data-testid="run-adversarial-probe"
      >
        <SearchCheck className="h-4 w-4" aria-hidden />
        {running ? "Running probe" : "Run adversarial probe"}
      </button>

      {error ? (
        <StatePanel className="mt-4" state="error" title="Catch failed">
          {error}
        </StatePanel>
      ) : null}

      {catchItem ? (
        <div className="mt-4 space-y-4">
          <div className="rounded-md border border-warning/40 bg-warning/5 p-3">
            <div className="flex gap-2">
              <AlertTriangle
                className="mt-0.5 h-4 w-4 shrink-0 text-warning"
                aria-hidden
              />
              <div>
                <p
                  className="text-sm font-medium"
                  data-testid="adversarial-catch-question"
                >
                  {catchItem.question}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Scenario: {catchItem.generated_scenario}
                </p>
                <p className="mt-1 break-all text-xs text-muted-foreground">
                  Evidence: {catchItem.evidence_ref}
                </p>
              </div>
            </div>
          </div>

          <label className="block text-xs font-medium text-muted-foreground">
            Intended interpretation
            <textarea
              className="mt-1 min-h-20 w-full rounded-md border bg-background p-2 text-sm text-foreground"
              value={intended}
              onChange={(event) => setIntended(event.currentTarget.value)}
              data-testid="catch-intended"
            />
          </label>

          <label className="block text-xs font-medium text-muted-foreground">
            Rejected interpretation
            <textarea
              className="mt-1 min-h-20 w-full rounded-md border bg-background p-2 text-sm text-foreground"
              value={rejected}
              onChange={(event) => setRejected(event.currentTarget.value)}
              data-testid="catch-rejected"
            />
          </label>

          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border"
              checked={createEvalCases}
              onChange={(event) =>
                setCreateEvalCases(event.currentTarget.checked)
              }
            />
            Create accepted and rejected eval cases
          </label>

          <label className="block text-xs font-medium text-muted-foreground">
            Dismiss reason
            <textarea
              className="mt-1 min-h-16 w-full rounded-md border bg-background p-2 text-sm text-foreground"
              value={dismissReason}
              onChange={(event) => setDismissReason(event.currentTarget.value)}
              data-testid="catch-dismiss-reason"
              placeholder="Covered by existing policy, not applicable, or intentionally accepted risk."
            />
          </label>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
              disabled={
                resolving ||
                !intended.trim() ||
                !rejected.trim() ||
                catchItem.status !== "open"
              }
              onClick={() => void handleResolve("resolve")}
              data-testid="resolve-adversarial-catch"
            >
              <CheckCircle2 className="h-4 w-4" aria-hidden />
              {resolving ? "Resolving" : "Resolve and create evals"}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
              disabled={resolving || catchItem.status !== "open"}
              onClick={() => void handleResolve("dismiss")}
              data-testid="dismiss-adversarial-catch"
            >
              <XCircle className="h-4 w-4" aria-hidden />
              Dismiss
            </button>
          </div>

          {resolved ? (
            <StatePanel
              className="mt-4"
              state={resolved.status === "dismissed" ? "stale" : "success"}
              title={
                resolved.status === "dismissed"
                  ? "Catch dismissed"
                  : "Catch resolved"
              }
            >
              <p data-testid="adversarial-catch-result">
                {resolved.status === "dismissed"
                  ? "No eval cases were created."
                  : `${resolved.eval_case_refs.length} eval cases were created from this answer.`}
              </p>
            </StatePanel>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
