import { describe, expect, it, vi } from "vitest";
import {
  deleteKbDocument,
  formatBytes,
  listKbDocuments,
  uploadKbDocument,
} from "./kb";
import type { KbDocument, UploaderFn } from "./kb";

describe("kb (fixture mode)", () => {
  it("listKbDocuments returns a seeded handbook", async () => {
    const { items } = await listKbDocuments("agt_fixture_a");
    expect(items.length).toBeGreaterThanOrEqual(1);
    expect(items[0]?.contentType).toBe("text/markdown");
  });

  it("uploadKbDocument streams progress and appends to the list", async () => {
    const file = new File(["hello"], "notes.md", { type: "text/markdown" });
    const ratios: number[] = [];
    const doc = await uploadKbDocument({
      agentId: "agt_fixture_b",
      file,
      onProgress: (r) => ratios.push(r),
    });
    expect(doc.name).toBe("notes.md");
    expect(doc.status).toBe("indexing");
    expect(ratios.at(-1)).toBe(1);
    const { items } = await listKbDocuments("agt_fixture_b");
    expect(items.some((d) => d.id === doc.id)).toBe(true);
  });

  it("deleteKbDocument removes the entry", async () => {
    const file = new File(["x"], "x.txt", { type: "text/plain" });
    const doc = await uploadKbDocument({ agentId: "agt_fixture_c", file });
    await deleteKbDocument({
      agentId: "agt_fixture_c",
      documentId: doc.id,
    });
    const { items } = await listKbDocuments("agt_fixture_c");
    expect(items.some((d) => d.id === doc.id)).toBe(false);
  });
});

describe("kb (cp-api mode)", () => {
  it("listKbDocuments fetches the canonical URL", async () => {
    const fetcher = vi.fn<(
      input: RequestInfo | URL,
      init?: RequestInit,
    ) => Promise<Response>>(async () =>
      new Response(JSON.stringify({ items: [] }), { status: 200 }),
    );
    await listKbDocuments("agt_z", {
      fetcher: fetcher as unknown as typeof fetch,
      baseUrl: "https://api.example.com",
      token: "studio",
    });
    const [url, init] = fetcher.mock.calls[0]!;
    if (!init) throw new Error("missing fetch init");
    expect(String(url)).toBe("https://api.example.com/v1/agents/agt_z/kb/documents");
    const headers = init.headers as Record<string, string>;
    expect(headers.authorization).toBe("Bearer studio");
  });

  it("uploadKbDocument routes through the injected uploader", async () => {
    const file = new File(["abc"], "a.md", { type: "text/markdown" });
    const stub: KbDocument = {
      id: "doc_real",
      agentId: "agt_z",
      name: "a.md",
      contentType: "text/markdown",
      bytes: 3,
      status: "indexing",
      uploadedAt: "2026-05-01T00:00:00Z",
      lastRefreshedAt: null,
    };
    const uploader = vi.fn<UploaderFn>(async () => stub);
    const doc = await uploadKbDocument(
      { agentId: "agt_z", file },
      {
        baseUrl: "https://api.example.com",
        uploader,
        token: "studio",
      },
    );
    expect(doc.id).toBe("doc_real");
    const args = uploader.mock.calls[0] as Parameters<UploaderFn>;
    expect(args[0]).toBe(
      "https://api.example.com/v1/agents/agt_z/kb/documents",
    );
    expect(args[2]?.authorization).toBe("Bearer studio");
  });

  it("deleteKbDocument surfaces non-2xx responses", async () => {
    const fetcher = vi.fn(async () => new Response("", { status: 500 }));
    await expect(
      deleteKbDocument(
        { agentId: "agt_z", documentId: "doc_x" },
        {
          fetcher: fetcher as unknown as typeof fetch,
          baseUrl: "https://api.example.com",
        },
      ),
    ).rejects.toThrow(/500/);
  });
});

describe("formatBytes", () => {
  it("renders B/KB/MB", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(2 * 1024 * 1024)).toBe("2.0 MB");
  });
});
