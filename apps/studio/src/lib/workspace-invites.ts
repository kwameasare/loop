import { readSessionToken } from "@/lib/cp-auth-exchange";
import { createAuthedCpApiFetch } from "@/lib/cp-api-fetch";
import type { WorkspaceRole } from "@/lib/members";

export type WorkspaceInvite = {
  id: string;
  workspace_id: string;
  email: string;
  role: WorkspaceRole;
  full_name?: string | null;
  note?: string | null;
  status: "pending" | "accepted" | "revoked" | "expired";
  created_at: string;
  expires_at: string;
  created_by: string;
  invite_url: string;
};

export type ListWorkspaceInvitesResponse = {
  items: WorkspaceInvite[];
};

export type CreateWorkspaceInviteInput = {
  email: string;
  role: WorkspaceRole;
  full_name?: string;
  note?: string;
};

export interface WorkspaceInviteClientOptions {
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
    throw new Error("LOOP_CP_API_BASE_URL is required for workspace invites.");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

async function cpFetch<T>(
  method: string,
  path: string,
  opts: WorkspaceInviteClientOptions,
  body?: unknown,
): Promise<T> {
  const base = cpApiBaseUrl(opts.baseUrl);
  const fetcher = createAuthedCpApiFetch({
    ...(opts.fetcher ? { fetcher: opts.fetcher } : {}),
    refreshBaseUrl: base.replace(/\/v1$/, ""),
  });
  const explicitToken = opts.token ?? process.env.LOOP_TOKEN;
  const sessionToken =
    typeof window !== "undefined" ? readSessionToken()?.access_token : null;
  if (!explicitToken && !sessionToken && typeof window !== "undefined") {
    throw new Error("Sign in before managing workspace invites.");
  }
  const headers: Record<string, string> = { accept: "application/json" };
  if (explicitToken) headers.authorization = `Bearer ${explicitToken}`;
  const init: RequestInit = { method, headers, cache: "no-store" };
  if (body !== undefined) {
    headers["content-type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const response = await fetcher(`${base}${path}`, init);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `cp-api ${method} ${path} -> ${response.status}${text ? `: ${text}` : ""}`,
    );
  }
  return (await response.json()) as T;
}

export async function listWorkspaceInvites(
  workspaceId: string,
  opts: WorkspaceInviteClientOptions = {},
): Promise<ListWorkspaceInvitesResponse> {
  return cpFetch<ListWorkspaceInvitesResponse>(
    "GET",
    `/workspaces/${encodeURIComponent(workspaceId)}/invites`,
    opts,
  );
}

export async function createWorkspaceInvite(
  workspaceId: string,
  input: CreateWorkspaceInviteInput,
  opts: WorkspaceInviteClientOptions = {},
): Promise<WorkspaceInvite> {
  return cpFetch<WorkspaceInvite>(
    "POST",
    `/workspaces/${encodeURIComponent(workspaceId)}/invites`,
    opts,
    input,
  );
}
