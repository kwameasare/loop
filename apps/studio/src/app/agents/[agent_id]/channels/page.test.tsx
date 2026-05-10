import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

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
    expect(screen.getByTestId("channel-binding-whatsapp")).toHaveAttribute(
      "data-focused",
      "true",
    );
  });

  it("marks a missing web-channel route as degraded instead of disabled", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        new Response("missing", { status: 404 }),
      ),
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

  it("resolves channel binding evidence links to the peer channel card", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";

    render(
      await AgentChannelsPage({
        params: { agent_id: "agt_1" },
        searchParams: { binding_id: "cb_local_telegram" },
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
});
