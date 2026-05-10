import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChannelBindingsPanel } from "./channel-bindings-panel";
import {
  type ChannelBinding,
  buildLocalChannelBindings,
} from "@/lib/channel-bindings";

describe("ChannelBindingsPanel", () => {
  const ORIGINAL_BASE_URL = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    if (ORIGINAL_BASE_URL === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE_URL;
    }
  });

  it("renders all peer channel bindings with voice as one card", () => {
    render(
      <ChannelBindingsPanel
        agentId="agt_1"
        initialBindings={buildLocalChannelBindings("agt_1")}
      />,
    );

    for (const channelType of [
      "web_chat",
      "whatsapp",
      "telegram",
      "slack",
      "teams",
      "sms",
      "email",
      "voice",
      "webhook_api",
    ]) {
      expect(
        screen.getByTestId(`channel-binding-${channelType}`),
      ).toBeInTheDocument();
    }
    expect(screen.getByTestId("channel-bindings-panel")).toHaveTextContent(
      "Voice is a channel binding",
    );
  });

  it("starts setup by upserting a draft channel binding", async () => {
    const upsertChannelBinding = vi.fn(
      async (_agentId: string, input: Partial<ChannelBinding>) => ({
        ...buildLocalChannelBindings("agt_1").find(
          (binding) => binding.channel_type === input.channel_type,
        )!,
        ...input,
        status: "draft" as const,
      }),
    );
    render(
      <ChannelBindingsPanel
        agentId="agt_1"
        initialBindings={buildLocalChannelBindings("agt_1")}
        upsertChannelBinding={upsertChannelBinding}
      />,
    );

    fireEvent.click(screen.getByTestId("channel-binding-draft-whatsapp"));

    await waitFor(() => {
      expect(upsertChannelBinding).toHaveBeenCalledWith(
        "agt_1",
        expect.objectContaining({
          channel_type: "whatsapp",
          status: "draft",
        }),
      );
    });
    expect(screen.getByTestId("channel-binding-whatsapp")).toHaveTextContent(
      "draft",
    );
  });

  it("shows an explicit backend requirement instead of drafting locally", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    render(
      <ChannelBindingsPanel
        agentId="agt_1"
        initialBindings={buildLocalChannelBindings("agt_1")}
      />,
    );

    fireEvent.click(screen.getByTestId("channel-binding-draft-whatsapp"));

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("channel-binding-whatsapp")).toHaveTextContent(
      "not configured",
    );
  });
});
