export type EnterpriseSignupPayload = {
  organization_name: string;
  workspace_slug?: string;
  admin_name: string;
  admin_email: string;
  company_size: string;
  region: string;
  primary_use_case: string;
  channel_priorities: string[];
  compliance_needs: string[];
  sso_required: boolean;
};

export type EnterpriseSignupRecord = EnterpriseSignupPayload & {
  id: string;
  workspace_slug: string;
  status: "pending_review" | "approved" | "rejected";
  created_at: string;
  updated_at: string;
  approved_workspace_id?: string | null;
  approved_by?: string | null;
  admin_invite_id?: string | null;
};

export type EnterpriseSignupResponse = {
  signup: EnterpriseSignupRecord;
  next_step: {
    label: string;
    detail: string;
    href: string;
  };
};

export interface EnterpriseSignupClientOptions {
  fetcher?: typeof fetch;
  baseUrl?: string;
}

export function cpApiBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("NEXT_PUBLIC_LOOP_API_URL is required for enterprise signup.");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

export async function createEnterpriseSignup(
  payload: EnterpriseSignupPayload,
  opts: EnterpriseSignupClientOptions = {},
): Promise<EnterpriseSignupResponse> {
  const fetcher = opts.fetcher ?? fetch;
  const response = await fetcher(`${cpApiBaseUrl(opts.baseUrl)}/enterprise/signups`, {
    method: "POST",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    cache: "no-store",
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `cp-api POST enterprise/signups -> ${response.status}${detail ? `: ${detail}` : ""}`,
    );
  }
  return (await response.json()) as EnterpriseSignupResponse;
}
