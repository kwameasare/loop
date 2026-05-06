import type { ObjectState } from "@/lib/design-tokens";
import { OBJECT_STATE_TREATMENTS } from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

export interface StageStep {
  id: string;
  label: string;
  state: ObjectState;
}

export interface StageStepperProps {
  steps: StageStep[];
  currentId: string;
  className?: string;
}

export function StageStepper({ steps, currentId, className }: StageStepperProps) {
  const currentIndex = Math.max(
    0,
    steps.findIndex((step) => step.id === currentId),
  );
  return (
    <ol
      className={cn("grid gap-2 sm:grid-cols-[repeat(auto-fit,minmax(7rem,1fr))]", className)}
      data-testid="stage-stepper"
    >
      {steps.map((step, index) => {
        const treatment = OBJECT_STATE_TREATMENTS[step.state];
        const reached = index <= currentIndex;
        return (
          <li
            key={step.id}
            className={cn(
              "flex min-h-16 flex-col justify-between rounded-md border p-3",
              reached ? treatment.className : "bg-card text-muted-foreground",
            )}
            aria-current={step.id === currentId ? "step" : undefined}
          >
            <span className="text-xs font-medium">{step.label}</span>
            <span className="mt-2 inline-flex items-center gap-2 text-xs">
              <span
                aria-hidden="true"
                className={cn(
                  "h-2 w-2 border border-current bg-current",
                  treatment.shape === "ring" ? "rounded-full bg-transparent" : "",
                  treatment.shape === "dot" ? "rounded-full" : "",
                  treatment.shape === "triangle" ? "rotate-45" : "",
                )}
              />
              {treatment.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
