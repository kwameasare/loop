"use client";

import { ArrowRight, Download, FileText, Sparkles } from "lucide-react";

import {
  ONBOARDING_DOORS,
  ONBOARDING_DOOR_META,
  type OnboardingDoor,
} from "@/lib/onboarding";
import { cn } from "@/lib/utils";

const ICONS: Record<OnboardingDoor, typeof Download> = {
  import: Download,
  template: FileText,
  blank: Sparkles,
};

export interface ThreeDoorsProps {
  className?: string;
  onChoose?: (door: OnboardingDoor) => void;
}

export function ThreeDoors({ className, onChoose }: ThreeDoorsProps) {
  return (
    <section
      aria-label="Choose how to start"
      data-testid="three-doors"
      className={cn("flex flex-col gap-3", className)}
    >
      <header>
        <h1 className="text-xl font-semibold">Welcome to Studio</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Pick a door. Within 60 seconds you will see a streaming response from
          your first agent.
        </p>
      </header>
      <ul
        className="grid grid-cols-1 gap-3 md:grid-cols-3"
        data-testid="three-doors-list"
      >
        {ONBOARDING_DOORS.map((id) => {
          const meta = ONBOARDING_DOOR_META[id];
          const Icon = ICONS[id];
          return (
            <li key={id}>
              <button
                type="button"
                onClick={() => onChoose?.(id)}
                data-testid={`door-${id}`}
                className="group flex h-full w-full flex-col items-start gap-3 rounded-md border border-border bg-card p-5 text-left transition-colors duration-swift ease-standard hover:border-focus focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              >
                <div className="flex items-center gap-2 text-foreground">
                  <Icon aria-hidden="true" className="h-4 w-4" />
                  <span className="font-medium">{meta.title}</span>
                </div>
                <p className="flex-1 text-sm text-muted-foreground">
                  {meta.summary}
                </p>
                <div className="flex w-full items-center justify-between text-xs text-muted-foreground">
                  <span>~{Math.round(meta.estimatedSeconds / 60)} min</span>
                  <span className="flex items-center gap-1 text-foreground">
                    {meta.cta}
                    <ArrowRight aria-hidden="true" className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
