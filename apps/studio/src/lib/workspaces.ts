import { readSessionToken } from "@/lib/cp-auth-exchange";
import { createAuthedCpApiFetch } from "@/lib/cp-api-fetch";

export type Workspace = {
  id: string;
  name: string;
  slug: string;
  role: "owner" | "admin" | "member" | "viewer";
};

export type ListWorkspacesResponse = {
  workspaces: Workspace[];
  degraded_reason?: string | undefined;
};

export interface ListWorkspacesOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
  allowFixture?: boolean;
}

interface CpWorkspace {
  id?: string;
  name?: string;
  slug?: string;
  role?: string;
}

interface CpWorkspaceList {
  items?: CpWorkspace[];
}

const FIXTURE: Workspace[] = [
  {
    id: "local-workspace",
    name: "Local workspace",
    slug: "local",
    role: "owner",
  },
];

function cpApiBaseUrl(override?: string): string | null {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function roleFromCp(role: string | undefined): Workspace["role"] {
  if (
    role === "owner" ||
    role === "admin" ||
    role === "member" ||
    role === "viewer"
  ) {
    return role;
  }
  return "member";
}

function mapWorkspace(workspace: CpWorkspace): Workspace {
  return {
    id: workspace.id ?? "",
    name: workspace.name ?? "Untitled workspace",
    slug: workspace.slug ?? workspace.id ?? "workspace",
    role: roleFromCp(workspace.role),
  };
}

export async function listWorkspaces(
  opts: ListWorkspacesOptions = {},
): Promise<ListWorkspacesResponse> {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) {
    if (opts.allowFixture === true) {
      return Promise.resolve({ workspaces: [...FIXTURE] });
    }
    return Promise.resolve({
      workspaces: [],
      degraded_reason:
        "Workspace context requires the control-plane workspace endpoint.",
    });
  }
  const explicitToken = opts.token ?? process.env.LOOP_TOKEN;
  const hasBrowserSession =
    typeof window !== "undefined" && readSessionToken()?.access_token;
  if (
    typeof window !== "undefined" &&
    !opts.fetcher &&
    !explicitToken &&
    !hasBrowserSession
  ) {
    if (opts.allowFixture === true) {
      return Promise.resolve({ workspaces: [...FIXTURE] });
    }
    return Promise.resolve({
      workspaces: [],
      degraded_reason:
        "Sign in before workspace context can be loaded from the control plane.",
    });
  }
  const fetcher = createAuthedCpApiFetch({
    ...(opts.fetcher ? { fetcher: opts.fetcher } : {}),
    refreshBaseUrl: base.replace(/\/v1$/, ""),
  });
  const headers: Record<string, string> = { accept: "application/json" };
  if (explicitToken) headers.authorization = `Bearer ${explicitToken}`;
  const response = await fetcher(`${base}/workspaces`, {
    method: "GET",
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`cp-api GET workspaces -> ${response.status}`);
  }
  const body = (await response.json()) as CpWorkspaceList;
  return { workspaces: (body.items ?? []).map(mapWorkspace) };
}

export async function listFixtureWorkspaces(): Promise<ListWorkspacesResponse> {
  return Promise.resolve({ workspaces: [...FIXTURE] });
}
