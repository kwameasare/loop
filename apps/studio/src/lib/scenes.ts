import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export interface WorkspaceScene {
  id: string;
  name: string;
  category: string;
  trace_ids: string[];
  expected_behavior: string;
  created_by: string;
  created_at: string;
}

export interface SceneReplayResult {
  scene_id: string;
  status: "queued" | "running" | "completed" | "failed" | string;
  trace_ids: string[];
  draft_replay_id: string;
}

export async function listWorkspaceScenes(
  workspaceId: string,
  opts: UxWireupClientOptions = {},
): Promise<WorkspaceScene[]> {
  const body = await cpJson<{ items: WorkspaceScene[] }>(
    `/workspaces/${encodeURIComponent(workspaceId)}/scenes`,
    {
      ...opts,
      fallback: { items: [] },
      allowFallback: false,
    },
  );
  return body.items;
}

export async function replayWorkspaceScene(
  workspaceId: string,
  sceneId: string,
  opts: UxWireupClientOptions = {},
): Promise<SceneReplayResult> {
  return cpJson<SceneReplayResult>(
    `/workspaces/${encodeURIComponent(workspaceId)}/scenes/${encodeURIComponent(
      sceneId,
    )}/replay`,
    {
      ...opts,
      method: "POST",
      fallback: {
        scene_id: sceneId,
        status: "queued",
        trace_ids: [],
        draft_replay_id: "",
      },
      allowFallback: false,
    },
  );
}
