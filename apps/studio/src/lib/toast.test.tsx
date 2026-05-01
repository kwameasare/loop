import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import { ToastProvider, toast, useToasts } from "./toast";

function Probe() {
  const { toasts } = useToasts();
  return <span data-testid="probe-count">{toasts.length}</span>;
}

describe("toast system", () => {
  it("renders error toasts with code and request_id", () => {
    render(
      <ToastProvider>
        <Probe />
      </ToastProvider>,
    );
    act(() => {
      toast.error({
        title: "Save failed",
        description: "could not write",
        code: "E_LOOP_429",
        requestId: "req_abc",
      });
    });
    const row = screen.getByTestId("toast-error");
    expect(row).toHaveTextContent("Save failed");
    expect(row).toHaveTextContent("E_LOOP_429");
    expect(row).toHaveTextContent("req_abc");
  });

  it("supports string shorthand and dismiss button", () => {
    render(
      <ToastProvider>
        <Probe />
      </ToastProvider>,
    );
    let id = "";
    act(() => {
      id = toast.success("Created");
    });
    expect(screen.getByTestId("toast-success")).toHaveTextContent("Created");
    act(() => {
      fireEvent.click(screen.getByTestId(`toast-dismiss-${id}`));
    });
    expect(screen.queryByTestId("toast-success")).toBeNull();
  });

  it("auto-dismisses after the configured duration", () => {
    vi.useFakeTimers();
    try {
      render(
        <ToastProvider>
          <Probe />
        </ToastProvider>,
      );
      act(() => {
        toast.info({ title: "FYI", durationMs: 2000 });
      });
      expect(screen.getByTestId("toast-info")).toBeTruthy();
      act(() => {
        vi.advanceTimersByTime(2100);
      });
      expect(screen.queryByTestId("toast-info")).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it("warns and drops toasts when no provider is mounted", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    try {
      const id = toast.error("orphan");
      expect(id).toBe("");
      expect(warn).toHaveBeenCalled();
    } finally {
      warn.mockRestore();
    }
  });
});
