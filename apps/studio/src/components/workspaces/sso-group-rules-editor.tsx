"use client";

/**
 * S617: SAML group → workspace role mapping editor.
 *
 * Renders an editable table of (group_name → role) rules that the
 * cp-api persists in ``workspace_sso_group_rules`` and the SAML ACS
 * handler consumes via ``load_group_rules`` to build the
 * ``SamlSpConfig.group_role_map`` tuple.
 *
 * The component is pure UI — the parent page owns the cp-api client
 * and provides ``onUpsert`` / ``onDelete`` handlers. Tests can drive
 * the full CRUD flow with simple ``vi.fn()`` spies.
 */

import { useState } from "react";

export type WorkspaceRole =
  | "owner"
  | "admin"
  | "editor"
  | "operator"
  | "viewer";

export const WORKSPACE_ROLES: readonly WorkspaceRole[] = [
  "owner",
  "admin",
  "editor",
  "operator",
  "viewer",
] as const;

export interface SsoGroupRule {
  groupName: string;
  role: WorkspaceRole;
}

export interface SsoGroupRulesEditorProps {
  rules: readonly SsoGroupRule[];
  onUpsert: (rule: SsoGroupRule) => Promise<void> | void;
  onDelete: (groupName: string) => Promise<void> | void;
  /** Optional error from the parent (e.g. cp-api 4xx). */
  errorMessage?: string;
}

export function SsoGroupRulesEditor({
  rules,
  onUpsert,
  onDelete,
  errorMessage,
}: SsoGroupRulesEditorProps) {
  const [groupName, setGroupName] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("viewer");
  const [localError, setLocalError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  return (
    <section
      data-testid="sso-group-rules"
      className="flex flex-col gap-4 rounded-md border p-4"
    >
      <header className="flex flex-col gap-1">
        <h2 className="text-sm font-semibold">SAML group → workspace role</h2>
        <p className="text-xs text-muted-foreground" role="note">
          Map IdP group names (Okta, Entra ID, or Google Workspace) to Loop
          workspace roles. Highest-privilege match wins; unmapped users get the
          workspace default role.
        </p>
      </header>

      <table data-testid="sso-group-rules-table" className="text-sm">
        <thead>
          <tr className="text-left text-xs uppercase text-muted-foreground">
            <th className="px-2 py-1">Group</th>
            <th className="px-2 py-1">Role</th>
            <th className="px-2 py-1" aria-label="actions"></th>
          </tr>
        </thead>
        <tbody>
          {rules.length === 0 && (
            <tr data-testid="sso-group-rules-empty">
              <td className="px-2 py-2 text-xs text-muted-foreground" colSpan={3}>
                No mapping rules yet. Add one below.
              </td>
            </tr>
          )}
          {rules.map((rule) => (
            <tr
              key={rule.groupName}
              data-testid={`sso-group-rule-${rule.groupName}`}
            >
              <td className="px-2 py-1 font-mono">{rule.groupName}</td>
              <td className="px-2 py-1 capitalize">{rule.role}</td>
              <td className="px-2 py-1">
                <button
                  type="button"
                  data-testid={`sso-group-rule-delete-${rule.groupName}`}
                  className="text-xs text-red-600 hover:underline"
                  onClick={() => void onDelete(rule.groupName)}
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form
        data-testid="sso-group-rules-form"
        className="flex flex-wrap items-end gap-2"
        onSubmit={async (event) => {
          event.preventDefault();
          const trimmed = groupName.trim();
          if (!trimmed) {
            setLocalError("Group name is required.");
            return;
          }
          setLocalError(null);
          setSubmitting(true);
          try {
            await onUpsert({ groupName: trimmed, role });
            setGroupName("");
            setRole("viewer");
          } finally {
            setSubmitting(false);
          }
        }}
      >
        <label className="flex flex-col gap-1 text-xs">
          <span>Group name</span>
          <input
            data-testid="sso-group-rules-name"
            className="rounded-md border bg-background px-2 py-1 text-sm"
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
            placeholder="loop-admins"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span>Role</span>
          <select
            data-testid="sso-group-rules-role"
            className="rounded-md border bg-background px-2 py-1 text-sm"
            value={role}
            onChange={(e) => setRole(e.target.value as WorkspaceRole)}
          >
            {WORKSPACE_ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          data-testid="sso-group-rules-submit"
          disabled={submitting}
          className="rounded-md border bg-primary px-3 py-1 text-sm text-primary-foreground disabled:opacity-50"
        >
          {submitting ? "Saving…" : "Add rule"}
        </button>
      </form>

      {(localError || errorMessage) && (
        <p
          data-testid="sso-group-rules-error"
          className="text-sm text-red-600"
          role="alert"
        >
          {localError ?? errorMessage}
        </p>
      )}
    </section>
  );
}
