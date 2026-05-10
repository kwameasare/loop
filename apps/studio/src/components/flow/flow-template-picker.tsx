"use client";

import { useState } from "react";

import { FLOW_TEMPLATES, type FlowTemplate } from "@/lib/flow-templates";

export interface FlowTemplatePickerProps {
  /** Called when the user selects a template and clicks "Use template". */
  onSelect: (template: FlowTemplate) => void;
  /** Called when the user dismisses the picker without selecting. */
  onDismiss: () => void;
}

export function FlowTemplatePicker({
  onSelect,
  onDismiss,
}: FlowTemplatePickerProps) {
  const [selected, setSelected] = useState<string | null>(null);

  function handleApply() {
    const tpl = FLOW_TEMPLATES.find((t) => t.id === selected);
    if (!tpl) return;
    onSelect(tpl);
  }

  return (
    <div
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      data-testid="flow-template-picker"
      role="dialog"
    >
      <div className="flex w-[640px] flex-col gap-4 rounded-xl border bg-card p-6 shadow-xl">
        <header className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">New agent from template</h2>
          <button
            aria-label="Close"
            className="rounded p-1 hover:bg-muted"
            data-testid="flow-template-close"
            onClick={onDismiss}
            type="button"
          >
            ✕
          </button>
        </header>

        <p className="text-sm text-muted-foreground">
          Pick a starter flow. You can customise it after loading.
        </p>

        <ul className="flex flex-col gap-3" role="listbox">
          {FLOW_TEMPLATES.map((tpl) => {
            const isSelected = selected === tpl.id;
            return (
              <li
                aria-selected={isSelected}
                className={`cursor-pointer rounded-lg border p-4 transition-colors hover:bg-muted ${
                  isSelected ? "border-info bg-info/10" : ""
                }`}
                data-testid={`flow-template-card-${tpl.id}`}
                key={tpl.id}
                onClick={() => setSelected(tpl.id)}
                role="option"
              >
                <p className="font-medium">{tpl.name}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {tpl.description}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {tpl.nodes.length} nodes · {tpl.edges.length} edges
                </p>
              </li>
            );
          })}
        </ul>

        <footer className="flex justify-end gap-2 pt-2">
          <button
            className="rounded border bg-background px-4 py-2 text-sm hover:bg-muted"
            data-testid="flow-template-cancel"
            onClick={onDismiss}
            type="button"
          >
            Cancel
          </button>
          <button
            className="rounded bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
            data-testid="flow-template-apply"
            disabled={!selected}
            onClick={handleApply}
            type="button"
          >
            Use template
          </button>
        </footer>
      </div>
    </div>
  );
}
