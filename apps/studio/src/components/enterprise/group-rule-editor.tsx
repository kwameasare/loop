"use client";

/**
 * GroupRuleEditor — editable table of SAML group → workspace role mappings
 * (S617).
 *
 * Renders the current rule set as a table with:
 *   - one row per rule (group text input + role dropdown)
 *   - an "Add rule" button to append a blank row
 *   - a "Remove" button per row
 *   - a "Save" button that calls ``onSave`` with the current rows
 *
 * data-testid hierarchy:
 *   group-rule-editor               — root container
 *   group-rule-row-{i}              — each rule row (0-based)
 *   group-rule-group-input-{i}      — group text input for row i
 *   group-rule-role-select-{i}      — role <select> for row i
 *   group-rule-remove-{i}           — remove button for row i
 *   group-rule-add                  — "Add rule" button
 *   group-rule-save                 — "Save" button
 *   group-rule-error                — error message (when present)
 *   group-rule-success              — success message (when present)
 */

import { useState } from "react";

import {
  type GroupRuleRow,
  WORKSPACE_ROLES,
  type WorkspaceRole,
} from "@/lib/enterprise";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface GroupRuleEditorProps {
  /** Initial rule set to display. */
  initialRules?: GroupRuleRow[];
  /**
   * Called when the user clicks "Save".  Receives the current (validated)
   * rule set.  Should return a promise; the editor shows a saving state
   * while it resolves.
   */
  onSave: (rules: GroupRuleRow[]) => Promise<void>;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function GroupRuleEditor({
  initialRules = [],
  onSave,
}: GroupRuleEditorProps) {
  const [rows, setRows] = useState<GroupRuleRow[]>(initialRules);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Row mutation helpers
  const addRow = () => {
    setRows((prev) => [...prev, { group: "", role: "viewer" }]);
    setError(null);
    setSuccess(false);
  };

  const removeRow = (index: number) => {
    setRows((prev) => prev.filter((_, i) => i !== index));
    setError(null);
    setSuccess(false);
  };

  const updateGroup = (index: number, value: string) => {
    setRows((prev) =>
      prev.map((row, i) => (i === index ? { ...row, group: value } : row)),
    );
    setError(null);
    setSuccess(false);
  };

  const updateRole = (index: number, value: WorkspaceRole) => {
    setRows((prev) =>
      prev.map((row, i) => (i === index ? { ...row, role: value } : row)),
    );
    setError(null);
    setSuccess(false);
  };

  // Validation
  const validate = (): string | null => {
    for (const row of rows) {
      if (!row.group.trim()) {
        return "All group names must be non-empty.";
      }
    }
    const groups = rows.map((r) => r.group.trim());
    if (new Set(groups).size !== groups.length) {
      return "Duplicate group names are not allowed.";
    }
    return null;
  };

  const handleSave = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      await onSave(rows.map((r) => ({ ...r, group: r.group.trim() })));
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div data-testid="group-rule-editor" className="space-y-4">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="pb-2 pr-4 font-medium">IdP group</th>
            <th className="pb-2 pr-4 font-medium">Workspace role</th>
            <th className="pb-2 font-medium sr-only">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              data-testid={`group-rule-row-${i}`}
              className="border-b last:border-0"
            >
              <td className="py-2 pr-4">
                <input
                  data-testid={`group-rule-group-input-${i}`}
                  type="text"
                  value={row.group}
                  onChange={(e) => updateGroup(i, e.target.value)}
                  placeholder="e.g. admins"
                  className="w-full rounded border px-2 py-1 text-sm"
                  aria-label={`Group name for rule ${i + 1}`}
                />
              </td>
              <td className="py-2 pr-4">
                <select
                  data-testid={`group-rule-role-select-${i}`}
                  value={row.role}
                  onChange={(e) =>
                    updateRole(i, e.target.value as WorkspaceRole)
                  }
                  className="rounded border px-2 py-1 text-sm"
                  aria-label={`Role for rule ${i + 1}`}
                >
                  {WORKSPACE_ROLES.map((role) => (
                    <option key={role} value={role}>
                      {role.charAt(0).toUpperCase() + role.slice(1)}
                    </option>
                  ))}
                </select>
              </td>
              <td className="py-2">
                <button
                  data-testid={`group-rule-remove-${i}`}
                  type="button"
                  onClick={() => removeRow(i)}
                  className="text-destructive hover:underline text-sm"
                  aria-label={`Remove rule ${i + 1}`}
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex items-center gap-3">
        <button
          data-testid="group-rule-add"
          type="button"
          onClick={addRow}
          className="rounded border px-3 py-1.5 text-sm hover:bg-muted"
        >
          + Add rule
        </button>

        <button
          data-testid="group-rule-save"
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>

      {error && (
        <p
          data-testid="group-rule-error"
          role="alert"
          className="text-sm text-destructive"
        >
          {error}
        </p>
      )}

      {success && (
        <p
          data-testid="group-rule-success"
          role="status"
          className="text-sm text-green-600"
        >
          Group rules saved.
        </p>
      )}
    </div>
  );
}
