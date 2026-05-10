import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/deploy"),
}));

import { HelpClipLauncher } from "@/components/help/help-clip-launcher";

describe("HelpClipLauncher", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    vi.unstubAllGlobals();
  });

  it("shows a degraded state instead of a local fake help clip", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    render(<HelpClipLauncher />);

    fireEvent.click(screen.getByRole("button", { name: /open contextual help/i }));

    expect(await screen.findByTestId("help-clip-card")).toBeInTheDocument();
    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Show me the safest next step/i)).not.toBeInTheDocument();
  });
});
