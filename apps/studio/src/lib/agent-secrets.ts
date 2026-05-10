/**
 * Secrets surfaced in the studio "Secrets" tab. Values are NEVER read
 * client-side — only references (id + name + ref + rotated_at). The
 * cp-api list endpoint already enforces this contract; the studio
 * mirrors it by typing ``value`` away entirely.
 *
 * Fixture secret references are available only when a caller explicitly opts
 * into fixture mode. The default path never invents KMS refs or pretends a
 * secret was added/rotated without the control plane.
 */

export interface AgentSecret {
  id: string;
  agent_id: string;
  name: string;
  /** Pointer into the workspace KMS, e.g. ``kms://prod/openai-key``. */
  ref: string;
  created_at: string;
  rotated_at: string | null;
}

export interface ListAgentSecretsOptions {
  fetcher?: typeof fetch;
  baseUrl?: string;
  token?: string;
  allowFixture?: boolean;
}

export interface ListAgentSecretsResponse {
  items: AgentSecret[];
  degraded_reason?: string | undefined;
}

export async function listAgentSecrets(
  agentId: string,
  opts: ListAgentSecretsOptions = {},
): Promise<ListAgentSecretsResponse> {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) {
    if (opts.allowFixture === true) return { items: fixtureSecrets(agentId) };
    return {
      items: [],
      degraded_reason:
        "Secrets require the control-plane vault endpoint. No local KMS references are shown.",
    };
  }
  const fetcher = opts.fetcher ?? fetch;
  const response = await fetcher(
    `${base}/agents/${encodeURIComponent(agentId)}/secrets`,
    { method: "GET", headers: secretHeaders(opts), cache: "no-store" },
  );
  if (response.status === 404) return { items: [] };
  if (!response.ok) {
    throw new Error(`cp-api GET /agents/${agentId}/secrets -> ${response.status}`);
  }
  return (await response.json()) as ListAgentSecretsResponse;
}

export interface AddAgentSecretInput {
  agentId: string;
  name: string;
  ref: string;
}

export interface AddAgentSecretOptions {
  fetcher?: typeof fetch;
  baseUrl?: string;
  token?: string;
  allowFixture?: boolean;
}

const SECRET_NAME_RE = /^[A-Z][A-Z0-9_]*$/;

export async function addAgentSecret(
  input: AddAgentSecretInput,
  opts: AddAgentSecretOptions = {},
): Promise<AgentSecret> {
  if (!SECRET_NAME_RE.test(input.name)) {
    throw new Error("Secret name must be SCREAMING_SNAKE_CASE.");
  }
  if (!input.ref.trim()) {
    throw new Error("Secret ref is required.");
  }
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) {
    if (opts.allowFixture !== true) {
      throw new Error("LOOP_CP_API_BASE_URL is required to add a secret.");
    }
    return {
      id: `sec_${Math.random().toString(36).slice(2, 10)}`,
      agent_id: input.agentId,
      name: input.name,
      ref: input.ref,
      created_at: new Date().toISOString(),
      rotated_at: null,
    };
  }
  const f = opts.fetcher ?? fetch;
  const response = await f(
    `${base}/agents/${encodeURIComponent(input.agentId)}/secrets`,
    {
      method: "POST",
      headers: secretHeaders(opts),
      body: JSON.stringify({ name: input.name, ref: input.ref }),
    },
  );
  if (!response.ok) {
    throw new Error(
      `cp-api POST /agents/${input.agentId}/secrets -> ${response.status}`,
    );
  }
  return (await response.json()) as AgentSecret;
}

export interface RotateAgentSecretInput {
  secretId: string;
}

export interface RotateAgentSecretOptions {
  fetcher?: typeof fetch;
  baseUrl?: string;
  token?: string;
  allowFixture?: boolean;
}

export async function rotateAgentSecret(
  input: RotateAgentSecretInput,
  opts: RotateAgentSecretOptions = {},
): Promise<{ secretId: string; rotated_at: string }> {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) {
    if (opts.allowFixture !== true) {
      throw new Error("LOOP_CP_API_BASE_URL is required to rotate a secret.");
    }
    return { secretId: input.secretId, rotated_at: new Date().toISOString() };
  }
  const f = opts.fetcher ?? fetch;
  const response = await f(
    `${base}/secrets/${encodeURIComponent(input.secretId)}/rotate`,
    { method: "POST", headers: secretHeaders(opts), body: "{}" },
  );
  if (!response.ok) {
    throw new Error(
      `cp-api POST /secrets/${input.secretId}/rotate -> ${response.status}`,
    );
  }
  const body = (await response.json()) as Partial<{
    secretId: string;
    rotated_at: string;
  }>;
  return {
    secretId: body.secretId ?? input.secretId,
    rotated_at: body.rotated_at ?? new Date().toISOString(),
  };
}

function cpApiBaseUrl(override?: string): string | null {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function secretHeaders(
  opts: Pick<ListAgentSecretsOptions, "token">,
): Record<string, string> {
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  return headers;
}

function fixtureSecrets(agentId: string): AgentSecret[] {
  const now = "2026-04-30T10:00:00Z";
  const last = "2026-04-15T09:30:00Z";
  return [
    {
      id: `sec_${agentId}_1`,
      agent_id: agentId,
      name: "OPENAI_API_KEY",
      ref: "kms://prod/openai-key",
      created_at: "2026-03-01T08:00:00Z",
      rotated_at: last,
    },
    {
      id: `sec_${agentId}_2`,
      agent_id: agentId,
      name: "STRIPE_SECRET",
      ref: "kms://prod/stripe-key",
      created_at: "2026-03-12T08:00:00Z",
      rotated_at: null,
    },
    {
      id: `sec_${agentId}_3`,
      agent_id: agentId,
      name: "TWILIO_TOKEN",
      ref: "kms://prod/twilio-token",
      created_at: "2026-04-01T08:00:00Z",
      rotated_at: now,
    },
  ];
}
