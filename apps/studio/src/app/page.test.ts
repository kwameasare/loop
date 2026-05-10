import { describe, expect, it } from "vitest";

import { resolveHomeWorkspaceId } from "./page";

describe("resolveHomeWorkspaceId", () => {
  it("uses an existing agent workspace when agents are present", () => {
    expect(
      resolveHomeWorkspaceId(
        [
          {
            id: "agent-1",
            name: "Agent",
            description: "",
            slug: "agent",
            active_version: null,
            object_state: "draft",
            state_reason: "draft",
            state_evidence_ref: "agent.draft",
            updated_at: "2026-05-01T00:00:00Z",
            workspace_id: "ws_agent",
          },
        ],
        [{ id: "ws_workspace", name: "Workspace", slug: "workspace", role: "owner" }],
        "ws_env",
      ),
    ).toBe("ws_agent");
  });

  it("uses the authorized workspace list for empty workspaces", () => {
    expect(
      resolveHomeWorkspaceId(
        [],
        [{ id: "ws_empty", name: "Empty workspace", slug: "empty", role: "owner" }],
        undefined,
      ),
    ).toBe("ws_empty");
  });

  it("does not invent a local workspace id", () => {
    expect(resolveHomeWorkspaceId([], [], undefined)).toBeNull();
  });
});
