"use client";

/**
 * P0.3: "New suite" modal launched from /evals.
 *
 * Pure client form so it can validate uniqueness before round-tripping
 * cp-api. The page hands in the existing slug list (used to flag
 * collisions early) and a submit handler that resolves with the
 * created suite — the page refreshes in place.
 */

import { useId, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { createEvalSuite, type CreateEvalSuiteInput } from "@/lib/evals";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const SLUG_RE = /^[a-z][a-z0-9_\-]{1,63}$/;

export interface NewSuiteModalProps {
  /** Existing suite names (to surface duplicate-name errors before POST). */
  existingNames: string[];
  createSuite?: (input: CreateEvalSuiteInput) => Promise<{ id: string }>;
}

const METRIC_OPTIONS = [
  { value: "accuracy", label: "Accuracy" },
  { value: "latency_p95", label: "Latency p95" },
  { value: "cost", label: "Cost" },
  { value: "toxicity", label: "Toxicity" },
] as const;

export function NewSuiteModal({
  existingNames,
  createSuite = createEvalSuite,
}: NewSuiteModalProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [datasetRef, setDatasetRef] = useState("");
  const [metrics, setMetrics] = useState<string[]>(["accuracy"]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const formId = useId();

  function reset() {
    setName("");
    setDatasetRef("");
    setMetrics(["accuracy"]);
    setError(null);
    setSubmitting(false);
  }

  function toggleMetric(metric: string) {
    setMetrics((current) =>
      current.includes(metric)
        ? current.filter((m) => m !== metric)
        : [...current, metric],
    );
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const trimmed = name.trim();
    if (!SLUG_RE.test(trimmed)) {
      setError(
        "Name must start with a lowercase letter and contain only lowercase letters, digits, dashes or underscores.",
      );
      return;
    }
    if (existingNames.includes(trimmed)) {
      setError("A suite with this name already exists.");
      return;
    }
    if (!datasetRef.trim()) {
      setError("Dataset ref is required.");
      return;
    }
    if (metrics.length === 0) {
      setError("Select at least one metric.");
      return;
    }
    setSubmitting(true);
    try {
      const created = await createSuite({
        name: trimmed,
        dataset_ref: datasetRef.trim(),
        metrics,
      });
      setOpen(false);
      reset();
      router.push(`/evals/suites/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create suite");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen && !submitting) {
          reset();
        }
      }}
    >
      <DialogTrigger asChild>
        <Button
          type="button"
          onClick={() => setOpen(true)}
          data-testid="new-suite-open"
        >
          New suite
        </Button>
      </DialogTrigger>
      <DialogContent
        className="max-w-md"
        data-testid="new-suite-modal"
      >
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-3"
          data-testid="new-suite-form"
        >
          <DialogHeader>
            <DialogTitle>New suite</DialogTitle>
            <DialogDescription>
              Start with a dataset, then attach scorers, fixtures, thresholds,
              and deploy gates in the suite builder.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-1">
            <label
              className="text-xs text-muted-foreground"
              htmlFor={`${formId}-name`}
            >
              Name
            </label>
            <input
              autoFocus
              id={`${formId}-name`}
              className="rounded border border-border bg-background px-2 py-1 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="support-smoke"
              disabled={submitting}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label
              className="text-xs text-muted-foreground"
              htmlFor={`${formId}-dataset-ref`}
            >
              Dataset ref
            </label>
            <input
              id={`${formId}-dataset-ref`}
              className="rounded border border-border bg-background px-2 py-1 text-sm"
              value={datasetRef}
              onChange={(e) => setDatasetRef(e.target.value)}
              placeholder="datasets/support-smoke-v1"
              disabled={submitting}
              data-testid="new-suite-dataset-ref"
            />
          </div>
          <fieldset className="flex flex-col gap-2">
            <legend className="text-xs text-muted-foreground">Metrics</legend>
            <div className="grid grid-cols-2 gap-2">
              {METRIC_OPTIONS.map((metric) => {
                const checked = metrics.includes(metric.value);
                return (
                  <label
                    key={metric.value}
                    className="flex items-center gap-2 rounded border px-2 py-1 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleMetric(metric.value)}
                      disabled={submitting}
                      data-testid={`new-suite-metric-${metric.value}`}
                    />
                    {metric.label}
                  </label>
                );
              })}
            </div>
          </fieldset>
          {error ? (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          ) : null}
          <div className="flex gap-2">
            <Button
              type="submit"
              disabled={submitting}
              data-testid="new-suite-submit"
            >
              {submitting ? "Creating…" : "Create"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
