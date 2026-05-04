"use client";

/**
 * P0.3: ``/workspaces/{id}/members`` — member management.
 *
 * Client component because the table mutates state in-place and
 * cp-api authorisation depends on a session token attached at the
 * fetch layer (the SPA's bearer token, not a server-side cookie).
 * The page reads the active user's sub via ``useUser`` and forwards
 * it to the screen so the table can flag "you" and disable
 * self-removal.
 */

import { use } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { useUser } from "@/lib/use-user";
import { MembersScreen } from "./members-screen";

interface PageProps {
  params: Promise<{ workspace_id: string }> | { workspace_id: string };
}

export default function MembersPage({ params }: PageProps) {
  // Next 14 still supports a sync `params` for client components, but
  // wrapping the read in `use` keeps us forward-compatible with the
  // promise-shaped params slated for Next 15.
  const resolved =
    "then" in (params as object) ? use(params as Promise<{ workspace_id: string }>) : (params as { workspace_id: string });
  return (
    <RequireAuth>
      <main className="container mx-auto flex max-w-3xl flex-col gap-6 p-6">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight">Members</h1>
          <p className="text-muted-foreground text-sm">
            Manage who can access this workspace. Owner-only mutations are
            enforced by cp-api; demoting the last owner is rejected.
          </p>
        </header>
        <MembersScreenAuthed workspaceId={resolved.workspace_id} />
      </main>
    </RequireAuth>
  );
}

function MembersScreenAuthed({ workspaceId }: { workspaceId: string }) {
  const { user } = useUser();
  if (!user) {
    return (
      <p className="text-sm text-muted-foreground">
        Sign in to view workspace members.
      </p>
    );
  }
  return <MembersScreen workspaceId={workspaceId} currentUserSub={user.sub} />;
}
