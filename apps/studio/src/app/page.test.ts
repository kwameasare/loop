import { afterEach, describe, expect, it } from "vitest";

import { homeContextWarnings, resolveHomeWorkspaceId } from "./home/page";

const ORIGINAL_WORKSPACE = process.env.LOOP_DEFAULT_WORKSPACE_ID;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[key];
  } else {
    process.env[key] = value;
  }
}

describe("resolveHomeWorkspaceId", () => {
  afterEach(() => {
    restoreEnv("LOOP_DEFAULT_WORKSPACE_ID", ORIGINAL_WORKSPACE);
  });

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
        [
          {
            id: "ws_workspace",
            name: "Workspace",
            slug: "workspace",
            role: "owner",
          },
        ],
      ),
    ).toBe("ws_agent");
  });

  it("uses the authorized workspace list for empty workspaces", () => {
    expect(
      resolveHomeWorkspaceId(
        [],
        [
          {
            id: "ws_empty",
            name: "Empty workspace",
            slug: "empty",
            role: "owner",
          },
        ],
        undefined,
      ),
    ).toBe("ws_empty");
  });

  it("does not invent a local workspace id", () => {
    delete process.env.LOOP_DEFAULT_WORKSPACE_ID;
    expect(resolveHomeWorkspaceId([], [])).toBeNull();
  });
});

describe("homeContextWarnings", () => {
  it("keeps backend failures visible instead of making home look empty", () => {
    expect(
      homeContextWarnings(
        "cp-api GET agents -> 503",
        "Workspace context requires cp-api.",
      ),
    ).toEqual([
      "Agent registry unavailable: cp-api GET agents -> 503",
      "Workspace context unavailable: Workspace context requires cp-api.",
    ]);
  });

  it("omits warnings when context loaded cleanly", () => {
    expect(homeContextWarnings()).toEqual([]);
  });
});
