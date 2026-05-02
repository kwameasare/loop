"use client";

/**
 * S594: ``/workspaces/new`` page.
 *
 * Hosts the ``WorkspaceCreateForm`` and wires its submit handler to
 * the live (or stubbed) cp-api workspace-create endpoint. Once the
 * cp-api endpoint stabilises (epic E5/S023) this swaps from the local
 * stub to the generated client without a UI change.
 */

import { useRouter } from "next/navigation";

import { WorkspaceCreateForm } from "@/components/workspaces/workspace-create-form";
import type { WorkspaceCreate } from "@/lib/openapi-types";

export default function NewWorkspacePage() {
  const router = useRouter();

  async function createWorkspace(payload: WorkspaceCreate): Promise<void> {
    // POST /v1/workspaces — uses native fetch so we don't pull in a
    // client lib here. The cp-api will derive region from the body
    // and refuse subsequent updates that change it (S593).
    const res = await fetch("/v1/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Workspace creation failed (${res.status}): ${text || "unknown error"}`);
    }
    const created = (await res.json()) as { slug?: string };
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
