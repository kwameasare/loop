"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { GovernOverview } from "@/components/enterprise/govern-overview";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import {
  fetchComplianceReview,
  fetchEnterpriseSecurity,
  type ComplianceReviewModel,
  type EnterpriseSecurityModel,
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
  const activeWorkspaceId = active?.id;
  const [model, setModel] = useState<ComplianceReviewModel | null>(null);
  const [security, setSecurity] = useState<EnterpriseSecurityModel | null>(
    null,
  );
  const [securityError, setSecurityError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    void Promise.allSettled([
      fetchComplianceReview(activeWorkspaceId),
      fetchEnterpriseSecurity(activeWorkspaceId),
    ])
      .then(([complianceResult, securityResult]) => {
        if (cancelled) return;
        if (complianceResult.status === "fulfilled") {
          setModel(complianceResult.value);
        } else {
          const reason = complianceResult.reason;
          setError(
            reason instanceof Error
              ? reason.message
              : "Could not load compliance review.",
          );
        }
        if (securityResult.status === "fulfilled") {
          setSecurity(securityResult.value);
          setSecurityError(null);
        } else {
          const reason = securityResult.reason;
          setSecurity(null);
          setSecurityError(
            reason instanceof Error
              ? reason.message
              : "Could not load enterprise security evidence.",
          );
        }
      })
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId]);

  if (isLoading) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading compliance review…
        </p>
      </main>
    );
  }
  if (!activeWorkspaceId) {
    return <WorkspaceRequiredState title="Compliance Review" />;
  }
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
      <main className="mx-auto max-w-3xl p-6">
        <SectionDegraded
          title="Compliance Review"
          description="Compliance review could not load from the control plane."
          evidence={error}
        />
      </main>
    );
  }

  return (
    <main
      data-testid="enterprise-govern-page"
      className="mx-auto max-w-6xl p-6"
    >
      <GovernOverview
        compliance={model!}
        byokKeys={security?.byokKeys ?? []}
        residencyZones={security?.residencyZones ?? []}
        {...(securityError ?? security?.degradedReason
          ? {
              securityDegradedReason:
                securityError ?? security?.degradedReason ?? "",
            }
          : {})}
        {...(security?.evidenceRef
          ? { securityEvidenceRef: security.evidenceRef }
          : {})}
      />
    </main>
  );
}
