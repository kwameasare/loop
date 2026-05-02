"use client";

/**
 * S155: Settings drawer -- profile name (editable), region (read-only),
 * and theme selector (persisted to localStorage).
 *
 * Open by calling ``openSettings()`` from anywhere in the tree, or by
 * rendering the ``SettingsButton`` trigger supplied here.
 */

import { useState } from "react";
import { useSettings, type Theme } from "@/lib/use-settings";

// ---------------------------------------------------------------------------
// Minimal headless drawer: no external dialog library required.
// ---------------------------------------------------------------------------

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

function Drawer({ open, onClose, children }: DrawerProps) {
  if (!open) return null;
  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        className="fixed inset-0 bg-black/40 z-40"
        onClick={onClose}
        data-testid="settings-backdrop"
      />
      {/* Panel */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Settings"
        className="fixed inset-y-0 right-0 z-50 flex w-80 flex-col bg-background shadow-xl"
        data-testid="settings-drawer"
      >
        {children}
      </aside>
    </>
  );
}

// ---------------------------------------------------------------------------
// SettingsDrawer
// ---------------------------------------------------------------------------

interface SettingsDrawerProps {
  open: boolean;
  onClose: () => void;
  /** Seed from auth profile; user may override locally. */
  defaultProfileName?: string;
}

const THEME_OPTIONS: { value: Theme; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

export function SettingsDrawer({ open, onClose, defaultProfileName = "" }: SettingsDrawerProps) {
  const { profileName, region, theme, setProfileName, setTheme } =
    useSettings(defaultProfileName);

  const [draft, setDraft] = useState(profileName);

  function handleSaveName() {
    setProfileName(draft.trim() || defaultProfileName);
  }

  return (
    <Drawer open={open} onClose={onClose}>
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="text-base font-semibold" id="settings-title">
          Settings
        </h2>
        <button
          type="button"
          aria-label="Close settings"
          className="rounded p-1 hover:bg-muted"
          onClick={onClose}
          data-testid="settings-close"
        >
          ✕
        </button>
      </div>

      <div className="flex flex-col gap-6 overflow-y-auto p-4">
        {/* Profile */}
        <section aria-labelledby="settings-profile-heading">
          <h3 className="mb-2 text-sm font-medium" id="settings-profile-heading">
            Profile
          </h3>
          <label className="mb-1 block text-xs text-muted-foreground" htmlFor="settings-profile-name">
            Display name
          </label>
          <div className="flex gap-2">
            <input
              id="settings-profile-name"
              type="text"
              className="flex-1 rounded border bg-background px-2 py-1 text-sm"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              data-testid="settings-profile-name-input"
            />
            <button
              type="button"
              className="rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
              onClick={handleSaveName}
              data-testid="settings-profile-name-save"
            >
              Save
            </button>
          </div>
        </section>

        {/* Region (read-only) */}
        <section aria-labelledby="settings-region-heading">
          <h3 className="mb-2 text-sm font-medium" id="settings-region-heading">
            Region
          </h3>
          <p
            className="rounded border bg-muted/40 px-2 py-1 text-sm"
            data-testid="settings-region-display"
          >
            {region}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Workspace region is set at creation and cannot be changed.
          </p>
        </section>

        {/* Theme */}
        <section aria-labelledby="settings-theme-heading">
          <h3 className="mb-2 text-sm font-medium" id="settings-theme-heading">
            Theme
          </h3>
          <div className="flex gap-2" role="group" aria-label="Theme selection">
            {THEME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                aria-pressed={theme === opt.value}
                className={`rounded border px-3 py-1 text-sm transition-colors ${
                  theme === opt.value
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted"
                }`}
                onClick={() => setTheme(opt.value)}
                data-testid={`settings-theme-${opt.value}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </section>
      </div>
    </Drawer>
  );
}

// ---------------------------------------------------------------------------
// Convenience trigger button (used in Topbar / UserMenu)
// ---------------------------------------------------------------------------

interface SettingsButtonProps {
  onClick: () => void;
}

export function SettingsButton({ onClick }: SettingsButtonProps) {
  return (
    <button
      type="button"
      aria-label="Open settings"
      className="rounded p-1 text-sm hover:bg-muted"
      onClick={onClick}
      data-testid="settings-open-button"
    >
      ⚙
    </button>
  );
}
