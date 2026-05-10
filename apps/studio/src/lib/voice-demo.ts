import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export interface VoiceDemoLinkAccess {
  id: string;
  workspace_id: string;
  snapshot_id: string;
  url: string;
  expires_at: string;
  rate_limit: string;
  duration_cap_minutes: number;
  mic_test_required: boolean;
  redaction_policy: string;
  trace_capture_policy: string;
  whitelabel: boolean;
  status: "active" | "expired";
  session_count: number;
}

export interface VoiceDemoSession {
  id: string;
  room: string;
  identity: string;
  livekit_url: string;
  expires_at: string;
  trace_capture_policy: string;
}

export interface CreatedVoiceDemoLink extends VoiceDemoLinkAccess {
  token: string;
}

export async function createVoiceDemoLink(
  workspaceId: string,
  snapshotId: string,
  opts: UxWireupClientOptions & { expiresInMinutes?: number } = {},
): Promise<CreatedVoiceDemoLink> {
  return cpJson<CreatedVoiceDemoLink>(
    `/workspaces/${encodeURIComponent(workspaceId)}/voice/demo-links`,
    {
      ...opts,
      method: "POST",
      body: {
        snapshot_id: snapshotId,
        expires_in_minutes: opts.expiresInMinutes ?? 5,
      },
      fallback: {} as CreatedVoiceDemoLink,
    },
  );
}

export async function fetchVoiceDemoLink(
  token: string,
  opts: UxWireupClientOptions = {},
): Promise<VoiceDemoLinkAccess> {
  return cpJson<VoiceDemoLinkAccess>(`/voice-demo/${encodeURIComponent(token)}`, {
    ...opts,
    fallback: {} as VoiceDemoLinkAccess,
  });
}

export async function startVoiceDemoSession(
  token: string,
  opts: UxWireupClientOptions = {},
): Promise<VoiceDemoSession> {
  return cpJson<VoiceDemoSession>(
    `/voice-demo/${encodeURIComponent(token)}/sessions`,
    {
      ...opts,
      method: "POST",
      fallback: {} as VoiceDemoSession,
    },
  );
}
