/**
 * Component test for the web-channel card. Validates the enable/disable
 * happy paths, the snippet copy flow, and the disabled-by-default UI.
 */
import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WebChannelCard } from "./web-channel-card";
import type { WebChannelBinding } from "@/lib/web-channels";

const disabled: WebChannelBinding = {
  agentId: "agt_demo",
  status: "disabled",
  channelId: null,
  token: null,
  enabledAt: null,
};

const enabled: WebChannelBinding = {
  agentId: "agt_demo",
  status: "enabled",
  channelId: "wch_xyz",
  token: "wct_real",
  enabledAt: "2026-05-01T00:00:00Z",
};

describe("WebChannelCard", () => {
  it("renders disabled state with placeholder snippet", () => {
    render(<WebChannelCard agentId="agt_demo" initialBinding={disabled} />);
    const card = screen.getByTestId("web-channel-card");
    expect(card.getAttribute("data-status")).toBe("disabled");
    expect(screen.getByTestId("web-channel-toggle").textContent).toBe(
      "Enable",
    );
    expect(
      (screen.getByTestId("web-channel-snippet") as HTMLTextAreaElement).value,
    ).toContain("Enable the web channel");
    expect(
      (screen.getByTestId("web-channel-copy") as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("enabling mints a snippet with the new token", async () => {
    const enable = vi.fn(async () => enabled);
    render(
      <WebChannelCard
        agentId="agt_demo"
        initialBinding={disabled}
        enable={enable}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("web-channel-toggle"));
    });
    expect(enable).toHaveBeenCalledWith("agt_demo");
    const snippet = (
      screen.getByTestId("web-channel-snippet") as HTMLTextAreaElement
    ).value;
    expect(snippet).toContain('data-token="wct_real"');
    expect(snippet).toContain('data-agent-id="agt_demo"');
    expect(screen.getByTestId("web-channel-id").textContent).toContain(
      "wch_xyz",
    );
    expect(
      screen.getByTestId("web-channel-toast-success").textContent,
    ).toContain("Web channel enabled");
  });

  it("disabling reverts to placeholder", async () => {
    const disable = vi.fn(async () => disabled);
    render(
      <WebChannelCard
        agentId="agt_demo"
        initialBinding={enabled}
        disable={disable}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("web-channel-toggle"));
    });
    expect(disable).toHaveBeenCalledWith("agt_demo");
    expect(screen.getByTestId("web-channel-card").getAttribute("data-status")).toBe(
      "disabled",
    );
    expect(
      (screen.getByTestId("web-channel-snippet") as HTMLTextAreaElement).value,
    ).toContain("Enable the web channel");
  });

  it("copies the snippet to the clipboard", async () => {
    const copy = vi.fn<(snippet: string) => Promise<void>>(async () => undefined);
    render(
      <WebChannelCard
        agentId="agt_demo"
        initialBinding={enabled}
        copy={copy}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("web-channel-copy"));
    });
    expect(copy).toHaveBeenCalledTimes(1);
    expect(copy.mock.calls[0]?.[0]).toContain('data-token="wct_real"');
    expect(
      screen.getByTestId("web-channel-toast-success").textContent,
    ).toContain("copied");
  });

  it("surfaces enable failures as an error toast", async () => {
    const enable = vi.fn(async () => {
      throw new Error("cp-api boom");
    });
    render(
      <WebChannelCard
        agentId="agt_demo"
        initialBinding={disabled}
        enable={enable}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("web-channel-toggle"));
    });
    expect(
      screen.getByTestId("web-channel-toast-error").textContent,
    ).toContain("cp-api boom");
  });
});
