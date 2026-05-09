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
      "teams",
      "sms",
      "email",
      "voice",
      "webhook_api",
    ]) {
      expect(screen.getByTestId(`channel-type-${id}`)).toBeInTheDocument();
    }

    for (const id of ["web", "voice", "whatsapp", "telegram", "webhook_api"]) {
      expect(screen.getByTestId(`channel-type-${id}`)).toHaveAttribute(
        "href",
        "/agents/agt_123/channels",
      );
    }
  });
});
