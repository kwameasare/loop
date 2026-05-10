import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ChannelsPage, { resolveChannelsWorkspaceId } from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;
const ORIGINAL_WORKSPACE = process.env.LOOP_DEFAULT_WORKSPACE_ID;

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[key];
  } else {
    process.env[key] = value;
  }
}

describe("resolveChannelsWorkspaceId", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    restoreEnv("LOOP_DEFAULT_WORKSPACE_ID", ORIGINAL_WORKSPACE);
  });

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

  it("renders control-plane context failures without hiding non-voice channels", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";
    process.env.LOOP_DEFAULT_WORKSPACE_ID = "";

    render(await ChannelsPage());

    expect(screen.getByTestId("channels-agents-degraded")).toHaveTextContent(
      "Workspace context is required before listing agents.",
    );
    expect(screen.getByTestId("channels-workspace-degraded")).toHaveTextContent(
      "control-plane workspace endpoint",
    );
    expect(screen.getByTestId("channel-type-whatsapp")).toBeInTheDocument();
    expect(screen.getByTestId("channel-type-telegram")).toBeInTheDocument();
    expect(screen.getByTestId("channel-type-voice")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /open voice channel stage/i }),
    ).toHaveAttribute("href", "/voice");
    expect(
      screen.getByText(
        /Text, chat, email, webhooks, and telephony remain peers/i,
      ),
    ).toBeInTheDocument();
  });
});
