"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Building2,
  FileSearch,
  KeyRound,
  ShieldCheck,
  Users,
} from "lucide-react";

import { InviteMemberForm } from "@/components/admin/invite-member-form";
import { RequireAuth } from "@/components/auth/require-auth";
import { WorkspaceRequiredState } from "@/components/section-states";
import { buttonVariants } from "@/components/ui/button";
import { MembersTable } from "@/components/workspaces/members-table";
import {
  listMembers,
  type Membership,
  removeMember,
  updateMemberRole,
  type WorkspaceRole,
} from "@/lib/members";
import { useActiveWorkspace } from "@/lib/use-active-workspace";
import { useUser } from "@/lib/use-user";
import {
  createWorkspaceInvite,
  listWorkspaceInvites,
  type WorkspaceInvite,
} from "@/lib/workspace-invites";

function AdminCard({
  title,
  detail,
  href,
  icon: Icon,
}: {
  title: string;
  detail: string;
  href: string;
  icon: typeof Users;
}) {
  return (
    <Link href={href} className="instrument-panel interactive-lift rounded-md p-4">
      <Icon className="h-5 w-5 text-primary" aria-hidden />
      <p className="mt-3 font-semibold">{title}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{detail}</p>
    </Link>
  );
}

function InviteList({ invites }: { invites: WorkspaceInvite[] }) {
  if (invites.length === 0) {
    return (
      <p className="rounded-md border bg-background/72 p-4 text-sm text-muted-foreground">
        No pending invites yet.
      </p>
    );
  }
  return (
    <div className="overflow-hidden rounded-md border">
      <table className="w-full text-left text-sm" data-testid="workspace-invites-table">
        <thead className="bg-muted/55 text-xs text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-medium">Invitee</th>
            <th className="px-3 py-2 font-medium">Role</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">Expires</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {invites.map((invite) => (
            <tr key={invite.id}>
              <td className="px-3 py-2">
                <p className="font-medium">{invite.email}</p>
                <p className="text-xs text-muted-foreground">{invite.full_name}</p>
              </td>
              <td className="px-3 py-2">{invite.role}</td>
              <td className="px-3 py-2">{invite.status}</td>
              <td className="px-3 py-2">
                {new Date(invite.expires_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EnterpriseAdminDashboard() {
  return (
    <RequireAuth>
      <EnterpriseAdminBody />
    </RequireAuth>
  );
}

function EnterpriseAdminBody() {
  const { active, isLoading, degradedReason } = useActiveWorkspace();
  const { user } = useUser();
  const [members, setMembers] = useState<Membership[]>([]);
  const [invites, setInvites] = useState<WorkspaceInvite[]>([]);
  const [error, setError] = useState<string | null>(null);

  const workspaceId = active?.id;
  const currentUserSub = user?.sub ?? "";

  const refresh = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const [membersResult, invitesResult] = await Promise.all([
        listMembers(workspaceId),
        listWorkspaceInvites(workspaceId),
      ]);
      setMembers(membersResult.items);
      setInvites(invitesResult.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load enterprise admin.");
    }
  }, [workspaceId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const ownerCount = useMemo(
    () => members.filter((member) => member.role === "owner").length,
    [members],
  );

  if (isLoading) {
    return (
      <main className="p-6">
        <p className="text-sm text-muted-foreground">Loading enterprise admin...</p>
      </main>
    );
  }
  if (!workspaceId || !active) {
    return <WorkspaceRequiredState title="Enterprise admin" />;
  }

  async function handleInvite(input: Parameters<typeof createWorkspaceInvite>[1]) {
    if (!workspaceId) return;
    await createWorkspaceInvite(workspaceId, input);
    await refresh();
  }

  async function handleChangeRole(userSub: string, role: WorkspaceRole) {
    if (!workspaceId) return;
    await updateMemberRole(workspaceId, userSub, role);
    await refresh();
  }

  async function handleRemove(userSub: string) {
    if (!workspaceId) return;
    await removeMember(workspaceId, userSub);
    await refresh();
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-5 p-4 lg:p-6">
      <header className="instrument-panel rounded-md p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-primary">Enterprise admin</p>
            <h1 className="mt-2 text-3xl font-semibold">{active.name}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Onboard people, connect identity, review roles, and keep evidence
              attached to the workspace. This page reads and mutates cp-api
              workspace state.
            </p>
          </div>
          <div className="grid gap-2 text-sm sm:grid-cols-3 lg:min-w-[26rem]">
            <div className="rounded-md border bg-background/72 p-3">
              <p className="text-muted-foreground">Members</p>
              <p className="mt-1 text-2xl font-semibold">{members.length}</p>
            </div>
            <div className="rounded-md border bg-background/72 p-3">
              <p className="text-muted-foreground">Owners</p>
              <p className="mt-1 text-2xl font-semibold">{ownerCount}</p>
            </div>
            <div className="rounded-md border bg-background/72 p-3">
              <p className="text-muted-foreground">Invites</p>
              <p className="mt-1 text-2xl font-semibold">{invites.length}</p>
            </div>
          </div>
        </div>
        {degradedReason ? (
          <p className="mt-4 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning">
            {degradedReason}
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

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <AdminCard
          title="SSO"
          detail="Connect SAML and verify the identity-provider round trip."
          href="/enterprise"
          icon={KeyRound}
        />
        <AdminCard
          title="Governance"
          detail="Policies, approvers, residency, and workspace evidence."
          href="/enterprise/govern"
          icon={ShieldCheck}
        />
        <AdminCard
          title="Audit"
          detail="Search append-only records for membership and admin changes."
          href="/enterprise/audit"
          icon={FileSearch}
        />
        <AdminCard
          title="System admin"
          detail="Review enterprise signups and provision new tenants."
          href="/system/admin"
          icon={Building2}
        />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="grid gap-5">
          <InviteMemberForm onInvite={handleInvite} />
          <section className="rounded-md border bg-card p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold">Current members</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Role changes and removals round-trip through cp-api.
                </p>
              </div>
              <Link
                href={`/workspaces/${encodeURIComponent(workspaceId)}/members`}
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                Detailed table
              </Link>
            </div>
            <MembersTable
              members={members}
              currentUserSub={currentUserSub}
              onChangeRole={handleChangeRole}
              onRemove={handleRemove}
            />
          </section>
        </div>

        <section className="rounded-md border bg-card p-4">
          <h2 className="font-semibold">Pending invites</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Invitations are audit-backed records. Email delivery can attach to
            this queue without changing the admin surface.
          </p>
          <div className="mt-4">
            <InviteList invites={invites} />
          </div>
        </section>
      </section>
    </main>
  );
}
