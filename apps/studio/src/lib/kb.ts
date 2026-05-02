/**
 * Knowledge-base helpers for the agent "Knowledge" tab.
 *
 * The cp-api endpoints
 *   - ``GET /v1/agents/{id}/kb/documents``
 *   - ``POST /v1/agents/{id}/kb/documents``  (multipart/form-data)
 *   - ``DELETE /v1/agents/{id}/kb/documents/{doc_id}``
 * are mirrored here. When no cp-api base URL is configured the helpers
 * fall back to in-memory fixtures so the UX is still demo-able.
 *
 * Upload uses XHR so we can surface a real progress percentage; a
 * pluggable ``uploader`` keeps the unit tests deterministic.
 */

export interface KbDocument {
  id: string;
  agentId: string;
  name: string;
  /** MIME type as reported by the upload (text/markdown, application/pdf, …). */
  contentType: string;
  /** Size in bytes. */
  bytes: number;
  /** Indexing pipeline state. */
  status: "indexing" | "ready" | "error";
  uploadedAt: string;
}

export interface KbHelperOptions {
  fetcher?: typeof fetch;
  baseUrl?: string;
  token?: string;
}

function resolveBase(opts: KbHelperOptions): string | null {
  const raw =
    opts.baseUrl ??
    (typeof process !== "undefined"
      ? process.env.LOOP_CP_API_BASE_URL ??
        process.env.NEXT_PUBLIC_LOOP_API_URL
      : undefined);
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function authHeaders(opts: KbHelperOptions): Record<string, string> {
  const headers: Record<string, string> = { accept: "application/json" };
  if (opts.token) headers.authorization = `Bearer ${opts.token}`;
  return headers;
}

const FIXTURE_DOCS: Record<string, KbDocument[]> = {};

function fixtureFor(agentId: string): KbDocument[] {
  if (!FIXTURE_DOCS[agentId]) {
    FIXTURE_DOCS[agentId] = [
      {
        id: "doc_seed_handbook",
        agentId,
        name: "support_handbook.md",
        contentType: "text/markdown",
        bytes: 12_345,
        status: "ready",
        uploadedAt: "2026-04-01T12:00:00Z",
      },
    ];
  }
  return FIXTURE_DOCS[agentId]!;
}

export async function listKbDocuments(
  agentId: string,
  opts: KbHelperOptions = {},
): Promise<{ items: KbDocument[] }> {
  const base = resolveBase(opts);
  if (!base) return { items: [...fixtureFor(agentId)] };
  const f = opts.fetcher ?? fetch;
  const response = await f(
    `${base}/agents/${encodeURIComponent(agentId)}/kb/documents`,
    { headers: authHeaders(opts) },
  );
  if (!response.ok) {
    throw new Error(
      `cp-api GET /agents/${agentId}/kb/documents -> ${response.status}`,
    );
  }
  return (await response.json()) as { items: KbDocument[] };
}

export interface DeleteKbDocumentInput {
  agentId: string;
  documentId: string;
}

export async function deleteKbDocument(
  input: DeleteKbDocumentInput,
  opts: KbHelperOptions = {},
): Promise<{ documentId: string }> {
  const base = resolveBase(opts);
  if (!base) {
    const docs = fixtureFor(input.agentId);
    const idx = docs.findIndex((d) => d.id === input.documentId);
    if (idx >= 0) docs.splice(idx, 1);
    return { documentId: input.documentId };
  }
  const f = opts.fetcher ?? fetch;
  const response = await f(
    `${base}/agents/${encodeURIComponent(input.agentId)}/kb/documents/${encodeURIComponent(input.documentId)}`,
    { method: "DELETE", headers: authHeaders(opts) },
  );
  if (!response.ok) {
    throw new Error(
      `cp-api DELETE /kb/documents/${input.documentId} -> ${response.status}`,
    );
  }
  return { documentId: input.documentId };
}

export interface UploadKbDocumentInput {
  agentId: string;
  file: File;
  /** Called repeatedly with a 0..1 progress ratio. */
  onProgress?: (ratio: number) => void;
  signal?: AbortSignal;
}

export interface UploadKbDocumentOptions extends KbHelperOptions {
  /** Override XHR for tests; receives the same input + opts. */
  uploader?: UploaderFn;
}

export type UploaderFn = (
  url: string,
  input: UploadKbDocumentInput,
  headers: Record<string, string>,
) => Promise<KbDocument>;

const xhrUploader: UploaderFn = (url, input, headers) =>
  new Promise<KbDocument>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    for (const [k, v] of Object.entries(headers)) xhr.setRequestHeader(k, v);
    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      input.onProgress?.(Math.min(1, e.loaded / Math.max(1, e.total)));
    };
    xhr.onerror = () => reject(new Error("network error"));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as KbDocument);
        } catch (err) {
          reject(err as Error);
        }
      } else {
        reject(new Error(`upload -> ${xhr.status}`));
      }
    };
    if (input.signal) {
      input.signal.addEventListener(
        "abort",
        () => xhr.abort(),
        { once: true },
      );
    }
    const form = new FormData();
    form.append("file", input.file, input.file.name);
    xhr.send(form);
  });

export async function uploadKbDocument(
  input: UploadKbDocumentInput,
  opts: UploadKbDocumentOptions = {},
): Promise<KbDocument> {
  const base = resolveBase(opts);
  if (!base) {
    // Fixture path: simulate 0→100 progress and append to the in-memory list.
    for (const ratio of [0.1, 0.4, 0.8, 1.0]) {
      input.onProgress?.(ratio);
      await new Promise((r) => setTimeout(r, 1));
    }
    const doc: KbDocument = {
      id: `doc_${Math.random().toString(36).slice(2, 10)}`,
      agentId: input.agentId,
      name: input.file.name,
      contentType: input.file.type || "application/octet-stream",
      bytes: input.file.size,
      status: "indexing",
      uploadedAt: new Date().toISOString(),
    };
    fixtureFor(input.agentId).push(doc);
    return doc;
  }
  const url = `${base}/agents/${encodeURIComponent(input.agentId)}/kb/documents`;
  const headers = authHeaders(opts);
  const uploader = opts.uploader ?? xhrUploader;
  return uploader(url, input, headers);
}

// ---------------------------------------------------------------------------
// S494: per-doc scheduled refresh cadence + on-demand trigger
// ---------------------------------------------------------------------------

/** How often a document should be refreshed. "manual" means no schedule. */
export type RefreshCadence = "manual" | "hourly" | "daily" | "weekly";

export const REFRESH_CADENCE_LABELS: Record<RefreshCadence, string> = {
  manual: "Manual only",
  hourly: "Every hour",
  daily: "Every 24 h",
  weekly: "Every 7 days",
};

/** Live status of the last / current refresh run for one document. */
export type DocRefreshStatusKind = "pending" | "running" | "ok" | "error";

export interface DocRefreshStatus {
  documentId: string;
  cadence: RefreshCadence;
  status: DocRefreshStatusKind;
  lastRunAt: string | null;   // ISO-8601 or null
  nextRunAt: string | null;   // ISO-8601 or null
  runCount: number;
  error: string | null;
}

// In-memory fixture store so the UI is demo-able without a live API.
const FIXTURE_REFRESH: Record<string, DocRefreshStatus> = {};

function fixtureRefreshFor(documentId: string): DocRefreshStatus {
  if (!FIXTURE_REFRESH[documentId]) {
    FIXTURE_REFRESH[documentId] = {
      documentId,
      cadence: "daily",
      status: "ok",
      lastRunAt: "2026-05-01T08:00:00Z",
      nextRunAt: "2026-05-02T08:00:00Z",
      runCount: 1,
      error: null,
    };
  }
  return FIXTURE_REFRESH[documentId]!;
}

export async function getDocRefreshStatus(
  _agentId: string,
  documentId: string,
  opts: KbHelperOptions = {},
): Promise<DocRefreshStatus> {
  const base = resolveBase(opts);
  if (!base) return { ...fixtureRefreshFor(documentId) };
  const f = opts.fetcher ?? fetch;
  const res = await f(
    `${base}/kb/documents/${encodeURIComponent(documentId)}/refresh`,
    { headers: authHeaders(opts) },
  );
  if (!res.ok) throw new Error(`GET refresh status -> ${res.status}`);
  return (await res.json()) as DocRefreshStatus;
}

export async function setDocRefreshCadence(
  _agentId: string,
  documentId: string,
  cadence: RefreshCadence,
  opts: KbHelperOptions = {},
): Promise<DocRefreshStatus> {
  const base = resolveBase(opts);
  if (!base) {
    const rec = fixtureRefreshFor(documentId);
    rec.cadence = cadence;
    return { ...rec };
  }
  const f = opts.fetcher ?? fetch;
  const res = await f(
    `${base}/kb/documents/${encodeURIComponent(documentId)}/refresh`,
    {
      method: "PATCH",
      headers: { ...authHeaders(opts), "content-type": "application/json" },
      body: JSON.stringify({ cadence }),
    },
  );
  if (!res.ok) throw new Error(`PATCH refresh cadence -> ${res.status}`);
  return (await res.json()) as DocRefreshStatus;
}

export async function triggerDocRefresh(
  _agentId: string,
  documentId: string,
  opts: KbHelperOptions = {},
): Promise<DocRefreshStatus> {
  const base = resolveBase(opts);
  if (!base) {
    const rec = fixtureRefreshFor(documentId);
    rec.status = "running";
    rec.lastRunAt = new Date().toISOString();
    rec.runCount += 1;
    // Simulate completion asynchronously in fixture mode.
    setTimeout(() => {
      rec.status = "ok";
      rec.error = null;
    }, 100);
    return { ...rec };
  }
  const f = opts.fetcher ?? fetch;
  const res = await f(
    `${base}/kb/documents/${encodeURIComponent(documentId)}/refresh`,
    {
      method: "POST",
      headers: authHeaders(opts),
    },
  );
  if (!res.ok) throw new Error(`POST trigger refresh -> ${res.status}`);
  return (await res.json()) as DocRefreshStatus;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
