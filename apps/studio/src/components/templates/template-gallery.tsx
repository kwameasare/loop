"use client";

import { Database, FlaskConical, MessageSquare, Wrench } from "lucide-react";

import {
  ONBOARDING_TEMPLATES,
  type OnboardingTemplate,
} from "@/lib/onboarding";
import { cn } from "@/lib/utils";

export interface TemplateGalleryProps {
  templates?: readonly OnboardingTemplate[];
  className?: string;
  onPick?: (template: OnboardingTemplate) => void;
}

export function TemplateGallery({
  templates = ONBOARDING_TEMPLATES,
  className,
  onPick,
}: TemplateGalleryProps) {
  return (
    <section
      aria-label="Templates"
      data-testid="template-gallery"
      className={cn("flex flex-col gap-3", className)}
    >
      <header>
        <h2 className="text-base font-semibold">Working agent templates</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Each template ships with sample KB, mock tools, eval suite, seeded
          conversations, traces, and a cost estimate.
        </p>
      </header>
      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {templates.map((tpl) => (
          <li key={tpl.id}>
            <button
              type="button"
              data-testid={`template-${tpl.id}`}
              onClick={() => onPick?.(tpl)}
              className="flex h-full w-full flex-col items-start gap-3 rounded-md border border-border bg-card p-4 text-left transition-colors duration-swift ease-standard hover:border-focus focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <div className="flex w-full items-center justify-between">
                <span className="font-medium">{tpl.name}</span>
                <span className="text-xs text-muted-foreground">
                  ~${tpl.costEstimateUsdPerMonth}/mo
                </span>
              </div>
              <p className="text-xs text-muted-foreground">{tpl.blurb}</p>
              <dl className="grid w-full grid-cols-2 gap-2 text-xs">
                <Stat icon={Database} label="KB" value={tpl.kbSources} />
                <Stat icon={Wrench} label="Tools" value={tpl.mockTools} />
                <Stat icon={FlaskConical} label="Evals" value={tpl.evalCases} />
                <Stat
                  icon={MessageSquare}
                  label="Convos"
                  value={tpl.seededConversations}
                />
              </dl>
              <ul className="flex flex-wrap gap-1">
                {tpl.channels.map((ch) => (
                  <li
                    key={ch}
                    className="rounded-sm border border-border bg-background px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground"
                  >
                    {ch}
                  </li>
                ))}
              </ul>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

interface StatProps {
  icon: typeof Database;
  label: string;
  value: number;
}

function Stat({ icon: Icon, label, value }: StatProps) {
  return (
    <div className="flex items-center gap-1.5 text-muted-foreground">
      <Icon aria-hidden="true" className="h-3 w-3" />
      <span>
        <span className="font-medium text-foreground">{value}</span> {label}
      </span>
    </div>
  );
}
