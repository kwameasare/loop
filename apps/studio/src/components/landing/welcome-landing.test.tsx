import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WelcomeLanding } from "./welcome-landing";

describe("WelcomeLanding", () => {
  it("renders enterprise CTAs and does not require workspace data", () => {
    render(<WelcomeLanding />);

    expect(
      screen.getByRole("heading", { name: "Loop Studio", level: 1 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /start enterprise signup/i }),
    ).toHaveAttribute("href", "/signup");
    expect(screen.getByRole("link", { name: /open studio/i })).toHaveAttribute(
      "href",
      "/login?returnTo=/home",
    );
    expect(screen.getByText(/Omnichannel by design/i)).toBeInTheDocument();
  });
});
