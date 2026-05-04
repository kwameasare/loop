import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ToolsList } from "./tools-list";

describe("ToolsList", () => {
  it("renders an empty state when there are no tools", () => {
    render(<ToolsList tools={[]} />);
    expect(screen.getByTestId("tools-empty")).toBeInTheDocument();
  });

  it("renders a row per tool with kind and source", () => {
    render(
      <ToolsList
        tools={[
          {
            id: "t1",
            name: "kb.search",
            kind: "mcp",
            description: "Search the workspace knowledge base",
            source: "https://kb.local/mcp",
          },
          {
            id: "t2",
            name: "stripe.refund",
            kind: "http",
            source: "https://api.stripe.com",
          },
        ]}
      />,
    );
    const items = screen.getAllByTestId("tools-item");
    expect(items).toHaveLength(2);
    expect(items[0].textContent).toContain("kb.search");
    expect(items[0].textContent).toContain("mcp");
    expect(items[0].textContent).toContain("knowledge base");
    expect(items[1].textContent).toContain("stripe.refund");
    expect(items[1].textContent).toContain("http");
  });
});
