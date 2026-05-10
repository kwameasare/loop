import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChannelBindingsPanel } from "./channel-bindings-panel";
import {
  type ChannelBinding,
  type ChannelReadinessInput,
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
    expect(
      screen.getByTestId("channel-binding-contract-whatsapp"),
    ).toHaveTextContent("Template-safe text with numbered options");
    expect(
      screen.getByTestId("channel-binding-contract-whatsapp"),
    ).toHaveTextContent("Opt-in required");
    expect(
      screen.getByTestId("channel-binding-contract-voice"),
    ).toHaveTextContent("Short spoken answer with confirmation prompts");
    expect(
      screen.getByTestId("channel-binding-contract-webhook_api"),
    ).toHaveTextContent("Signed JSON payload");
    expect(
      screen.getByTestId("channel-required-config-web_chat"),
    ).toHaveTextContent("Embed snippet");
    expect(
      screen.getByTestId("channel-required-config-web_chat"),
    ).toHaveTextContent("pending verification");
    expect(
      screen.getByTestId("channel-required-config-whatsapp"),
    ).toHaveTextContent("Template approvals");
    expect(
      screen.getByTestId("channel-required-config-telegram"),
    ).toHaveTextContent("Abuse controls");
    expect(
      screen.getByTestId("channel-required-config-slack"),
    ).toHaveTextContent("Slash commands");
    expect(screen.getByTestId("channel-required-config-sms")).toHaveTextContent(
      "Carrier compliance",
    );
    expect(
      screen.getByTestId("channel-required-config-email"),
    ).toHaveTextContent("Signature policy");
    expect(
      screen.getByTestId("channel-required-config-voice"),
    ).toHaveTextContent("Barge-in policy");
    expect(
      screen.getByTestId("channel-required-config-webhook_api"),
    ).toHaveTextContent("Idempotency key");
  });

  it("focuses the channel selected from the workspace channel catalog", () => {
    render(
      <ChannelBindingsPanel
        agentId="agt_1"
        initialBindings={buildLocalChannelBindings("agt_1")}
        focusedChannelType="whatsapp"
      />,
    );

    expect(screen.getByTestId("channel-binding-whatsapp")).toHaveAttribute(
      "data-focused",
      "true",
    );
    expect(screen.getByTestId("channel-binding-voice")).toHaveAttribute(
      "data-focused",
      "false",
    );
  });

  it("shows channel activity evidence when traffic and failures are recorded", () => {
    const bindings = buildLocalChannelBindings("agt_1").map((binding) =>
      binding.channel_type === "whatsapp"
        ? {
            ...binding,
            status: "live" as const,
            last_traffic_at: "2026-05-10T10:00:00Z",
            last_failure_at: "2026-05-10T10:05:00Z",
          }
        : binding,
    );

    render(<ChannelBindingsPanel agentId="agt_1" initialBindings={bindings} />);

    expect(screen.getByTestId("channel-binding-whatsapp")).toHaveTextContent(
      "2026-05-10 10:00",
    );
    expect(screen.getByTestId("channel-binding-whatsapp")).toHaveTextContent(
      "2026-05-10 10:05",
    );
  });

  it("focuses channel readiness when opened from Workbench evidence", () => {
    render(
      <ChannelBindingsPanel
        agentId="agt_1"
        initialBindings={buildLocalChannelBindings("agt_1")}
        focusReadiness={true}
      />,
    );

    expect(
      screen.getByTestId("channel-readiness-focused-workbench-panel"),
    ).toHaveTextContent("identity, auth, consent");
    expect(screen.getByTestId("channel-bindings-panel")).toHaveClass(
      "ring-focus",
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
    expect(screen.getByTestId("channel-setup-whatsapp")).toHaveTextContent(
      "Business account",
    );
    expect(screen.getByTestId("channel-binding-whatsapp")).toHaveTextContent(
      "draft",
    );

    fireEvent.change(screen.getByTestId("channel-provider-whatsapp"), {
      target: { value: "Meta Cloud API" },
    });
    fireEvent.change(screen.getByTestId("channel-identity-whatsapp"), {
      target: { value: "waba_123" },
    });
    fireEvent.change(screen.getByTestId("channel-auth-ref-whatsapp"), {
      target: { value: "secret://channels/waba" },
    });
    fireEvent.click(screen.getByTestId("channel-setup-save-whatsapp"));

    await waitFor(() => {
      expect(upsertChannelBinding).toHaveBeenLastCalledWith(
        "agt_1",
        expect.objectContaining({
          channel_type: "whatsapp",
          provider: "Meta Cloud API",
          auth_config_ref: "secret://channels/waba",
          identity_config: expect.objectContaining({
            business_account: "waba_123",
          }),
        }),
      );
    });
  });

  it("records readiness evidence from the channel card", async () => {
    const [whatsapp] = buildLocalChannelBindings("agt_1").filter(
      (binding) => binding.channel_type === "whatsapp",
    );
    const updateChannelReadiness = vi.fn(
      async (
        _agentId: string,
        _bindingId: string,
        checkId: string,
        input: ChannelReadinessInput,
      ) => ({
        ...whatsapp!,
        status: "draft" as const,
        readiness: whatsapp!.readiness.map((check) =>
          check.id === checkId
            ? {
                ...check,
                status: input.status,
                evidence_ref: input.evidence_ref ?? null,
                message: "verified",
              }
            : check,
        ),
      }),
    );
    render(
      <ChannelBindingsPanel
        agentId="agt_1"
        initialBindings={buildLocalChannelBindings("agt_1")}
        updateChannelReadiness={updateChannelReadiness}
      />,
    );

    fireEvent.click(
      screen.getByTestId("channel-readiness-passed-whatsapp-business_verified"),
    );

    await waitFor(() => {
      expect(updateChannelReadiness).toHaveBeenCalledWith(
        "agt_1",
        whatsapp!.id,
        "business_verified",
        expect.objectContaining({
          status: "passed",
          evidence_ref: "manual/whatsapp/business_verified",
        }),
      );
    });
    expect(screen.getByTestId("channel-binding-whatsapp")).toHaveTextContent(
      "Evidence: manual/whatsapp/business_verified",
    );
  });

  it("disables setup when channel state is degraded", () => {
    const upsertChannelBinding = vi.fn();
    render(
      <ChannelBindingsPanel
        agentId="agt_1"
        initialBindings={buildLocalChannelBindings("agt_1")}
        degradedReason="Channel binding status requires cp-api. Studio is showing setup requirements only."
        upsertChannelBinding={upsertChannelBinding}
      />,
    );

    expect(screen.getByTestId("channel-bindings-degraded")).toHaveTextContent(
      "Live channel state is unavailable",
    );
    const draftButton = screen.getByTestId("channel-binding-draft-whatsapp");
    expect(draftButton).toBeDisabled();
    expect(draftButton).toHaveTextContent("Backend required");
    fireEvent.click(draftButton);
    expect(upsertChannelBinding).not.toHaveBeenCalled();
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
