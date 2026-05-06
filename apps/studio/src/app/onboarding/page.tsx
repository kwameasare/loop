"use client";

/**
 * UX402 — Onboarding surface.
 *
 * §33 (Onboarding) and §4.8–§4.10 of the canonical target UX standard.
 * Three doors only, working-agent templates, three-hint guided spotlight,
 * weekly recap, and a permissioned concierge that can learn from recent
 * conversations with explicit consent.
 */

import { useMemo, useState } from "react";

import {
  ConciergeConsentPanel,
  GuidedSpotlight,
  ThreeDoors,
} from "@/components/onboarding";
import { TemplateGallery } from "@/components/templates";
import {
  FIRST_QUARTER_HYGIENE,
  FIRST_WEEK_NUDGES,
  formatWeeklyRecap,
  type OnboardingDoor,
  type OnboardingTemplate,
  type WeeklyRecap,
} from "@/lib/onboarding";

const SAMPLE_RECAP: WeeklyRecap = {
  weekOf: "2026-05-04",
  promotions: 4,
  rollbacks: 2,
  evalsSaved: 12,
  kbSourcesUpdated: 3,
  costDeltaPercent: 5,
  latencyDeltaPercent: 0,
};

export default function OnboardingPage(): JSX.Element {
  const [door, setDoor] = useState<OnboardingDoor | null>(null);
  const [template, setTemplate] = useState<OnboardingTemplate | null>(null);
  const recap = useMemo(() => formatWeeklyRecap(SAMPLE_RECAP), []);

  return (
    <main
      className="mx-auto flex w-full max-w-6xl flex-col gap-8 p-6"
      aria-label="Onboarding"
    >
      <ThreeDoors onChoose={setDoor} />

      {door === "template" ? (
        <TemplateGallery onPick={setTemplate} />
      ) : null}

      {template ? (
        <section
          className="rounded-md border border-focus/40 bg-focus/5 p-4 text-sm"
          data-testid="template-selection"
        >
          You picked <strong>{template.name}</strong> — Studio will provision
          its KB, mock tools, evals, and seeded conversations into a draft
          agent.
        </section>
      ) : null}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-[2fr_3fr]">
        <GuidedSpotlight />
        <ConciergeConsentPanel reviewer="ux-thor" />
      </section>

      <section
        aria-label="First-week nudges"
        className="rounded-md border border-border bg-card p-4"
      >
        <h2 className="text-sm font-semibold">First week</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          At most one nudge per day, opt-out by category.
        </p>
        <ul className="mt-2 flex flex-wrap gap-2 text-xs">
          {FIRST_WEEK_NUDGES.map((n) => (
            <li
              key={n}
              className="rounded-sm border border-border bg-background px-2 py-1 text-muted-foreground"
            >
              {n}
            </li>
          ))}
        </ul>
      </section>

      <section
        aria-label="First-month recap"
        className="rounded-md border border-border bg-card p-4"
      >
        <h2 className="text-sm font-semibold">First month</h2>
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-sm bg-background p-3 text-xs text-muted-foreground">
          {recap}
        </pre>
      </section>

      <section
        aria-label="First-quarter hygiene"
        className="rounded-md border border-border bg-card p-4"
      >
        <h2 className="text-sm font-semibold">First quarter</h2>
        <ul className="mt-2 flex flex-wrap gap-2 text-xs">
          {FIRST_QUARTER_HYGIENE.map((n) => (
            <li
              key={n}
              className="rounded-sm border border-border bg-background px-2 py-1 text-muted-foreground"
            >
              {n}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
