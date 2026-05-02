"use client";

import {
  FLOW_NODE_KINDS,
  FLOW_DRAG_MIME,
  type FlowNodeType,
} from "@/lib/flow-nodes";

export interface NodePaletteProps {
  /**
   * Optional handler invoked when a palette item starts being dragged.
   * In production the canvas reads the type via the dataTransfer payload;
   * exposing a callback simplifies tests in jsdom (where dataTransfer is
   * not always populated faithfully).
   */
  onDragStart?: (type: FlowNodeType) => void;
}

export function NodePalette(props: NodePaletteProps) {
  return (
    <aside
      aria-label="Flow node palette"
      className="flex w-48 flex-col gap-2 border-r bg-white p-3"
      data-testid="flow-palette"
    >
      <h3 className="text-xs font-semibold uppercase text-zinc-500">
        Nodes
      </h3>
      {FLOW_NODE_KINDS.map((kind) => (
        <button
          aria-label={`Add ${kind.label} node`}
          className="flex items-center gap-2 rounded border px-2 py-2 text-left text-sm hover:bg-zinc-50"
          data-testid={`palette-item-${kind.type}`}
          draggable
          key={kind.type}
          onDragStart={(e) => {
            if (e.dataTransfer) {
              e.dataTransfer.setData(FLOW_DRAG_MIME, kind.type);
              e.dataTransfer.effectAllowed = "copy";
            }
            props.onDragStart?.(kind.type);
          }}
          type="button"
        >
          <span
            aria-hidden
            className={`flex h-7 w-7 items-center justify-center rounded text-base ${kind.color}`}
            data-testid={`palette-icon-${kind.type}`}
          >
            {kind.icon}
          </span>
          <span className="flex flex-col">
            <span className="font-medium">{kind.label}</span>
            <span className="text-[11px] text-zinc-500">
              {kind.description}
            </span>
          </span>
        </button>
      ))}
    </aside>
  );
}
