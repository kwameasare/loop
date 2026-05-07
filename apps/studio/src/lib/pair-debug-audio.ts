import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export interface PairDebugAudioSession {
  id: string;
  workspace_id: string;
  agent_id: string;
  participant_id: string;
  transport: "webrtc";
  signaling_url: string;
  ice_servers: ReadonlyArray<{ urls: readonly string[] }>;
  participants: readonly string[];
  expires_at: string;
}

export interface PairDebugAudioOptions extends UxWireupClientOptions {
  participantId?: string;
}

export async function createPairDebugAudioSession(
  workspaceId: string,
  agentId: string,
  opts: PairDebugAudioOptions = {},
): Promise<PairDebugAudioSession> {
  const participantId = opts.participantId ?? "builder:local";
  return cpJson<PairDebugAudioSession>(
    `/workspaces/${encodeURIComponent(workspaceId)}/pair-debug/audio/session`,
    {
      ...opts,
      method: "POST",
      body: {
        agent_id: agentId,
        participant_id: participantId,
      },
      fallback: {
        id: `pair-audio-${agentId}`,
        workspace_id: workspaceId,
        agent_id: agentId,
        participant_id: participantId,
        transport: "webrtc",
        signaling_url: `wss://studio.loop.test/pair-debug/${workspaceId}/${agentId}`,
        ice_servers: [{ urls: ["stun:stun.l.google.com:19302"] }],
        participants: [participantId, "builder:teammate"],
        expires_at: new Date(Date.now() + 15 * 60_000).toISOString(),
      },
    },
  );
}

export function hasPairDebugPeerSupport(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.RTCPeerConnection !== "undefined"
  );
}
