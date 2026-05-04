"use client";

/**
 * P0.3: client-side member management screen.
 *
 * Renders the table + add form and round-trips
 * ``/v1/workspaces/{id}/members*`` for every mutation. Re-fetches
 * the membership list after every successful mutation so the UI is
 * always consistent with cp-api state (cp emits an audit event on
 * each mutation; we don't want to drift on optimistic updates).
 */

import { useCallback, useEffect, useState } from "react";

import { AddMemberForm } from "@/components/workspaces/add-member-form";
import { MembersTable } from "@/components/workspaces/members-table";
import {
  addMember,
  listMembers,
  type Membership,
  removeMember,
  updateMemberRole,
  type WorkspaceRole,
} from "@/lib/members";

export interface MembersScreenProps {
  workspaceId: string;
  currentUserSub: string;
}

export function MembersScreen({
  workspaceId,
  currentUserSub,
}: MembersScreenProps) {
  const [members, setMembers] = useState<Membership[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await listMembers(workspaceId);
      setMembers(res.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load members");
    }
  }, [workspaceId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function onAdd(input: {
    user_sub: string;
    role: WorkspaceRole;
  }): Promise<void> {
    await addMember(workspaceId, input);
    await refresh();
  }

  async function onChangeRole(
    user_sub: string,
    role: WorkspaceRole,
  ): Promise<void> {
    await updateMemberRole(workspaceId, user_sub, role);
    await refresh();
  }

  async function onRemove(user_sub: string): Promise<void> {
    await removeMember(workspaceId, user_sub);
    await refresh();
  }

  if (error && members === null) {
    return (
      <div className="rounded-lg border p-4" role="alert">
        <p className="text-sm">Could not load members: {error}</p>
      </div>
    );
  }
  if (members === null) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="members-loading">
        Loading members…
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <MembersTable
        members={members}
        currentUserSub={currentUserSub}
        onChangeRole={onChangeRole}
        onRemove={onRemove}
      />
      <AddMemberForm onAdd={onAdd} />
    </div>
  );
}
