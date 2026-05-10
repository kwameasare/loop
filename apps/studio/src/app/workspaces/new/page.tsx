"use client";

/**
 * S594: ``/workspaces/new`` page.
 *
 * Hosts the ``WorkspaceCreateForm`` and wires its submit handler to
 * the cp-api workspace-create endpoint. Workspace creation is a
 * persisted enterprise object mutation; Studio must not post to a
 * same-origin placeholder or fabricate a tenant.
 */

import { useRouter } from "next/navigation";

import { WorkspaceCreateForm } from "@/components/workspaces/workspace-create-form";
import type { WorkspaceCreate } from "@/lib/openapi-types";
import { createWorkspace as createWorkspaceOnControlPlane } from "@/lib/workspaces";

export default function NewWorkspacePage() {
  const router = useRouter();

  async function createWorkspace(payload: WorkspaceCreate): Promise<void> {
    const created = await createWorkspaceOnControlPlane(payload);
    if (created.slug) {
      router.push(`/?ws=${encodeURIComponent(created.slug)}`);
    } else {
      router.push("/");
    }
  }

  return (
    <main className="flex flex-col gap-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold">Create workspace</h1>
        <p className="text-sm text-muted-foreground">
          A workspace pins your data, telemetry, and inference to one region.
        </p>
      </header>
      <WorkspaceCreateForm onSubmit={createWorkspace} />
    </main>
  );
}
