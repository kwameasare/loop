import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, act } from "@testing-library/react";

import { AppErrorBoundary } from "./error-boundary";
import { ToastProvider } from "@/lib/toast";

function Boom({ when }: { when: boolean }) {
  if (when) {
    const err = new Error("kaboom") as Error & {
      code?: string;
      requestId?: string;
    };
    err.code = "E_LOOP_500";
    err.requestId = "req_xyz";
    throw err;
  }
  return <span data-testid="ok">ok</span>;
}

describe("AppErrorBoundary", () => {
  it("renders fallback and emits a toast carrying code + request_id", () => {
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    try {
      render(
        <ToastProvider>
          <AppErrorBoundary>
            <Boom when={true} />
          </AppErrorBoundary>
        </ToastProvider>,
      );
      expect(screen.getByTestId("error-boundary-fallback")).toBeTruthy();
      const toastRow = screen.getByTestId("toast-error");
      expect(toastRow).toHaveTextContent("E_LOOP_500");
      expect(toastRow).toHaveTextContent("req_xyz");
    } finally {
      errSpy.mockRestore();
    }
  });

  it("recovers when reset is invoked", () => {
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    try {
      function Harness() {
        return (
          <ToastProvider>
            <AppErrorBoundary>
              <Boom when={true} />
            </AppErrorBoundary>
          </ToastProvider>
        );
      }
      const { rerender } = render(<Harness />);
      expect(screen.getByTestId("error-boundary-fallback")).toBeTruthy();
      act(() => {
        fireEvent.click(screen.getByTestId("error-boundary-reset"));
      });
      // After reset, re-render with a non-throwing child.
      rerender(
        <ToastProvider>
          <AppErrorBoundary>
            <Boom when={false} />
          </AppErrorBoundary>
        </ToastProvider>,
      );
      expect(screen.getByTestId("ok")).toBeTruthy();
    } finally {
      errSpy.mockRestore();
    }
  });
});
