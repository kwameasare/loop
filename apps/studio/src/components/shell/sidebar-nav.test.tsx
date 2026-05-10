import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/agents",
}));

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

import {
  NAV_ITEMS,
  NAV_SECTIONS,
  SidebarNav,
  buildNavSections,
} from "@/components/shell/sidebar-nav";

describe("SidebarNav", () => {
  it("renders the primary queue and expands lifecycle sections on demand", () => {
    render(<SidebarNav />);
    expect(screen.getByTestId("nav-inbox")).toHaveAttribute("href", "/inbox");
    expect(screen.getByTestId("nav-agents")).toHaveAttribute("href", "/agents");
    expect(screen.getByTestId("nav-channels")).toHaveAttribute(
      "href",
      "/channels",
    );
    expect(screen.getByTestId("nav-channels")).toHaveTextContent("Channels");
    expect(screen.getByTestId("nav-channels")).toHaveTextContent(
      "Web, WhatsApp, Telegram, Slack, Teams, SMS, email, voice",
    );
    expect(screen.getByTestId("nav-voice-channel-stage")).toHaveAttribute(
      "href",
      "/voice",
    );

    fireEvent.click(screen.getByRole("button", { name: /observe/i }));
    expect(screen.getByTestId("nav-observatory")).toHaveAttribute(
      "href",
      "/observe",
    );
    expect(screen.queryByTestId("nav-voice")).not.toBeInTheDocument();
  });

  it("renders the canonical six-verb IA", () => {
    render(<SidebarNav />);
    expect(NAV_SECTIONS.map((section) => section.label)).toEqual([
      "Build",
      "Test",
      "Ship",
      "Observe",
      "Migrate",
      "Govern",
    ]);
    for (const section of NAV_SECTIONS) {
      expect(
        screen.getByTestId(`nav-section-${section.id}`),
      ).toBeInTheDocument();
    }
  });

  it("marks the matching route as the active page", () => {
    render(<SidebarNav />);
    const active = screen.getByTestId("nav-agents");
    expect(active).toHaveAttribute("aria-current", "page");
    fireEvent.click(screen.getByRole("button", { name: /ship/i }));
    expect(screen.getByTestId("nav-deploy-safety")).toHaveAttribute(
      "href",
      "/deploy/safety",
    );
    const inactive = screen.getByTestId("nav-money");
    expect(inactive).not.toHaveAttribute("aria-current");
  });

  it("does not ship duplicate lifecycle destinations", () => {
    const hrefs = NAV_ITEMS.map((item) => item.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("agent-scoped deploy links only deep-link after an agent is selected", () => {
    const withoutAgent = buildNavSections();
    const withAgent = buildNavSections("agent_123");
    expect(
      withoutAgent
        .flatMap((section) => section.items)
        .find((item) => item.id === "deploys")?.href,
    ).toBe("/deploys");
    expect(
      withoutAgent
        .flatMap((section) => section.items)
        .find((item) => item.id === "deploy-safety")?.href,
    ).toBe("/deploy/safety");
    expect(
      withoutAgent
        .flatMap((section) => section.items)
        .find((item) => item.id === "versions"),
    ).toBeUndefined();
    expect(
      withAgent
        .flatMap((section) => section.items)
        .find((item) => item.id === "deploys")?.href,
    ).toBe("/agents/agent_123/deploys");
  });
});
