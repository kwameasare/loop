"use client";

import { useEffect, useId, useRef, useState, type FormEvent } from "react";

import {
  type KbDocument,
  type UploadKbDocumentInput,
  type DeleteKbDocumentInput,
  deleteKbDocument as defaultDelete,
  formatBytes,
  uploadKbDocument as defaultUpload,
  triggerDocRefresh as defaultTriggerRefresh,
} from "@/lib/kb";

type UploadFn = (input: UploadKbDocumentInput) => Promise<KbDocument>;
type DeleteFn = (input: DeleteKbDocumentInput) => Promise<{ documentId: string }>;
type RefreshFn = typeof defaultTriggerRefresh;

export interface KbListProps {
  agentId: string;
  initialDocuments: KbDocument[];
  upload?: UploadFn;
  remove?: DeleteFn;
  triggerRefresh?: RefreshFn;
}

type Toast = { kind: "success" | "error"; message: string } | null;

const DELETE_PHRASE = "DELETE";

/**
 * Knowledge-base management UI for the agent Knowledge tab.
 *
 * The component lists existing documents, opens an upload modal with a
 * live progress bar (driven by the helper's ``onProgress`` callback),
 * and gates deletes behind a typed-confirmation that requires the
 * editor to type the literal phrase ``DELETE``.
 */
export function KbList({
  agentId,
  initialDocuments,
  upload = defaultUpload,
  remove = defaultDelete,
  triggerRefresh = defaultTriggerRefresh,
}: KbListProps) {
  const [docs, setDocs] = useState(initialDocuments);
  const [toast, setToast] = useState<Toast>(null);
  const [refreshingIds, setRefreshingIds] = useState<Set<string>>(new Set());

  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);

  const [confirmDoc, setConfirmDoc] = useState<KbDocument | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const fileLabelId = useId();
  const confirmId = useId();

  useEffect(() => setDocs(initialDocuments), [initialDocuments]);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(t);
  }, [toast]);

  function resetUpload() {
    setUploadFile(null);
    setUploadProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!uploadFile || uploading) return;
    setUploading(true);
    setUploadProgress(0);
    try {
      const doc = await upload({
        agentId,
        file: uploadFile,
        onProgress: (r) => setUploadProgress(Math.round(r * 100)),
      });
      setDocs((prev) => [doc, ...prev]);
      setUploadOpen(false);
      resetUpload();
      setToast({
        kind: "success",
        message: `Uploaded ${doc.name}. Indexing started.`,
      });
    } catch (err) {
      setToast({
        kind: "error",
        message: (err as Error).message ?? "Upload failed.",
      });
    } finally {
      setUploading(false);
    }
  }

  async function handleRefresh(documentId: string) {
    if (refreshingIds.has(documentId)) return;
    setRefreshingIds((prev) => new Set([...prev, documentId]));
    try {
      const status = await triggerRefresh(agentId, documentId);
      setDocs((prev) =>
        prev.map((d) =>
          d.id === documentId
            ? { ...d, lastRefreshedAt: status.lastRunAt }
            : d,
        ),
      );
      setToast({ kind: "success", message: "Refresh triggered." });
    } catch (err) {
      setToast({
        kind: "error",
        message: (err as Error).message ?? "Refresh failed.",
      });
    } finally {
      setRefreshingIds((prev) => {
        const next = new Set(prev);
        next.delete(documentId);
        return next;
      });
    }
  }

  async function handleDelete() {
    if (!confirmDoc || deleting) return;
    if (confirmText !== DELETE_PHRASE) return;
    setDeleting(true);
    try {
      await remove({ agentId, documentId: confirmDoc.id });
      setDocs((prev) => prev.filter((d) => d.id !== confirmDoc.id));
      setToast({
        kind: "success",
        message: `Deleted ${confirmDoc.name}.`,
      });
      setConfirmDoc(null);
      setConfirmText("");
    } catch (err) {
      setToast({
        kind: "error",
        message: (err as Error).message ?? "Delete failed.",
      });
    } finally {
      setDeleting(false);
    }
  }

  const canDelete = confirmText === DELETE_PHRASE && !deleting;

  return (
    <section className="flex flex-col gap-3" data-testid="kb-list">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">Knowledge</h2>
          <p className="text-sm text-muted-foreground">
            Documents indexed for retrieval-augmented answers.
          </p>
        </div>
        <button
          className="rounded bg-gray-900 text-white text-sm px-3 py-1"
          data-testid="kb-upload-open"
          onClick={() => setUploadOpen(true)}
          type="button"
        >
          Upload document
        </button>
      </header>

      {docs.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid="kb-empty">
          No documents yet. Upload a markdown, text, or PDF file to start.
        </p>
      ) : (
        <ul
          className="flex flex-col divide-y border rounded"
          data-testid="kb-doc-list"
        >
          {docs.map((doc) => (
            <li
              key={doc.id}
              className="flex items-center justify-between px-3 py-2 text-sm"
              data-testid={`kb-doc-${doc.id}`}
            >
              <div className="flex flex-col">
                <span className="font-medium">{doc.name}</span>
                <span className="text-xs text-gray-500">
                  {doc.contentType} · {formatBytes(doc.bytes)} ·{" "}
                  <span data-testid={`kb-doc-status-${doc.id}`}>
                    {doc.status}
                  </span>
                  {" · "}
                  <span data-testid={`kb-doc-last-refreshed-${doc.id}`}>
                    {doc.lastRefreshedAt
                      ? `Refreshed ${new Date(doc.lastRefreshedAt).toLocaleString()}`
                      : "Never refreshed"}
                  </span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                  data-testid={`kb-doc-refresh-${doc.id}`}
                  disabled={refreshingIds.has(doc.id)}
                  onClick={() => handleRefresh(doc.id)}
                  type="button"
                >
                  {refreshingIds.has(doc.id) ? "Refreshing…" : "Refresh"}
                </button>
                <button
                  className="text-xs text-red-600 hover:underline"
                  data-testid={`kb-doc-delete-${doc.id}`}
                  onClick={() => {
                    setConfirmDoc(doc);
                    setConfirmText("");
                  }}
                  type="button"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {uploadOpen ? (
        <div
          aria-modal="true"
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
          data-testid="kb-upload-modal"
          role="dialog"
        >
          <form
            className="bg-white rounded p-4 w-[420px] flex flex-col gap-3"
            onSubmit={handleUpload}
          >
            <h3 className="text-sm font-medium">Upload document</h3>
            <label className="text-xs font-medium" htmlFor={fileLabelId}>
              File
            </label>
            <input
              data-testid="kb-upload-file"
              id={fileLabelId}
              onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              ref={fileInputRef}
              type="file"
            />
            {uploading ? (
              <div
                className="h-2 rounded bg-gray-200 overflow-hidden"
                data-testid="kb-upload-progress"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={uploadProgress}
                role="progressbar"
              >
                <div
                  className="h-full bg-emerald-500 transition-[width]"
                  data-testid="kb-upload-progress-fill"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            ) : null}
            <div className="flex justify-end gap-2">
              <button
                className="text-sm px-3 py-1 rounded border"
                data-testid="kb-upload-cancel"
                disabled={uploading}
                onClick={() => {
                  setUploadOpen(false);
                  resetUpload();
                }}
                type="button"
              >
                Cancel
              </button>
              <button
                className="text-sm px-3 py-1 rounded bg-gray-900 text-white disabled:opacity-50"
                data-testid="kb-upload-submit"
                disabled={!uploadFile || uploading}
                type="submit"
              >
                {uploading ? `Uploading ${uploadProgress}%` : "Upload"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {confirmDoc ? (
        <div
          aria-modal="true"
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
          data-testid="kb-delete-modal"
          role="dialog"
        >
          <div className="bg-white rounded p-4 w-[420px] flex flex-col gap-3">
            <h3 className="text-sm font-medium">Delete document?</h3>
            <p className="text-sm">
              Type <code className="font-mono">DELETE</code> to permanently
              remove <strong>{confirmDoc.name}</strong> from the agent&apos;s
              knowledge base.
            </p>
            <input
              autoFocus
              className="border rounded px-2 py-1 text-sm"
              data-testid="kb-delete-confirm"
              id={confirmId}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="DELETE"
              value={confirmText}
            />
            <div className="flex justify-end gap-2">
              <button
                className="text-sm px-3 py-1 rounded border"
                data-testid="kb-delete-cancel"
                onClick={() => {
                  setConfirmDoc(null);
                  setConfirmText("");
                }}
                type="button"
              >
                Cancel
              </button>
              <button
                className="text-sm px-3 py-1 rounded bg-red-600 text-white disabled:opacity-50"
                data-testid="kb-delete-submit"
                disabled={!canDelete}
                onClick={handleDelete}
                type="button"
              >
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {toast ? (
        <p
          className={
            toast.kind === "success"
              ? "text-xs text-emerald-700"
              : "text-xs text-red-600"
          }
          data-testid={`kb-toast-${toast.kind}`}
          role="status"
        >
          {toast.message}
        </p>
      ) : null}
    </section>
  );
}
