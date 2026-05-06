import type { ReactNode } from "react";
import {
  AlertTriangle,
  Clock3,
  FilePlus2,
  Loader2,
  ShieldAlert,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import {
  getTargetStateCopy,
  type TargetStateKind,
  type TargetStateCopy,
} from "./copy";

type TargetStateTone = "info" | "neutral" | "warning" | "danger" | "blocked";

interface TargetStateAction {
  label?: string | undefined;
  onClick?: (() => void) | undefined;
  href?: string | undefined;
}

export interface TargetStateProps {
  state: TargetStateKind;
  objectName: string;
  title?: string | undefined;
  description?: string | undefined;
  stage?: string | undefined;
  evidence?: string | undefined;
  requestId?: string | undefined;
  updatedAt?: string | undefined;
  primaryAction?: TargetStateAction | undefined;
  secondaryAction?: TargetStateAction | undefined;
  children?: ReactNode | undefined;
  className?: string | undefined;
}

const STATE_META: Record<
  TargetStateKind,
  {
    tone: TargetStateTone;
    icon: typeof Loader2;
    role: "status" | "alert";
    live: "polite" | "assertive";
    skeleton?: boolean;
  }
> = {
  loading: {
    tone: "info",
    icon: Loader2,
    role: "status",
    live: "polite",
    skeleton: true,
  },
  empty: {
    tone: "neutral",
    icon: FilePlus2,
    role: "status",
    live: "polite",
  },
  error: {
    tone: "danger",
    icon: AlertTriangle,
    role: "alert",
    live: "assertive",
  },
  degraded: {
    tone: "warning",
    icon: AlertTriangle,
    role: "alert",
    live: "assertive",
  },
  stale: {
    tone: "warning",
    icon: Clock3,
    role: "status",
    live: "polite",
  },
  permissionBlocked: {
    tone: "blocked",
    icon: ShieldAlert,
    role: "alert",
    live: "assertive",
  },
};

const TONE_CLASS: Record<TargetStateTone, string> = {
  info: "border-info/40 bg-info/5",
  neutral: "border-border bg-card",
  warning: "border-warning/50 bg-warning/5",
  danger: "border-destructive/40 bg-destructive/5",
  blocked: "border-border bg-muted/50",
};

const ICON_CLASS: Record<TargetStateTone, string> = {
  info: "border-info/30 bg-info/10 text-info",
  neutral: "border-border bg-muted text-muted-foreground",
  warning: "border-warning/40 bg-warning/10 text-warning",
  danger: "border-destructive/40 bg-destructive/10 text-destructive",
  blocked: "border-border bg-background text-muted-foreground",
};

function stateCopy(props: TargetStateProps): TargetStateCopy {
  return getTargetStateCopy(props.state, {
    object: props.objectName,
    stage: props.stage ?? "Loading workspace data",
    requestId: props.requestId ?? "unknown",
    updatedAt: props.updatedAt ?? "unknown",
  });
}

function ActionButton({
  action,
  fallback,
  variant,
}: {
  action: TargetStateAction;
  fallback: string;
  variant: "outline" | "default";
}) {
  const label = action.label ?? fallback;
  if (action.href) {
    return (
      <a
        className={cn(
          "inline-flex h-9 items-center justify-center rounded-md border px-3 text-sm font-medium transition-colors duration-swift ease-standard focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
          variant === "default"
            ? "border-primary bg-primary text-primary-foreground hover:bg-primary/90"
            : "border-border bg-background hover:bg-muted",
        )}
        href={action.href}
      >
        {label}
      </a>
    );
  }

  return (
    <Button type="button" variant={variant} size="sm" onClick={action.onClick}>
      {label}
    </Button>
  );
}

function LoadingSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="grid gap-2 sm:grid-cols-[1.2fr_0.8fr]"
      data-testid="target-state-skeleton"
    >
      <span className="h-3 rounded-sm bg-muted" />
      <span className="h-3 rounded-sm bg-muted" />
      <span className="h-3 rounded-sm bg-muted sm:col-span-2" />
    </div>
  );
}

export function TargetState(props: TargetStateProps) {
  const copy = stateCopy(props);
  const meta = STATE_META[props.state];
  const Icon = meta.icon;
  const title = props.title ?? copy.title;
  const description = props.description ?? copy.description;
  const hasDetails =
    Boolean(props.evidence) ||
    Boolean(props.stage) ||
    Boolean(props.requestId) ||
    Boolean(props.updatedAt);

  return (
    <section
      aria-live={meta.live}
      className={cn(
        "rounded-md border p-4 shadow-sm",
        TONE_CLASS[meta.tone],
        props.className,
      )}
      data-state={props.state}
      data-testid="target-state"
      role={meta.role}
    >
      <div className="grid gap-4 sm:grid-cols-[auto_minmax(0,1fr)]">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-md border",
            ICON_CLASS[meta.tone],
          )}
        >
          <Icon
            aria-hidden="true"
            className={cn(
              "h-5 w-5",
              props.state === "loading"
                ? "animate-spin motion-reduce:animate-none"
                : "",
            )}
          />
        </div>
        <div className="min-w-0 space-y-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
              {copy.eyebrow}
            </p>
            <h2 className="mt-1 text-base font-semibold leading-6">{title}</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              {description}
            </p>
          </div>

          {meta.skeleton ? <LoadingSkeleton /> : null}

          {hasDetails ? (
            <dl className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
              {props.evidence ? (
                <div className="rounded-md border border-border bg-background/60 p-2">
                  <dt className="font-medium text-foreground">
                    {copy.evidenceLabel}
                  </dt>
                  <dd className="mt-1">{props.evidence}</dd>
                </div>
              ) : null}
              {props.stage ? (
                <div className="rounded-md border border-border bg-background/60 p-2">
                  <dt className="font-medium text-foreground">
                    {copy.stageLabel}
                  </dt>
                  <dd className="mt-1">{props.stage}</dd>
                </div>
              ) : null}
              {props.requestId ? (
                <div className="rounded-md border border-border bg-background/60 p-2">
                  <dt className="font-medium text-foreground">
                    {copy.requestIdLabel}
                  </dt>
                  <dd className="mt-1 break-all">{props.requestId}</dd>
                </div>
              ) : null}
              {props.updatedAt ? (
                <div className="rounded-md border border-border bg-background/60 p-2">
                  <dt className="font-medium text-foreground">
                    {copy.updatedAtLabel}
                  </dt>
                  <dd className="mt-1">{props.updatedAt}</dd>
                </div>
              ) : null}
            </dl>
          ) : null}

          {props.children ? (
            <div className="text-sm text-muted-foreground">
              {props.children}
            </div>
          ) : null}

          {props.primaryAction || props.secondaryAction ? (
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
              {props.primaryAction ? (
                <ActionButton
                  action={props.primaryAction}
                  fallback={copy.primaryAction}
                  variant="default"
                />
              ) : null}
              {props.secondaryAction ? (
                <ActionButton
                  action={props.secondaryAction}
                  fallback={copy.secondaryAction}
                  variant="outline"
                />
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
