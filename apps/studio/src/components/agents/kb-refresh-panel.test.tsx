/**
 * S494 – tests for:
 *   1. `getDocRefreshStatus` / `setDocRefreshCadence` / `triggerDocRefresh` helpers
 *   2. `KbRefreshPanel` component (studio status display + on-demand trigger)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import {
  getDocRefreshStatus,
  setDocRefreshCadence,
  triggerDocRefresh,
  REFRESH_CADENCE_LABELS,
  type DocRefreshStatus,
  type KbHelperOptions,
} from "@/lib/kb";
import { KbRefreshPanel } from "./kb-refresh-panel";

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function makeFetcher(payload: unknown, ok = true) {
  return vi.fn().mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    json: async () => payload,
  } as Response);
}

const FIXTURE_STATUS: DocRefreshStatus = {
  documentId: "doc-1",
  cadence: "daily",
  status: "ok",
  lastRunAt: "2026-05-01T08:00:00Z",
  nextRunAt: "2026-05-02T08:00:00Z",
  runCount: 3,
  error: null,
};

const opts: KbHelperOptions = {
  baseUrl: "https://api.example.com",
  token: "tok",
  fetcher: makeFetcher(FIXTURE_STATUS) as typeof fetch,
};

// ---------------------------------------------------------------------------
// 1. getDocRefreshStatus
// ---------------------------------------------------------------------------

describe("getDocRefreshStatus", () => {
  it("returns fixture when no baseUrl", async () => {
    const result = await getDocRefreshStatus("agent-1", "doc-fixture");
    expect(result.documentId).toBe("doc-fixture");
    expect(result.cadence).toBe("daily");
    expect(["pending", "running", "ok", "error"]).toContain(result.status);
  });

  it("calls GET /kb/documents/:id/refresh with auth header", async () => {
    const fetcher = makeFetcher(FIXTURE_STATUS);
    const o: KbHelperOptions = { baseUrl: "https://api.example.com", token: "t", fetcher: fetcher as typeof fetch };
    const result = await getDocRefreshStatus("agent-1", "doc-1", o);
    expect(fetcher).toHaveBeenCalledOnce();
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/kb/documents/doc-1/refresh");
    expect((init.headers as Record<string, string>)["authorization"]).toBe("Bearer t");
    expect(result.runCount).toBe(3);
  });

  it("throws on non-ok response", async () => {
    const fetcher = makeFetcher({}, false);
    const o: KbHelperOptions = { baseUrl: "https://api.example.com", fetcher: fetcher as typeof fetch };
    await expect(getDocRefreshStatus("a", "d", o)).rejects.toThrow("500");
  });
});

// ---------------------------------------------------------------------------
// 2. setDocRefreshCadence
// ---------------------------------------------------------------------------

describe("setDocRefreshCadence", () => {
  it("PATCHes cadence and returns updated status", async () => {
    const updated = { ...FIXTURE_STATUS, cadence: "weekly" } as DocRefreshStatus;
    const fetcher = makeFetcher(updated);
    const o: KbHelperOptions = { baseUrl: "https://api.example.com", token: "t", fetcher: fetcher as typeof fetch };
    const result = await setDocRefreshCadence("agent-1", "doc-1", "weekly", o);
    expect(result.cadence).toBe("weekly");
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/kb/documents/doc-1/refresh");
    expect((init as RequestInit).method).toBe("PATCH");
  });

  it("updates fixture in-memory cadence without baseUrl", async () => {
    const first = await getDocRefreshStatus("agent-1", "doc-cadence-test");
    expect(first.cadence).toBe("daily");
    const updated = await setDocRefreshCadence("agent-1", "doc-cadence-test", "hourly");
    expect(updated.cadence).toBe("hourly");
    const refetch = await getDocRefreshStatus("agent-1", "doc-cadence-test");
    expect(refetch.cadence).toBe("hourly");
  });
});

// ---------------------------------------------------------------------------
// 3. triggerDocRefresh
// ---------------------------------------------------------------------------

describe("triggerDocRefresh", () => {
  it("POSTs to /kb/documents/:id/refresh", async () => {
    const running = { ...FIXTURE_STATUS, status: "running" } as DocRefreshStatus;
    const fetcher = makeFetcher(running);
    const o: KbHelperOptions = { baseUrl: "https://api.example.com", token: "t", fetcher: fetcher as typeof fetch };
    const result = await triggerDocRefresh("agent-1", "doc-1", o);
    expect(result.status).toBe("running");
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/kb/documents/doc-1/refresh");
    expect((init as RequestInit).method).toBe("POST");
  });

  it("fixture trigger increments runCount", async () => {
    const before = await getDocRefreshStatus("agent-1", "doc-trigger-test");
    const before_count = before.runCount;
    const result = await triggerDocRefresh("agent-1", "doc-trigger-test");
    expect(result.runCount).toBe(before_count + 1);
    expect(result.status).toBe("running");
  });
});

// ---------------------------------------------------------------------------
// 4. REFRESH_CADENCE_LABELS
// ---------------------------------------------------------------------------

describe("REFRESH_CADENCE_LABELS", () => {
  it("has labels for all four cadences", () => {
    expect(Object.keys(REFRESH_CADENCE_LABELS)).toEqual(
      expect.arrayContaining(["manual", "hourly", "daily", "weekly"]),
    );
  });
});

// ---------------------------------------------------------------------------
// 5. KbRefreshPanel component
// ---------------------------------------------------------------------------

describe("KbRefreshPanel", () => {
  const agentId = "agent-panel";
  const documentId = "doc-panel";

  function makeOpts(status: DocRefreshStatus = FIXTURE_STATUS): KbHelperOptions {
    return {
      baseUrl: "https://api.example.com",
      token: "tok",
      fetcher: makeFetcher(status) as typeof fetch,
    };
  }

  it("shows loading state initially then renders status", async () => {
    render(<KbRefreshPanel agentId={agentId} documentId={documentId} opts={makeOpts()} />);
    // eventually shows badge
    await waitFor(() => {
      expect(screen.getByTestId("kb-refresh-panel")).toBeInTheDocument();
    });
    expect(screen.getByTestId("kb-refresh-status-badge")).toHaveTextContent("ok");
  });

  it("shows run count and last/next timestamps", async () => {
    render(<KbRefreshPanel agentId={agentId} documentId={documentId} opts={makeOpts()} />);
    await waitFor(() => screen.getByTestId("kb-refresh-panel"));
    expect(screen.getByTestId("kb-refresh-run-count")).toHaveTextContent("3");
    expect(screen.getByTestId("kb-refresh-last-run")).toBeTruthy();
    expect(screen.getByTestId("kb-refresh-next-run")).toBeTruthy();
  });

  it("cadence select shows current cadence", async () => {
    render(<KbRefreshPanel agentId={agentId} documentId={documentId} opts={makeOpts()} />);
    await waitFor(() => screen.getByTestId("kb-refresh-panel"));
    const select = screen.getByTestId("kb-refresh-cadence-select") as HTMLSelectElement;
    expect(select.value).toBe("daily");
  });

  it("changing cadence calls PATCH and updates select", async () => {
    const patchResult = { ...FIXTURE_STATUS, cadence: "weekly" } as DocRefreshStatus;
    let callCount = 0;
    const fetcher = vi.fn().mockImplementation(() => {
      callCount++;
      return Promise.resolve({ ok: true, status: 200, json: async () => (callCount === 1 ? FIXTURE_STATUS : patchResult) });
    });
    const o: KbHelperOptions = { baseUrl: "https://api.example.com", fetcher: fetcher as typeof fetch };

    render(<KbRefreshPanel agentId={agentId} documentId={documentId} opts={o} />);
    await waitFor(() => screen.getByTestId("kb-refresh-panel"));

    await act(async () => {
      fireEvent.change(screen.getByTestId("kb-refresh-cadence-select"), {
        target: { value: "weekly" },
      });
    });

    await waitFor(() => {
      const select = screen.getByTestId("kb-refresh-cadence-select") as HTMLSelectElement;
      expect(select.value).toBe("weekly");
    });
  });

  it("Refresh now button triggers POST and shows running badge", async () => {
    const runningStatus = { ...FIXTURE_STATUS, status: "running" } as DocRefreshStatus;
    let callCount = 0;
    const fetcher = vi.fn().mockImplementation(() => {
      callCount++;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => (callCount === 1 ? FIXTURE_STATUS : runningStatus),
      });
    });
    const o: KbHelperOptions = { baseUrl: "https://api.example.com", fetcher: fetcher as typeof fetch };

    render(<KbRefreshPanel agentId={agentId} documentId={documentId} opts={o} />);
    await waitFor(() => screen.getByTestId("kb-refresh-panel"));

    await act(async () => {
      fireEvent.click(screen.getByTestId("kb-refresh-trigger-btn"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("kb-refresh-status-badge")).toHaveTextContent("running");
    });
  });

  it("trigger button is disabled when status is running", async () => {
    const runningStatus = { ...FIXTURE_STATUS, status: "running" } as DocRefreshStatus;
    render(<KbRefreshPanel agentId={agentId} documentId={documentId} opts={makeOpts(runningStatus)} />);
    await waitFor(() => screen.getByTestId("kb-refresh-panel"));
    expect(screen.getByTestId("kb-refresh-trigger-btn")).toBeDisabled();
  });

  it("shows error message from status.error field", async () => {
    const errStatus = { ...FIXTURE_STATUS, status: "error", error: "ingest failed" } as DocRefreshStatus;
    render(<KbRefreshPanel agentId={agentId} documentId={documentId} opts={makeOpts(errStatus)} />);
    await waitFor(() => screen.getByTestId("kb-refresh-panel"));
    expect(screen.getByTestId("kb-refresh-error-msg")).toHaveTextContent("ingest failed");
  });
});
