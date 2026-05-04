/**
 * P0.3: cp-api client for ``/v1/workspaces/{id}/members*``.
 *
 * The backend serialises the ``Membership`` row directly
 * (``user_sub`` + ``role``); the openapi spec's ``WorkspaceMember``
 * shape with ``email`` / ``full_name`` is aspirational and not yet
 * what cp-api hands back, so we model what's actually returned. When
 * the directory join lands we'll widen this type without changing the
 * call sites.
 */

export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

export const WORKSPACE_ROLES: ReadonlyArray<WorkspaceRole> = [
  "owner",
  "admin",
  "member",
  "viewer",
];

export interface Membership {
  workspace_id: string;
  user_sub: string;
  role: WorkspaceRole;
}

export interface ListMembersResponse {
  items: Membership[];
}

export interface MembersClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function cpApiBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("LOOP_CP_API_BASE_URL is required for member calls");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

async function cpFetch<T>(
  method: string,
  path: string,
  opts: MembersClientOptions,
  body?: unknown,
): Promise<T> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const init: RequestInit = { method, headers, cache: "no-store" };
  if (body !== undefined) {
    headers["content-type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const url = `${cpApiBaseUrl(opts.baseUrl)}${path}`;
  const res = await fetcher(url, init);
  if (!res.ok) {
    throw new Error(`cp-api ${method} ${path} -> ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function listMembers(
  workspace_id: string,
  opts: MembersClientOptions = {},
): Promise<ListMembersResponse> {
  return cpFetch<ListMembersResponse>(
    "GET",
    `/workspaces/${encodeURIComponent(workspace_id)}/members`,
    opts,
  );
}

export interface AddMemberInput {
  user_sub: string;
  role: WorkspaceRole;
}

export async function addMember(
  workspace_id: string,
  input: AddMemberInput,
  opts: MembersClientOptions = {},
): Promise<Membership> {
  return cpFetch<Membership>(
    "POST",
    `/workspaces/${encodeURIComponent(workspace_id)}/members`,
    opts,
    input,
  );
}

export async function removeMember(
  workspace_id: string,
  user_sub: string,
  opts: MembersClientOptions = {},
): Promise<void> {
  await cpFetch<void>(
    "DELETE",
    `/workspaces/${encodeURIComponent(workspace_id)}/members/${encodeURIComponent(user_sub)}`,
    opts,
  );
}

export async function updateMemberRole(
  workspace_id: string,
  user_sub: string,
  role: WorkspaceRole,
  opts: MembersClientOptions = {},
): Promise<Membership> {
  return cpFetch<Membership>(
    "PATCH",
    `/workspaces/${encodeURIComponent(workspace_id)}/members/${encodeURIComponent(user_sub)}`,
    opts,
    { role },
  );
}
