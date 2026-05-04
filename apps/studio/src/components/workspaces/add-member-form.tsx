"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  type AddMemberInput,
  type WorkspaceRole,
  WORKSPACE_ROLES,
} from "@/lib/members";

export interface AddMemberFormProps {
  /** Resolves with the freshly added Membership; used to refresh the list. */
  onAdd: (input: AddMemberInput) => Promise<void>;
}

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function AddMemberForm({ onAdd }: AddMemberFormProps) {
  const [userSub, setUserSub] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("member");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    if (!UUID_RE.test(userSub.trim())) {
      // cp-api maps every Auth0 sub to a UUID via uuid5 in
      // /v1/auth/exchange, so the studio always has a UUID-shaped
      // user_sub to work with.
      setError("user_sub must be a UUID");
      return;
    }
    setSubmitting(true);
    try {
      await onAdd({ user_sub: userSub.trim(), role });
      setUserSub("");
      setRole("member");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add member");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3 rounded-lg border p-4"
      data-testid="add-member-form"
    >
      <h3 className="text-sm font-medium">Add member</h3>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-muted-foreground" htmlFor="add-member-sub">
          User sub (UUID)
        </label>
        <input
          id="add-member-sub"
          className="rounded border border-border bg-background px-2 py-1 text-sm font-mono"
          value={userSub}
          onChange={(e) => setUserSub(e.target.value)}
          placeholder="00000000-0000-0000-0000-000000000000"
          disabled={submitting}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-muted-foreground" htmlFor="add-member-role">
          Role
        </label>
        <select
          id="add-member-role"
          className="rounded border border-border bg-background px-2 py-1 text-sm"
          value={role}
          onChange={(e) => setRole(e.target.value as WorkspaceRole)}
          disabled={submitting}
        >
          {WORKSPACE_ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>
      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
      <Button type="submit" disabled={submitting} data-testid="add-member-submit">
        {submitting ? "Adding…" : "Add"}
      </Button>
    </form>
  );
}
