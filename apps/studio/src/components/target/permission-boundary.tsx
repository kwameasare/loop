import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

import { StatePanel } from "./state-panel";

export interface PermissionBoundaryProps {
  allowed: boolean;
  reason: string;
  children: ReactNode;
  actionLabel?: string;
  onRequestAccess?: (() => void) | undefined;
}

export function PermissionBoundary({
  allowed,
  reason,
  children,
  actionLabel = "Request access",
  onRequestAccess,
}: PermissionBoundaryProps) {
  if (allowed) return <>{children}</>;
  return (
    <StatePanel
      state="permission"
      title="Permission needed"
      action={
        onRequestAccess ? (
          <Button type="button" variant="outline" size="sm" onClick={onRequestAccess}>
            {actionLabel}
          </Button>
        ) : null
      }
    >
      {reason}
    </StatePanel>
  );
}
