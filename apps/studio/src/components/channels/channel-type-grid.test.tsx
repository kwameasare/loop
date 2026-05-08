import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChannelTypeGrid } from "./channel-type-grid";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

describe("ChannelTypeGrid", () => {
  it("presents voice as one peer in an omnichannel system", () => {
    render(<ChannelTypeGrid agentId="agt_123" />);

    for (const id of [
      "web",
      "whatsapp",
      "telegram",
      "slack",
      "sms",
      "email",
      "voice",
    ]) {
      expect(screen.getByTestId(`channel-type-${id}`)).toBeInTheDocument();
    }

    expect(screen.getByTestId("channel-type-web")).toHaveAttribute(
      "href",
      "/agents/agt_123/channels",
    );
    expect(screen.getByTestId("channel-type-voice")).toHaveAttribute(
      "href",
      "/voice",
    );
    expect(screen.getByTestId("channel-type-whatsapp")).toHaveAttribute(
      "href",
      "/marketplace",
    );
  });
});
