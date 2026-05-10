import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/deploy"),
}));

import { HelpClipLauncher } from "@/components/help/help-clip-launcher";

describe("HelpClipLauncher", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    if (previousBaseUrl === undefined) delete process.env.LOOP_CP_API_BASE_URL;
    else process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
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

  it("plays contextual clips inline instead of linking to missing mp4 assets", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({
          items: [
            {
              clip_id: "clip_canary_slider",
              surface: "pipeline",
              title: "Canary promotion",
              url: "/help/clips/canary-slider",
              duration: 30,
              transcript: "Show me canary.",
              frames: [
                "Open the release candidate.",
                "Move the canary slider after gates pass.",
              ],
            },
          ],
        }),
      ),
    );

    render(<HelpClipLauncher />);

    fireEvent.click(screen.getByRole("button", { name: /open contextual help/i }));
    fireEvent.click(await screen.findByRole("button", { name: /play clip_canary_slider muted/i }));

    expect(screen.getByTestId("inline-help-clip")).toHaveTextContent(
      "Muted clip playing",
    );
    expect(screen.getByTestId("inline-help-clip")).toHaveTextContent(
      "Move the canary slider after gates pass.",
    );
    expect(screen.queryByRole("link", { name: /play/i })).not.toBeInTheDocument();
  });
});
