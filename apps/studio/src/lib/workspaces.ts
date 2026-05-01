/**
 * S154: Workspace fixtures + ``listWorkspaces`` stub.
 *
 * Mirrors ``GET /v1/workspaces`` from openapi.yaml. Like the agents
 * fixture in ``cp-api.ts``, this returns a hard-coded list while the
 * live cp-api endpoint stabilises (epic E5/S023). Studio code calls
 * ``listWorkspaces()`` so the migration to the live client is a
 * one-line swap.
 */

export type Workspace = {
  id: string;
  name: string;
  slug: string;
  role: "owner" | "admin" | "member";
};

export type ListWorkspacesResponse = {
  workspaces: Workspace[];
};

const FIXTURE: Workspace[] = [
  {
    id: "ws_acme",
    name: "Acme",
    slug: "acme",
    role: "owner",
  },
  {
    id: "ws_globex",
    name: "Globex",
    slug: "globex",
    role: "admin",
  },
];

export async function listWorkspaces(): Promise<ListWorkspacesResponse> {
  return Promise.resolve({ workspaces: [...FIXTURE] });
}
