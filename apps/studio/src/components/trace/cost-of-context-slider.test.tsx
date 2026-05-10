import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { CostOfContextSlider } from "@/components/trace/cost-of-context-slider";

describe("CostOfContextSlider", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    if (previousBaseUrl === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    }
  });

  it("does not advertise local ablations when cp-api is unavailable", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    render(<CostOfContextSlider agentId="agent_support" turnId="turn_1" />);

    expect(await screen.findByText(/LOOP_CP_API_BASE_URL is required/i)).toBeInTheDocument();
    expect(screen.getByTestId("cost-of-context-slider")).toHaveTextContent(
      "0 ablations",
    );
    expect(screen.queryByText("Long-tail prompt sections")).not.toBeInTheDocument();
  });
});
