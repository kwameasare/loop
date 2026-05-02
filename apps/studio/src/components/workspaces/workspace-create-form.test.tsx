import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import { WorkspaceCreateForm } from "./workspace-create-form";

describe("WorkspaceCreateForm (S594)", () => {
  it("defaults the region dropdown to the inferred (or initial) region", () => {
    render(<WorkspaceCreateForm onSubmit={vi.fn()} initialRegion="eu-west" />);
    const select = screen.getByTestId("workspace-create-region") as HTMLSelectElement;
    expect(select.value).toBe("eu-west");
  });

  it("renders the cannot-change-later notice prominently", () => {
    render(<WorkspaceCreateForm onSubmit={vi.fn()} initialRegion="na-east" />);
    const notice = screen.getByTestId("workspace-create-region-notice");
    // The notice MUST contain the literal "cannot be changed" phrase
    // — auditors and product reviewers grep on it.
    expect(notice.textContent).toMatch(/cannot be changed/i);
    expect(notice.getAttribute("role")).toBe("note");
  });

  it("persists the selected region in the submit payload", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<WorkspaceCreateForm onSubmit={onSubmit} initialRegion="na-east" />);

    fireEvent.change(screen.getByTestId("workspace-create-name"), {
      target: { value: "Acme" },
    });
    fireEvent.change(screen.getByTestId("workspace-create-slug"), {
      target: { value: "acme" },
    });
    fireEvent.change(screen.getByTestId("workspace-create-region"), {
      target: { value: "eu-west" },
    });
    fireEvent.click(screen.getByTestId("workspace-create-submit"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: "Acme",
        slug: "acme",
        region: "eu-west",
      });
    });
  });

  it("shows an error when name/slug missing instead of submitting", () => {
    const onSubmit = vi.fn();
    render(<WorkspaceCreateForm onSubmit={onSubmit} initialRegion="na-east" />);
    fireEvent.submit(screen.getByTestId("workspace-create-form"));
    // Native required attributes will block in a real browser; here
    // we still defensively early-return inside the handler.
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("updates the region description when the dropdown changes", () => {
    render(<WorkspaceCreateForm onSubmit={vi.fn()} initialRegion="na-east" />);
    const desc = screen.getByTestId("workspace-create-region-description");
    expect(desc.textContent).toMatch(/us-east-2/);
    fireEvent.change(screen.getByTestId("workspace-create-region"), {
      target: { value: "eu-west" },
    });
    expect(desc.textContent).toMatch(/eu-west-1/);
  });
});
