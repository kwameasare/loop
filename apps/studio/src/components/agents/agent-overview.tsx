"use client";

/**
 * S159: Agent overview tab -- description, model, last-deploy summary,
 * and an edit-description modal.
 *
 * The component is deliberately client-side so the edit modal can
 * manage local state without a round-trip. The parent server page
 * passes the serialised agent + deploy summary as props.
 */

import { useState } from "react";

export interface DeploySummary {
  /** ISO 8601 timestamp of the most recent deploy. */
  deployed_at: string | null;
  /** Deployed version number (null if agent has never been deployed). */
  version: number | null;
  /** Deploy status label. */
  status: "active" | "failed" | "pending" | null;
}

export interface AgentOverviewProps {
  id: string;
  name: string;
  description: string;
  /** Model identifier, e.g. "gpt-4o-mini". Empty string if not yet configured. */
  model: string;
  lastDeploy: DeploySummary;
  /** Called when the user saves a new description. Allows integration with server actions. */
  onDescriptionSave?: (newDescription: string) => void;
}

// ---------------------------------------------------------------------------
// Edit-description modal (headless, no external dialog lib)
// ---------------------------------------------------------------------------

interface EditDescriptionModalProps {
  open: boolean;
  initial: string;
  onSave: (value: string) => void;
  onClose: () => void;
}

function EditDescriptionModal({ open, initial, onSave, onClose }: EditDescriptionModalProps) {
  const [value, setValue] = useState(initial);

  if (!open) return null;

  function handleSave() {
    onSave(value.trim());
    onClose();
  }

  return (
    <>
      <div
        aria-hidden="true"
        className="fixed inset-0 bg-black/40 z-40"
        onClick={onClose}
        data-testid="edit-desc-backdrop"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-desc-title"
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        data-testid="edit-desc-modal"
      >
        <div className="flex w-full max-w-md flex-col gap-4 rounded-lg bg-background p-6 shadow-xl">
          <h2 className="text-base font-semibold" id="edit-desc-title">
            Edit description
          </h2>
          <textarea
            rows={4}
            className="w-full rounded border bg-background px-2 py-1 text-sm"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            data-testid="edit-desc-textarea"
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="rounded border px-3 py-1 text-sm hover:bg-muted"
              onClick={onClose}
              data-testid="edit-desc-cancel"
            >
              Cancel
            </button>
            <button
              type="button"
              className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
              onClick={handleSave}
              data-testid="edit-desc-save"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// AgentOverview
// ---------------------------------------------------------------------------

function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

export function AgentOverview({
  description: initialDescription,
  model,
  lastDeploy,
  onDescriptionSave,
}: AgentOverviewProps) {
  const [description, setDescription] = useState(initialDescription);
  const [editOpen, setEditOpen] = useState(false);

  function handleSave(value: string) {
    setDescription(value);
    onDescriptionSave?.(value);
  }

  return (
    <div className="flex flex-col gap-6" data-testid="agent-overview-tab">
      {/* Description */}
      <section aria-labelledby="overview-desc-heading">
        <div className="mb-1 flex items-center gap-2">
          <h3 className="text-sm font-medium" id="overview-desc-heading">
            Description
          </h3>
          <button
            type="button"
            className="rounded px-2 py-0.5 text-xs hover:bg-muted"
            onClick={() => setEditOpen(true)}
            data-testid="overview-edit-desc-button"
          >
            Edit
          </button>
        </div>
        <p
          className="text-sm text-muted-foreground"
          data-testid="overview-description"
        >
          {description || "No description yet."}
        </p>
      </section>

      {/* Model */}
      <section aria-labelledby="overview-model-heading">
        <h3 className="mb-1 text-sm font-medium" id="overview-model-heading">
          Model
        </h3>
        <p className="text-sm text-muted-foreground" data-testid="overview-model">
          {model || "Not configured"}
        </p>
      </section>

      {/* Last deploy */}
      <section aria-labelledby="overview-deploy-heading">
        <h3 className="mb-1 text-sm font-medium" id="overview-deploy-heading">
          Last deploy
        </h3>
        <dl className="flex flex-col gap-1 text-sm" data-testid="overview-last-deploy">
          <div className="flex gap-2">
            <dt className="text-muted-foreground">When</dt>
            <dd data-testid="overview-deploy-time">
              {formatDate(lastDeploy.deployed_at)}
            </dd>
          </div>
          {lastDeploy.version !== null && (
            <div className="flex gap-2">
              <dt className="text-muted-foreground">Version</dt>
              <dd data-testid="overview-deploy-version">v{lastDeploy.version}</dd>
            </div>
          )}
          {lastDeploy.status !== null && (
            <div className="flex gap-2">
              <dt className="text-muted-foreground">Status</dt>
              <dd data-testid="overview-deploy-status">{lastDeploy.status}</dd>
            </div>
          )}
        </dl>
      </section>

      <EditDescriptionModal
        open={editOpen}
        initial={description}
        onSave={handleSave}
        onClose={() => setEditOpen(false)}
      />
    </div>
  );
}
