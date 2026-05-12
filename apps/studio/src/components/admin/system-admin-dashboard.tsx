"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Building2,
  CheckCircle2,
  Clock3,
  ShieldAlert,
  UserPlus,
  Users,
} from "lucide-react";

import { RequireAuth } from "@/components/auth/require-auth";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  approveEnterpriseSignup,
  fetchSystemAdminOverview,
  type SystemAdminOverview,
} from "@/lib/system-admin";

function MetricCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number;
  icon: typeof Building2;
}) {
  return (
    <div className="rounded-md border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">{label}</p>
        <Icon className="h-4 w-4 text-primary" aria-hidden />
      </div>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
    </div>
  );
}

export function SystemAdminDashboard() {
  return (
    <RequireAuth>
      <SystemAdminBody />
    </RequireAuth>
  );
}

function SystemAdminBody() {
  const [overview, setOverview] = useState<SystemAdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busySignup, setBusySignup] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await fetchSystemAdminOverview();
      setOverview(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load system admin.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleApprove(signupId: string) {
    setBusySignup(signupId);
    try {
      await approveEnterpriseSignup(signupId, "Approved from Studio system admin.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not approve signup.");
    } finally {
      setBusySignup(null);
    }
  }

  if (!overview && !error) {
    return (
      <main className="p-6">
        <p className="text-sm text-muted-foreground">Loading system admin...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-5 p-4 lg:p-6">
      <header className="instrument-panel rounded-md p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-primary">System admin</p>
            <h1 className="mt-2 text-3xl font-semibold">Tenant operations</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Review enterprise signup requests, provision workspaces, and
              verify onboarding state across the Loop installation.
            </p>
          </div>
          <Link href="/enterprise/admin" className={buttonVariants({ variant: "outline" })}>
            Enterprise admin
          </Link>
        </div>
        {overview?.access.mode === "dev_unrestricted" ? (
          <p className="mt-4 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning">
            Dev mode: configure LOOP_SYSTEM_ADMIN_SUBS before production.
          </p>
        ) : null}
        {error ? (
          <p
            role="alert"
            className="mt-4 rounded-md border border-destructive/35 bg-destructive/10 p-3 text-sm text-destructive"
          >
            {error}
          </p>
        ) : null}
      </header>

      {overview ? (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <MetricCard
              label="Workspaces"
              value={overview.metrics.workspaces}
              icon={Building2}
            />
            <MetricCard
              label="Members"
              value={overview.metrics.members}
              icon={Users}
            />
            <MetricCard
              label="Agents"
              value={overview.metrics.agents}
              icon={ShieldAlert}
            />
            <MetricCard
              label="Pending signups"
              value={overview.metrics.pending_signups}
              icon={Clock3}
            />
            <MetricCard
              label="Pending invites"
              value={overview.metrics.pending_invites}
              icon={UserPlus}
            />
          </section>

          <section className="rounded-md border bg-card p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="font-semibold">Enterprise signup queue</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Approval provisions a workspace owned by the system admin and
                  creates the first owner invite for the requester.
                </p>
              </div>
              <Link href="/signup" className={buttonVariants({ variant: "outline", size: "sm" })}>
                New signup
              </Link>
            </div>

            <div className="mt-4 overflow-hidden rounded-md border">
              <table className="w-full text-left text-sm" data-testid="system-signups-table">
                <thead className="bg-muted/55 text-xs text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Organization</th>
                    <th className="px-3 py-2 font-medium">Admin</th>
                    <th className="px-3 py-2 font-medium">Region</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {overview.enterprise_signups.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                        No enterprise signup requests yet.
                      </td>
                    </tr>
                  ) : (
                    overview.enterprise_signups.map((signup) => (
                      <tr key={signup.id}>
                        <td className="px-3 py-3 align-top">
                          <p className="font-medium">{signup.organization_name}</p>
                          <p className="mt-1 max-w-md text-xs leading-5 text-muted-foreground">
                            {signup.primary_use_case}
                          </p>
                          <p className="mt-1 font-mono text-xs text-muted-foreground">
                            {signup.workspace_slug}
                          </p>
                        </td>
                        <td className="px-3 py-3 align-top">
                          <p>{signup.admin_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {signup.admin_email}
                          </p>
                        </td>
                        <td className="px-3 py-3 align-top">{signup.region}</td>
                        <td className="px-3 py-3 align-top">
                          <span className="inline-flex items-center gap-1 rounded-full border bg-background px-2 py-1 text-xs">
                            {signup.status === "approved" ? (
                              <CheckCircle2 className="h-3 w-3 text-primary" />
                            ) : (
                              <Clock3 className="h-3 w-3 text-warning" />
                            )}
                            {signup.status.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-3 py-3 align-top">
                          {signup.status === "pending_review" ? (
                            <Button
                              size="sm"
                              onClick={() => handleApprove(signup.id)}
                              disabled={busySignup !== null}
                            >
                              {busySignup === signup.id ? "Approving..." : "Approve"}
                            </Button>
                          ) : signup.approved_workspace_id ? (
                            <Link
                              href={`/enterprise/admin?ws=${encodeURIComponent(signup.workspace_slug)}`}
                              className={buttonVariants({ variant: "outline", size: "sm" })}
                            >
                              Open workspace
                            </Link>
                          ) : null}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-md border bg-card p-4">
            <h2 className="font-semibold">Recent invites</h2>
            <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {overview.recent_invites.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No workspace invites have been created yet.
                </p>
              ) : (
                overview.recent_invites.map((invite) => (
                  <div key={invite.id} className="rounded-md border bg-background/72 p-3">
                    <p className="font-medium">{invite.email}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {invite.role} / {invite.status} / {invite.workspace_id}
                    </p>
                  </div>
                ))
              )}
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}
