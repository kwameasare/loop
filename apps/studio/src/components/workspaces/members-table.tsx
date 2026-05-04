"use client";

/**
 * P0.3: Member-management table for the workspace settings page.
 *
 * Pure UI: the page wires submit handlers that round-trip
 * cp-api ``/v1/workspaces/{id}/members*`` so the table can be
 * exercised directly in vitest without an HTTP layer.
 *
 * Roles follow the cp-api enum (``owner|admin|member|viewer``). The
 * "owner" guard is enforced both in cp (cannot demote the last owner)
 * and here in the UI (no remove/role-change buttons surface for the
 * sole owner row).
 */

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  type Membership,
  type WorkspaceRole,
  WORKSPACE_ROLES,
} from "@/lib/members";

export interface MembersTableProps {
  members: Membership[];
  /**
   * Caller's own user_sub — used to flag "you" and disable
   * self-demotion / self-removal.
   */
  currentUserSub: string;
  onChangeRole: (user_sub: string, role: WorkspaceRole) => Promise<void>;
  onRemove: (user_sub: string) => Promise<void>;
}

export function MembersTable({
  members,
  currentUserSub,
  onChangeRole,
  onRemove,
}: MembersTableProps) {
  const [busySub, setBusySub] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ownerCount = useMemo(
    () => members.filter((m) => m.role === "owner").length,
    [members],
  );

  if (members.length === 0) {
    return (
      <p
        className="text-sm text-muted-foreground"
        data-testid="members-empty"
      >
        No members yet.
      </p>
    );
  }

  async function handleRole(member: Membership, next: WorkspaceRole) {
    if (next === member.role) return;
    setError(null);
    setBusySub(member.user_sub);
    try {
      await onChangeRole(member.user_sub, next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change role");
    } finally {
      setBusySub(null);
    }
  }

  async function handleRemove(member: Membership) {
    setError(null);
    setBusySub(member.user_sub);
    try {
      await onRemove(member.user_sub);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove member");
    } finally {
      setBusySub(null);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
      <table
        className="w-full border-collapse text-sm"
        data-testid="members-table"
      >
        <thead>
          <tr className="border-b text-left text-xs uppercase text-muted-foreground">
            <th className="py-2 pr-4 font-medium">User</th>
            <th className="py-2 pr-4 font-medium">Role</th>
            <th className="py-2 pr-4 font-medium" aria-label="actions" />
          </tr>
        </thead>
        <tbody>
          {members.map((m) => {
            const isSelf = m.user_sub === currentUserSub;
            const isLastOwner = m.role === "owner" && ownerCount === 1;
            const disabled = busySub !== null;
            return (
              <tr
                key={m.user_sub}
                className="border-b last:border-b-0"
                data-testid="members-row"
                data-user-sub={m.user_sub}
              >
                <td className="py-2 pr-4 font-mono text-xs">
                  {m.user_sub}
                  {isSelf ? (
                    <span className="ml-2 text-muted-foreground">(you)</span>
                  ) : null}
                </td>
                <td className="py-2 pr-4">
                  <label className="sr-only" htmlFor={`role-${m.user_sub}`}>
                    Role for {m.user_sub}
                  </label>
                  <select
                    id={`role-${m.user_sub}`}
                    className="rounded border border-border bg-background px-2 py-1"
                    value={m.role}
                    disabled={disabled || isLastOwner}
                    onChange={(e) =>
                      handleRole(m, e.target.value as WorkspaceRole)
                    }
                    data-testid="members-role-select"
                  >
                    {WORKSPACE_ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="py-2 pr-4 text-right">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={disabled || isLastOwner || isSelf}
                    onClick={() => handleRemove(m)}
                    data-testid="members-remove"
                  >
                    Remove
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
