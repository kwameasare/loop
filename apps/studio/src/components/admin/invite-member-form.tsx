"use client";

import { useState, type FormEvent } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { WORKSPACE_ROLES, type WorkspaceRole } from "@/lib/members";
import type { CreateWorkspaceInviteInput } from "@/lib/workspace-invites";

export function InviteMemberForm({
  onInvite,
}: {
  onInvite: (input: CreateWorkspaceInviteInput) => Promise<void>;
}) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("member");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<
    | { kind: "idle" }
    | { kind: "submitting" }
    | { kind: "error"; message: string }
    | { kind: "success" }
  >({ kind: "idle" });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus({ kind: "submitting" });
    try {
      await onInvite({
        email,
        role,
        ...(fullName.trim() ? { full_name: fullName.trim() } : {}),
        ...(note.trim() ? { note: note.trim() } : {}),
      });
      setEmail("");
      setFullName("");
      setRole("member");
      setNote("");
      setStatus({ kind: "success" });
    } catch (error) {
      setStatus({
        kind: "error",
        message: error instanceof Error ? error.message : "Could not invite member.",
      });
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="instrument-panel rounded-2xl p-4"
      data-testid="invite-member-form"
    >
      <div className="flex items-start gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-md bg-primary/15 text-primary">
          <Send className="h-4 w-4" aria-hidden />
        </span>
        <div>
          <h2 className="font-semibold">Invite teammate</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Email-based invites keep onboarding readable. Direct UUID membership
            remains available through the API.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="space-y-1 text-sm">
          <span className="font-medium">Email</span>
          <input
            required
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-md border bg-background px-3 py-2"
            placeholder="builder@company.com"
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Full name</span>
          <input
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            className="w-full rounded-md border bg-background px-3 py-2"
            placeholder="Priya Shah"
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Role</span>
          <select
            value={role}
            onChange={(event) => setRole(event.target.value as WorkspaceRole)}
            className="w-full rounded-md border bg-background px-3 py-2"
          >
            {WORKSPACE_ROLES.map((workspaceRole) => (
              <option key={workspaceRole} value={workspaceRole}>
                {workspaceRole}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Note</span>
          <input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className="w-full rounded-md border bg-background px-3 py-2"
            placeholder="Owns refund bot migration"
          />
        </label>
      </div>

      {status.kind === "error" ? (
        <p
          role="alert"
          className="mt-3 rounded-md border border-destructive/35 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {status.message}
        </p>
      ) : null}
      {status.kind === "success" ? (
        <p
          role="status"
          className="mt-3 rounded-md border border-primary/35 bg-primary/10 p-3 text-sm text-primary"
        >
          Invite recorded and audited.
        </p>
      ) : null}

      <Button
        type="submit"
        disabled={status.kind === "submitting"}
        className="mt-4 w-full sm:w-auto"
      >
        {status.kind === "submitting" ? "Inviting..." : "Invite teammate"}
      </Button>
    </form>
  );
}
