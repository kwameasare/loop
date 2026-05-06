"use client";

import {
  AlertTriangle,
  ArrowLeftRight,
  Ban,
  CheckCircle2,
  DollarSign,
  Eye,
  Inbox,
  RotateCcw,
} from "lucide-react";

import {
  URGENT_ACTIONS,
  URGENT_ACTION_LABELS,
  type UrgentAction,
} from "@/lib/responsive";
import { cn } from "@/lib/utils";

const ICONS: Record<UrgentAction, typeof AlertTriangle> = {
  "ack-incident": AlertTriangle,
  "inspect-summary": Eye,
  "view-deploy": ArrowLeftRight,
  "approve-changeset": CheckCircle2,
  "decline-changeset": Ban,
  rollback: RotateCcw,
  "takeover-inbox": Inbox,
  "view-cost-alert": DollarSign,
};

export interface MobileActionDeckProps {
  className?: string;
  onAction?: (action: UrgentAction) => void;
}

export function MobileActionDeck({ className, onAction }: MobileActionDeckProps) {
  return (
    <section
      aria-label="Mobile urgent actions"
      data-testid="mobile-action-deck"
      className={cn("flex flex-col gap-3", className)}
    >
      <header>
        <h2 className="text-base font-semibold">Urgent actions</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Mobile reserves the screen for the eight time-sensitive operations
          (§31.3). Open Studio on a desktop to edit agents.
        </p>
      </header>
      <ul
        className="grid grid-cols-2 gap-2"
        data-testid="mobile-action-list"
      >
        {URGENT_ACTIONS.map((id) => {
          const Icon = ICONS[id];
          return (
            <li key={id}>
              <button
                type="button"
                data-testid={`mobile-action-${id}`}
                onClick={() => onAction?.(id)}
                className="flex h-full w-full flex-col items-start gap-2 rounded-md border border-border bg-card p-3 text-left transition-colors duration-swift ease-standard hover:border-focus focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              >
                <Icon aria-hidden="true" className="h-4 w-4 text-foreground" />
                <span className="text-xs font-medium">
                  {URGENT_ACTION_LABELS[id]}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
