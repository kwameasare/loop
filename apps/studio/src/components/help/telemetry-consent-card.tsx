"use client";

import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  fetchTelemetryConsent,
  saveTelemetryConsent,
  type TelemetryConsentModel,
} from "@/lib/help-telemetry";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

type ConsentDraft = {
  product_analytics: boolean;
  diagnostics: boolean;
  ai_improvement: boolean;
  crash_reports: boolean;
};

const DEFAULT_DRAFT: ConsentDraft = {
  product_analytics: false,
  diagnostics: true,
  ai_improvement: false,
  crash_reports: true,
};

export function TelemetryConsentCard(): JSX.Element | null {
  const { active } = useActiveWorkspace();
  const [model, setModel] = useState<TelemetryConsentModel | null>(null);
  const [draft, setDraft] = useState<ConsentDraft>(DEFAULT_DRAFT);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setError(null);
    void fetchTelemetryConsent(active.id)
      .then((next) => {
        if (cancelled) return;
        setModel(next);
        setDraft({
          product_analytics:
            next.product_analytics ?? DEFAULT_DRAFT.product_analytics,
          diagnostics: next.diagnostics ?? DEFAULT_DRAFT.diagnostics,
          ai_improvement:
            next.ai_improvement ?? DEFAULT_DRAFT.ai_improvement,
          crash_reports: next.crash_reports ?? DEFAULT_DRAFT.crash_reports,
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setModel({
          workspace_id: active.id,
          user_sub: "unavailable",
          product_analytics: null,
          diagnostics: null,
          ai_improvement: null,
          crash_reports: null,
          annual_review_due: true,
        });
        setError(
          err instanceof Error
            ? err.message
            : "Could not load telemetry consent.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (!active || saved || model?.annual_review_due === false) return null;

  function toggle(key: keyof ConsentDraft) {
    setDraft((current) => ({ ...current, [key]: !current[key] }));
  }

  async function save(next: ConsentDraft) {
    if (!active) return;
    setSaving(true);
    setError(null);
    try {
      await saveTelemetryConsent(active.id, next);
      setSaved(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not save telemetry consent.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      className="instrument-panel rounded-md p-3"
      data-testid="telemetry-consent-card"
      aria-label="Telemetry consent"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 h-5 w-5 text-primary" aria-hidden={true} />
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold">Telemetry choices</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            No prompts, messages, KB, secrets, traces, or payloads by default.
          </p>
        </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={saving}
            onClick={() =>
              void save({
                product_analytics: false,
                diagnostics: false,
                ai_improvement: false,
                crash_reports: false,
              })
            }
          >
            Decline
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={saving}
            onClick={() => void save(draft)}
          >
            {saving ? "Saving" : "Save"}
          </Button>
        </div>
      </div>
      {error ? (
        <p
          className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 p-2 text-xs text-destructive"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      <div className="mt-3 grid gap-2 sm:grid-cols-4">
        {(
          [
            ["product_analytics", "Product analytics"],
            ["diagnostics", "Diagnostics"],
            ["ai_improvement", "AI improvement"],
            ["crash_reports", "Crash reports"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="switch"
            aria-checked={draft[key]}
            className="interactive-lift pressable flex items-center justify-between rounded-md border bg-card/60 px-3 py-2 text-sm"
            onClick={() => toggle(key)}
            data-testid={`telemetry-toggle-${key}`}
          >
            <span>{label}</span>
            <span className="text-xs text-muted-foreground">
              {draft[key] ? "On" : "Off"}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
