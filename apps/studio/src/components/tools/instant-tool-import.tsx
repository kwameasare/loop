"use client";

import { useState } from "react";
import { Code2, LibraryBig } from "lucide-react";

import {
  DEFAULT_TOOL_IMPORT,
  draftToolFromRequest,
  type ToolDraft,
  type ToolDraftSource,
} from "@/lib/agent-tools";
import { cpJson } from "@/lib/ux-wireup";
import { cn } from "@/lib/utils";

const SOURCES: { id: ToolDraftSource; label: string; helper: string }[] = [
  {
    id: "curl",
    label: "cURL",
    helper: "Paste a curl command copied from docs or terminal.",
  },
  {
    id: "openapi",
    label: "OpenAPI",
    helper: "Paste an OpenAPI operation or URL.",
  },
  {
    id: "postman",
    label: "Postman",
    helper: "Paste a Postman export sample.",
  },
  {
    id: "devtools",
    label: "DevTools",
    helper: "Paste browser DevTools Copy as fetch.",
  },
];

export function InstantToolImport({ agentId }: { agentId: string }) {
  const [source, setSource] = useState<ToolDraftSource>("curl");
  const [input, setInput] = useState(DEFAULT_TOOL_IMPORT);
  const [draft, setDraft] = useState<ToolDraft | null>(null);
  const [liveImportId, setLiveImportId] = useState<string | null>(null);
  const [added, setAdded] = useState(false);

  async function draftLiveTool() {
    setAdded(false);
    setDraft(draftToolFromRequest(input, source));
    const result = await cpJson<{ tool_id: string }>(
      `/agents/${encodeURIComponent(agentId)}/tools/import`,
      {
        method: "POST",
        body: { source: input, source_kind: source },
        fallback: { tool_id: "tool_local_import" },
      },
    );
    setLiveImportId(result.tool_id);
  }

  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      data-testid="tools-room-import"
      aria-labelledby="tools-import-heading"
    >
      <div className="flex flex-col gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Instant tool
          </p>
          <h3 className="mt-1 text-sm font-semibold" id="tools-import-heading">
            Draft from cURL, OpenAPI, Postman, or DevTools.
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Studio generates a typed MCP tool draft, auth needs, safety contract,
            mock response, and eval stub before any production grant exists.
          </p>
        </div>
        <div className="grid gap-2 [grid-template-columns:repeat(auto-fit,minmax(min(100%,7rem),1fr))]">
          {SOURCES.map((item) => (
            <button
              key={item.id}
              type="button"
              className={cn(
                "rounded-md border px-3 py-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                source === item.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-background",
              )}
              aria-pressed={source === item.id}
              onClick={() => setSource(item.id)}
              data-testid={`tools-room-source-${item.id}`}
              title={item.helper}
            >
              {item.label}
            </button>
          ))}
        </div>
        <textarea
          className="min-h-36 rounded-md border bg-background p-3 font-mono text-xs leading-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          aria-label="Tool request input"
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            onClick={() => void draftLiveTool()}
            data-testid="tools-room-draft-tool"
          >
            <Code2 className="h-4 w-4" aria-hidden />
            Preview generated tool
          </button>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:opacity-60"
            onClick={() => setAdded(true)}
            disabled={!draft}
            data-testid="tools-room-add-library"
          >
            <LibraryBig className="h-4 w-4" aria-hidden />
            Add to library
          </button>
        </div>
        {draft ? (
          <DraftSummary draft={draft} liveImportId={liveImportId} added={added} />
        ) : null}
      </div>
    </section>
  );
}

function DraftSummary({
  draft,
  liveImportId,
  added,
}: {
  draft: ToolDraft;
  liveImportId: string | null;
  added: boolean;
}) {
  return (
    <div
      className="rounded-md border border-info/40 bg-info/5 p-3"
      data-testid="tools-room-draft"
    >
      <p className="text-sm font-semibold">{draft.name}</p>
      <p className="mt-1 text-sm text-muted-foreground">
        {draft.method} {draft.url}
      </p>
      <div className="mt-3 grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr))]">
        <div>
          <p className="text-xs font-medium text-muted-foreground">Auth</p>
          <p className="text-sm">{draft.authNeeds.join(" ")}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground">
            Side effect
          </p>
          <p className="text-sm">{draft.sideEffect}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground">Boundary</p>
          <p className="text-sm">{draft.productionBoundary}</p>
        </div>
      </div>
      <ul className="mt-3 space-y-1 text-sm">
        {draft.schema.map((field) => (
          <li key={field.name}>
            {field.name}: {field.type}
            {field.sensitive ? " (Vault only)" : ""}
          </li>
        ))}
      </ul>
      <pre className="mt-3 overflow-auto rounded-md bg-background p-3 text-xs">
        <code>{draft.mockResponse}</code>
      </pre>
      <p className="mt-2 text-xs text-muted-foreground">
        Eval stub: {draft.evalStub}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Evidence: {draft.evidence}
      </p>
      {liveImportId ? (
        <p className="mt-1 font-mono text-xs text-muted-foreground">
          Live draft target: {liveImportId}
        </p>
      ) : null}
      {added ? (
        <p className="mt-2 text-xs font-medium text-success" role="status">
          Added to the draft tool library. Production grant still requires
          schema, auth, eval, and approval review.
        </p>
      ) : null}
    </div>
  );
}
