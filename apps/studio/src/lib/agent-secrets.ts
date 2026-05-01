/**
 * Secrets surfaced in the studio "Secrets" tab. Values are NEVER read
 * client-side — only references (id + name + ref + rotated_at). The
 * cp-api list endpoint already enforces this contract; the studio
 * mirrors it by typing ``value`` away entirely.
 *
 * Add / Rotate paths are tracked under follow-up S560 — until cp-api
 * exposes ``POST /v1/agents/{id}/secrets`` and ``POST /v1/secrets/{id}/rotate``
 * we ship a workspace-local fixture + simulated network call so the
 * UX can be reviewed and tested.
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
}

export interface ListAgentSecretsResponse {
  items: AgentSecret[];
}

export async function listAgentSecrets(
  agentId: string,
  _opts: ListAgentSecretsOptions = {},
): Promise<ListAgentSecretsResponse> {
  return { items: fixtureSecrets(agentId) };
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
  const baseRaw =
    opts.baseUrl ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!baseRaw) {
    // No live cp-api bound — return an in-memory record so UX flows
    // remain demo-able. Tests pin baseUrl so they exercise fetch.
    return {
      id: `sec_${Math.random().toString(36).slice(2, 10)}`,
      agent_id: input.agentId,
      name: input.name,
      ref: input.ref,
      created_at: new Date().toISOString(),
      rotated_at: null,
    };
  }
  const trimmed = baseRaw.replace(/\/$/, "");
  const base = trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
  const f = opts.fetcher ?? fetch;
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  if (opts.token) headers.authorization = `Bearer ${opts.token}`;
  const response = await f(
    `${base}/agents/${encodeURIComponent(input.agentId)}/secrets`,
    {
      method: "POST",
      headers,
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
}

export async function rotateAgentSecret(
  input: RotateAgentSecretInput,
  opts: RotateAgentSecretOptions = {},
): Promise<{ secretId: string; rotated_at: string }> {
  const baseRaw =
    opts.baseUrl ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!baseRaw) {
    return { secretId: input.secretId, rotated_at: new Date().toISOString() };
  }
  const trimmed = baseRaw.replace(/\/$/, "");
  const base = trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
  const f = opts.fetcher ?? fetch;
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  if (opts.token) headers.authorization = `Bearer ${opts.token}`;
  const response = await f(
    `${base}/secrets/${encodeURIComponent(input.secretId)}/rotate`,
    { method: "POST", headers, body: "{}" },
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
