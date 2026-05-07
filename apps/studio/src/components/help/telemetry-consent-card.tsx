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

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    void fetchTelemetryConsent(active.id).then((next) => {
      if (cancelled) return;
      setModel(next);
      setDraft({
        product_analytics: next.product_analytics ?? DEFAULT_DRAFT.product_analytics,
        diagnostics: next.diagnostics ?? DEFAULT_DRAFT.diagnostics,
        ai_improvement: next.ai_improvement ?? DEFAULT_DRAFT.ai_improvement,
        crash_reports: next.crash_reports ?? DEFAULT_DRAFT.crash_reports,
      });
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
    await saveTelemetryConsent(active.id, next);
    setSaved(true);
  }

  return (
    <section
      className="rounded-md border bg-card p-4 shadow-sm"
      data-testid="telemetry-consent-card"
      aria-label="Telemetry consent"
    >
      <div className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 h-5 w-5 text-primary" aria-hidden={true} />
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold">Telemetry consent</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Product analytics never include prompts, messages, KB chunks,
            secrets, traces, or customer payloads unless your enterprise admin
            explicitly configures that policy.
          </p>
        </div>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
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
            className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
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
      <div className="mt-3 flex flex-wrap justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() =>
            void save({
              product_analytics: false,
              diagnostics: false,
              ai_improvement: false,
              crash_reports: false,
            })
          }
        >
          Decline all
        </Button>
        <Button type="button" onClick={() => void save(draft)}>
          Save consent
        </Button>
      </div>
    </section>
  );
}
