import { readSessionToken } from "@/lib/cp-auth-exchange";
import { createAuthedCpApiFetch } from "@/lib/cp-api-fetch";
import type { EnterpriseSignupRecord } from "@/lib/enterprise-signup";
import type { WorkspaceInvite } from "@/lib/workspace-invites";

export type SystemAdminOverview = {
  access: {
    mode: "configured" | "dev_unrestricted";
    actor_sub: string;
  };
  metrics: {
    workspaces: number;
    members: number;
    agents: number;
    pending_signups: number;
    pending_invites: number;
  };
  enterprise_signups: EnterpriseSignupRecord[];
  recent_invites: WorkspaceInvite[];
  degraded_reasons: string[];
};

export type ApproveEnterpriseSignupResponse = {
  signup: EnterpriseSignupRecord;
  workspace_id: string;
  admin_invite: WorkspaceInvite | null;
};

export interface SystemAdminClientOptions {
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
    throw new Error("LOOP_CP_API_BASE_URL is required for system admin.");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

async function cpFetch<T>(
  method: string,
  path: string,
  opts: SystemAdminClientOptions,
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
    throw new Error("Sign in before opening system admin.");
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

export async function fetchSystemAdminOverview(
  opts: SystemAdminClientOptions = {},
): Promise<SystemAdminOverview> {
  return cpFetch<SystemAdminOverview>("GET", "/system/admin/overview", opts);
}

export async function approveEnterpriseSignup(
  signupId: string,
  note: string,
  opts: SystemAdminClientOptions = {},
): Promise<ApproveEnterpriseSignupResponse> {
  return cpFetch<ApproveEnterpriseSignupResponse>(
    "POST",
    `/system/admin/signups/${encodeURIComponent(signupId)}/approve`,
    opts,
    { note },
  );
}
