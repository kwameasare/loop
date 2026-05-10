import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

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
  });

  it("renders channel and web embed degraded states without hiding peer channels", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";

    render(await AgentChannelsPage({ params: { agent_id: "agt_1" } }));

    expect(screen.getByTestId("agent-channels")).toBeInTheDocument();
    expect(screen.getByTestId("channel-bindings-degraded")).toHaveTextContent(
      "Live channel state is unavailable",
    );
    expect(screen.getByTestId("web-channel-degraded")).toHaveTextContent(
      "LOOP_CP_API_BASE_URL is required to load web channel",
    );
    expect(screen.getByTestId("channel-type-whatsapp")).toBeInTheDocument();
    expect(screen.getByTestId("channel-type-voice")).toBeInTheDocument();
  });
});
