import { describe, expect, it } from "vitest";

import { resolveChannelsWorkspaceId } from "./page";

describe("resolveChannelsWorkspaceId", () => {
  it("uses an agent workspace when the registry has agents", () => {
    expect(
      resolveChannelsWorkspaceId(
        [
          {
            id: "agt_support",
            name: "Support",
            description: "Support agent",
            slug: "support",
            active_version: 1,
            object_state: "production",
            state_reason: "Live",
            state_evidence_ref: "deploy/dep_1",
            updated_at: "2026-05-01T00:00:00Z",
            workspace_id: "ws_from_agent",
          },
        ],
        [
          {
            id: "ws_from_workspace",
            name: "Workspace",
            slug: "workspace",
            role: "owner",
          },
        ],
      ),
    ).toBe("ws_from_agent");
  });

  it("uses the authorized workspace list when the workspace has no agents", () => {
    expect(
      resolveChannelsWorkspaceId(
        [],
        [
          {
            id: "ws_empty",
            name: "Empty workspace",
            slug: "empty",
            role: "admin",
          },
        ],
      ),
    ).toBe("ws_empty");
  });

  it("does not invent a local workspace id", () => {
    expect(resolveChannelsWorkspaceId([], [], undefined)).toBeNull();
  });
});
