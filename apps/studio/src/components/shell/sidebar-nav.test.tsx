import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/agents",
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

import { SidebarNav, NAV_ITEMS } from "@/components/shell/sidebar-nav";

describe("SidebarNav", () => {
  it("renders a link per nav item", () => {
    render(<SidebarNav />);
    for (const item of NAV_ITEMS) {
      expect(
        screen.getByTestId(`nav-${item.label.toLowerCase()}`),
      ).toHaveAttribute("href", item.href);
    }
  });

  it("marks the matching route as the active page", () => {
    render(<SidebarNav />);
    const active = screen.getByTestId("nav-agents");
    expect(active).toHaveAttribute("aria-current", "page");
    const inactive = screen.getByTestId("nav-costs");
    expect(inactive).not.toHaveAttribute("aria-current");
  });
});
