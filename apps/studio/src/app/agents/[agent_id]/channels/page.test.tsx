import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { buildLocalChannelBindings } from "@/lib/channel-bindings";

import AgentChannelsPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[key];
  } else {
    process.env[key] = value;
  }
}

describe("AgentChannelsPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("renders channel and web embed degraded states without hiding peer channels", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";

    render(
      await AgentChannelsPage({
        params: { agent_id: "agt_1" },
        searchParams: { channel: "whatsapp" },
      }),
    );

    expect(screen.getByTestId("agent-channels")).toBeInTheDocument();
    expect(screen.getByTestId("channel-bindings-degraded")).toHaveTextContent(
      "Live channel state is unavailable",
    );
    expect(screen.getByTestId("web-channel-degraded")).toHaveTextContent(
      "LOOP_CP_API_BASE_URL is required to load web channel",
    );
    expect(screen.getByTestId("channel-type-whatsapp")).toBeInTheDocument();
    expect(screen.getByTestId("channel-type-voice")).toBeInTheDocument();
    expect(screen.getByTestId("channel-bindings-empty")).toHaveTextContent(
      "WhatsApp is selected",
    );
    expect(
      screen.queryByTestId("channel-binding-whatsapp"),
    ).not.toBeInTheDocument();
  });

  it("resolves channel binding evidence links only from live backend bindings", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const liveBindings = buildLocalChannelBindings("agt_live")
      .filter((binding) =>
        ["telegram", "voice"].includes(binding.channel_type),
      )
      .map((binding) => ({
        ...binding,
        id:
          binding.channel_type === "telegram"
            ? "cb_live_telegram"
            : "cb_live_voice",
        workspace_id: "ws_live",
      }));
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input) => {
        const url = String(input);
        if (url.endsWith("/agents/agt_live/channel-bindings")) {
          return Response.json({ items: liveBindings });
        }
        if (url.endsWith("/agents/agt_live/channels/web")) {
          return Response.json({
            agentId: "agt_live",
            status: "disabled",
            channelId: null,
            token: null,
            enabledAt: null,
          });
        }
        return new Response("missing", { status: 404 });
      }),
    );

    render(
      await AgentChannelsPage({
        params: { agent_id: "agt_live" },
        searchParams: { binding_id: "cb_live_telegram" },
      }),
    );

    expect(screen.getByTestId("channel-binding-telegram")).toHaveAttribute(
      "data-focused",
      "true",
    );
    expect(screen.getByTestId("channel-binding-voice")).toHaveAttribute(
      "data-focused",
      "false",
    );
  });

  it("marks a missing web-channel route as degraded instead of disabled", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () => new Response("missing", { status: 404 })),
    );

    render(await AgentChannelsPage({ params: { agent_id: "agt_404" } }));

    expect(screen.getByTestId("web-channel-degraded")).toHaveTextContent(
      "web channel route returned 404",
    );
    expect(screen.getByTestId("web-channel-toggle")).toBeDisabled();
    expect(screen.getByTestId("web-channel-toggle")).toHaveTextContent(
      "Backend required",
    );
  });

  it("does not resolve binding evidence links from local setup templates", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";

    render(
      await AgentChannelsPage({
        params: { agent_id: "agt_1" },
        searchParams: { binding_id: "cb_local_telegram" },
      }),
    );

    expect(screen.getByTestId("channel-bindings-empty")).toHaveTextContent(
      "Choose a channel above",
    );
    expect(
      screen.queryByTestId("channel-binding-telegram"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("channel-binding-voice"),
    ).not.toBeInTheDocument();
  });

  it("shows an explicit empty state when no backend bindings exist yet", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input) => {
        const url = String(input);
        if (url.endsWith("/agents/agt_empty/channel-bindings")) {
          return Response.json({ items: [] });
        }
        if (url.endsWith("/agents/agt_empty/channels/web")) {
          return Response.json({
            agentId: "agt_empty",
            status: "disabled",
            channelId: null,
            token: null,
            enabledAt: null,
          });
        }
        return new Response("missing", { status: 404 });
      }),
    );

    render(await AgentChannelsPage({ params: { agent_id: "agt_empty" } }));

    expect(screen.getByTestId("channel-bindings-empty")).toHaveTextContent(
      "No channel bindings configured yet",
    );
    expect(screen.getByTestId("channel-type-whatsapp")).toBeInTheDocument();
    expect(screen.getByTestId("channel-type-voice")).toBeInTheDocument();
  });

  it("focuses the readiness panel from Workbench evidence links", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";

    render(
      await AgentChannelsPage({
        params: { agent_id: "agt_1" },
        searchParams: { view: "readiness" },
      }),
    );

    expect(
      screen.getByTestId("channel-readiness-focused-workbench-panel"),
    ).toHaveTextContent("Channel readiness");
    expect(screen.getByTestId("channel-bindings-panel")).toHaveClass(
      "ring-focus",
    );
  });
});
