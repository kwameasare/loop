import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { KbList } from "./kb-list";
import type { KbDocument } from "@/lib/kb";

const seed: KbDocument[] = [
  {
    id: "doc_a",
    agentId: "agt_demo",
    name: "guide.md",
    contentType: "text/markdown",
    bytes: 5120,
    status: "ready",
    uploadedAt: "2026-04-01T00:00:00Z",
    lastRefreshedAt: "2026-05-01T08:00:00Z",
  },
];

describe("KbList", () => {
  it("renders document rows with formatted size + status", () => {
    render(<KbList agentId="agt_demo" initialDocuments={seed} />);
    expect(screen.getByTestId("kb-doc-doc_a").textContent).toContain(
      "guide.md",
    );
    expect(screen.getByTestId("kb-doc-status-doc_a").textContent).toBe(
      "ready",
    );
  });

  it("renders empty state when no documents", () => {
    render(<KbList agentId="agt_demo" initialDocuments={[]} />);
    expect(screen.getByTestId("kb-empty")).toBeTruthy();
  });

  it("uploads a file with progress and prepends to the list", async () => {
    let progressFn: ((r: number) => void) | undefined;
    const upload = vi.fn(async (input: { onProgress?: (r: number) => void }) => {
      progressFn = input.onProgress;
      progressFn?.(0.5);
      progressFn?.(1);
      return {
        id: "doc_new",
        agentId: "agt_demo",
        name: "new.md",
        contentType: "text/markdown",
        bytes: 100,
        status: "indexing" as const,
        uploadedAt: "2026-05-01T00:00:00Z",
        lastRefreshedAt: null,
      };
    });
    render(
      <KbList
        agentId="agt_demo"
        initialDocuments={seed}
        upload={upload}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("kb-upload-open"));
    });
    expect(screen.getByTestId("kb-upload-modal")).toBeTruthy();
    const file = new File(["x"], "new.md", { type: "text/markdown" });
    await act(async () => {
      fireEvent.change(screen.getByTestId("kb-upload-file"), {
        target: { files: [file] },
      });
    });
    await act(async () => {
      fireEvent.submit(screen.getByTestId("kb-upload-submit").closest("form")!);
    });
    expect(upload).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("kb-doc-doc_new")).toBeTruthy();
    expect(screen.getByTestId("kb-toast-success").textContent).toContain(
      "Uploaded new.md",
    );
  });

  it("delete is gated behind typed-confirmation", async () => {
    const remove = vi.fn(async () => ({ documentId: "doc_a" }));
    render(
      <KbList
        agentId="agt_demo"
        initialDocuments={seed}
        remove={remove}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("kb-doc-delete-doc_a"));
    });
    const submit = screen.getByTestId("kb-delete-submit") as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    await act(async () => {
      fireEvent.change(screen.getByTestId("kb-delete-confirm"), {
        target: { value: "delete" },
      });
    });
    expect(submit.disabled).toBe(true);
    await act(async () => {
      fireEvent.change(screen.getByTestId("kb-delete-confirm"), {
        target: { value: "DELETE" },
      });
    });
    expect(submit.disabled).toBe(false);
    await act(async () => {
      fireEvent.click(submit);
    });
    expect(remove).toHaveBeenCalledWith({
      agentId: "agt_demo",
      documentId: "doc_a",
    });
    expect(screen.queryByTestId("kb-doc-doc_a")).toBeNull();
  });

  it("surfaces upload errors as toast.error", async () => {
    const upload = vi.fn(async () => {
      throw new Error("boom");
    });
    render(
      <KbList
        agentId="agt_demo"
        initialDocuments={seed}
        upload={upload}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("kb-upload-open"));
    });
    const file = new File(["x"], "x.md", { type: "text/markdown" });
    await act(async () => {
      fireEvent.change(screen.getByTestId("kb-upload-file"), {
        target: { files: [file] },
      });
    });
    await act(async () => {
      fireEvent.submit(screen.getByTestId("kb-upload-submit").closest("form")!);
    });
    expect(screen.getByTestId("kb-toast-error").textContent).toContain("boom");
  });

  it("shows last-refreshed timestamp when present", () => {
    render(<KbList agentId="agt_demo" initialDocuments={seed} />);
    const cell = screen.getByTestId("kb-doc-last-refreshed-doc_a");
    expect(cell.textContent).toContain("Refreshed");
  });

  it("shows 'Never refreshed' when lastRefreshedAt is null", () => {
    const noRefresh = [{ ...seed[0]!, lastRefreshedAt: null }];
    render(<KbList agentId="agt_demo" initialDocuments={noRefresh} />);
    expect(screen.getByTestId("kb-doc-last-refreshed-doc_a").textContent).toBe(
      "Never refreshed",
    );
  });

  it("refresh button calls triggerRefresh and updates lastRefreshedAt", async () => {
    const triggerRefresh = vi.fn(async (_agentId: string, documentId: string) => ({
      documentId,
      cadence: "daily" as const,
      status: "ok" as const,
      lastRunAt: "2026-06-01T09:00:00Z",
      nextRunAt: null,
      runCount: 2,
      error: null,
    }));
    render(
      <KbList
        agentId="agt_demo"
        initialDocuments={seed}
        triggerRefresh={triggerRefresh}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("kb-doc-refresh-doc_a"));
    });
    expect(triggerRefresh).toHaveBeenCalledWith("agt_demo", "doc_a");
    expect(screen.getByTestId("kb-doc-last-refreshed-doc_a").textContent).toContain(
      "Refreshed",
    );
  });

  it("refresh button is disabled while refresh is in-flight", async () => {
    let resolve!: () => void;
    const triggerRefresh = vi.fn(
      () =>
        new Promise<ReturnType<typeof import("@/lib/kb").triggerDocRefresh>>((res) => {
          resolve = () =>
            res({
              documentId: "doc_a",
              cadence: "daily",
              status: "ok",
              lastRunAt: "2026-06-01T09:00:00Z",
              nextRunAt: null,
              runCount: 2,
              error: null,
            });
        }),
    );
    render(
      <KbList
        agentId="agt_demo"
        initialDocuments={seed}
        triggerRefresh={triggerRefresh}
      />,
    );
    act(() => {
      fireEvent.click(screen.getByTestId("kb-doc-refresh-doc_a"));
    });
    const btn = screen.getByTestId("kb-doc-refresh-doc_a") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    await act(async () => { resolve(); });
    expect(btn.disabled).toBe(false);
  });

  it("refresh error surfaces as toast.error", async () => {
    const triggerRefresh = vi.fn(async () => {
      throw new Error("refresh boom");
    });
    render(
      <KbList
        agentId="agt_demo"
        initialDocuments={seed}
        triggerRefresh={triggerRefresh}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("kb-doc-refresh-doc_a"));
    });
    expect(screen.getByTestId("kb-toast-error").textContent).toContain(
      "refresh boom",
    );
  });
});
