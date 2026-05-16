import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WelcomeLanding } from "./welcome-landing";

describe("WelcomeLanding", () => {
  it("renders enterprise CTAs and does not require workspace data", () => {
    render(<WelcomeLanding />);

    expect(
      screen.getByRole("heading", { name: /agents you can see through/i, level: 1 }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: /get started/i })[0],
    ).toHaveAttribute("href", "/signup");
    expect(screen.getByRole("link", { name: /open studio/i })).toHaveAttribute(
      "href",
      "/login?returnTo=/home",
    );
    expect(
      screen.getByText(/Talks where your people are/i),
    ).toBeInTheDocument();
  });
});
