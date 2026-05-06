"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { EvidenceCallout } from "@/components/target/evidence-callout";
import { PermissionBoundary } from "@/components/target/permission-boundary";
import { StatePanel } from "@/components/target/state-panel";
import {
  ROLLBACK_TARGET,
  type RollbackTarget,
} from "@/lib/deploy-flight";

export interface RollbackPanelProps {
  target?: RollbackTarget;
  /** Caller permission. When false renders permission boundary. */
  canRollback?: boolean;
  onConfirm?: (target: RollbackTarget) => void;
  onRequestAccess?: () => void;
}

export function RollbackPanel({
  target = ROLLBACK_TARGET,
  canRollback = true,
  onConfirm,
  onRequestAccess,
}: RollbackPanelProps) {
  const [confirming, setConfirming] = useState(false);
  const [done, setDone] = useState(false);
  const handleConfirm = () => {
    setDone(true);
    onConfirm?.(target);
  };
  return (
    <PermissionBoundary
      allowed={canRollback}
      reason="Rollback is gated by deploy:rollback. SRE on-call can grant the role."
      onRequestAccess={onRequestAccess}
    >
      <section className="space-y-3" data-testid="rollback-panel">
        <header className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Rollback</h2>
          {!done ? (
            !confirming ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setConfirming(true)}
                data-testid="rollback-arm"
              >
                Prepare rollback
              </Button>
            ) : (
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirming(false)}
                  data-testid="rollback-cancel"
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={handleConfirm}
                  data-testid="rollback-confirm"
                >
                  Confirm rollback to {target.versionId}
                </Button>
              </div>
            )
          ) : (
            <span
              className="rounded-md border border-info/40 bg-info/10 px-2 py-0.5 text-xs text-info"
              data-testid="rollback-recorded"
            >
              audited · {target.versionId}
            </span>
          )}
        </header>

        <article
          className="rounded-md border bg-card p-3"
          data-testid="rollback-target"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Previous known-good
          </p>
          <p className="mt-1 text-sm font-medium">{target.label}</p>
          <p className="text-xs text-muted-foreground">{target.summary}</p>
          <p className="mt-2 font-mono text-[11px] text-muted-foreground">
            shipped {target.shippedAt} · {target.evidenceRef}
          </p>
        </article>

        {done ? (
          <EvidenceCallout
            title="Rollback complete and audited"
            tone="success"
            source="canonical §19.5"
          >
            The rollback action itself becomes a versioned event. Evidence has
            been written with the actor, timestamp, target snapshot, and the
            production state immediately before the rollback was issued.
          </EvidenceCallout>
        ) : confirming ? (
          <StatePanel state="degraded" title="About to rewind production">
            Confirming will route 100% traffic back to {target.versionId} within
            38 seconds. Make sure the on-call channel is informed; the rollback
            will be recorded and notified to every approver of the current
            deploy.
          </StatePanel>
        ) : (
          <EvidenceCallout
            title="Rollback target armed"
            tone="info"
            source="canonical §19.5"
          >
            Rollback is a production action but designed for emergencies — the
            previous known-good version is always one click away, with impact
            shown before confirmation, and the rollback itself becomes a
            versioned event.
          </EvidenceCallout>
        )}
      </section>
    </PermissionBoundary>
  );
}
