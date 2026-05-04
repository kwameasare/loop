"use client";

import Link from "next/link";

import { useActiveWorkspace } from "@/lib/use-active-workspace";

/**
 * Quick access to member-management for the active workspace.
 * Sits beside the workspace switcher in the studio top navigation.
 */
export function WorkspaceMembersLink() {
  const { active, isLoading } = useActiveWorkspace();

  if (isLoading || !active) {
    return null;
  }

  return (
    <Link
      href={`/workspaces/${active.id}/members`}
      className="text-muted-foreground hover:text-foreground hover:bg-muted rounded-md px-3 py-1.5 text-sm transition-colors"
      data-testid="workspace-members-link"
    >
      Members
    </Link>
  );
}
