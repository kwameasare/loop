import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import { EnterpriseSsoForm } from "./enterprise-sso-form";

describe("EnterpriseSsoForm (S615)", () => {
  it("renders the Not connected status by default", () => {
    render(<EnterpriseSsoForm status="not_connected" onSubmit={vi.fn()} />);
    const badge = screen.getByTestId("enterprise-sso-status");
    expect(badge.textContent).toMatch(/not connected/i);
    expect(badge.getAttribute("data-status")).toBe("not_connected");
  });

  it("flips to Connected when status prop is connected", () => {
    render(<EnterpriseSsoForm status="connected" onSubmit={vi.fn()} />);
    const badge = screen.getByTestId("enterprise-sso-status");
    expect(badge.textContent).toMatch(/^connected$/i);
    expect(badge.getAttribute("data-status")).toBe("connected");
  });

  it("submits the metadata URL when only the URL is filled", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<EnterpriseSsoForm status="not_connected" onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId("enterprise-sso-metadata-url"), {
      target: { value: "https://idp.example.com/metadata" },
    });
    fireEvent.click(screen.getByTestId("enterprise-sso-submit"));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        metadataUrl: "https://idp.example.com/metadata",
      });
    });
  });

  it("submits the uploaded XML contents when a file is chosen", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<EnterpriseSsoForm status="not_connected" onSubmit={onSubmit} />);
    const xml = "<EntityDescriptor entityID=\"urn:idp\"></EntityDescriptor>";
    const file = new File([xml], "metadata.xml", { type: "application/xml" });
    fireEvent.change(screen.getByTestId("enterprise-sso-metadata-file"), {
      target: { files: [file] },
    });
    await screen.findByTestId("enterprise-sso-xml-loaded");
    fireEvent.click(screen.getByTestId("enterprise-sso-submit"));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({ metadataXml: xml });
    });
  });

  it("shows a local error and does NOT call onSubmit when both URL and XML are provided", async () => {
    const onSubmit = vi.fn();
    render(<EnterpriseSsoForm status="not_connected" onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId("enterprise-sso-metadata-url"), {
      target: { value: "https://idp.example.com/metadata" },
    });
    const file = new File(["<x/>"], "metadata.xml", { type: "application/xml" });
    fireEvent.change(screen.getByTestId("enterprise-sso-metadata-file"), {
      target: { files: [file] },
    });
    await screen.findByTestId("enterprise-sso-xml-loaded");
    fireEvent.click(screen.getByTestId("enterprise-sso-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("enterprise-sso-error").textContent).toMatch(
        /one of/i,
      );
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows the parent errorMessage when status is error", () => {
    render(
      <EnterpriseSsoForm
        status="error"
        onSubmit={vi.fn()}
        errorMessage="Metadata URL returned 404."
      />,
    );
    expect(screen.getByTestId("enterprise-sso-error").textContent).toMatch(
      /404/,
    );
    expect(screen.getByTestId("enterprise-sso-status").getAttribute("data-status")).toBe(
      "error",
    );
  });

  it("blocks submit when neither URL nor XML provided", async () => {
    const onSubmit = vi.fn();
    render(<EnterpriseSsoForm status="not_connected" onSubmit={onSubmit} />);
    fireEvent.click(screen.getByTestId("enterprise-sso-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("enterprise-sso-error").textContent).toMatch(
        /provide either/i,
      );
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
