"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { GovernOverview } from "@/components/enterprise/govern-overview";
import { WorkspaceRequiredState } from "@/components/section-states";
import {
  fetchComplianceReview,
  type ComplianceReviewModel,
} from "@/lib/enterprise-govern";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function EnterpriseGovernPage(): JSX.Element {
  return (
    <RequireAuth>
      <EnterpriseGovernPageBody />
    </RequireAuth>
  );
}

function EnterpriseGovernPageBody(): JSX.Element {
  const { active, isLoading } = useActiveWorkspace();
  const [model, setModel] = useState<ComplianceReviewModel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    void fetchComplianceReview(active.id)
      .then((next) => {
        if (!cancelled) setModel(next);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not load compliance review.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (isLoading) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading compliance review…
        </p>
      </main>
    );
  }
  if (!active) return <WorkspaceRequiredState title="Compliance Review" />;
  if (!model && !error) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading compliance review…
        </p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      </main>
    );
  }

  return (
    <main
      data-testid="enterprise-govern-page"
      className="mx-auto max-w-6xl p-6"
    >
      <GovernOverview compliance={model!} />
    </main>
  );
}
