"use client";

import { useRef, useState } from "react";

import {
  DEFAULT_VIEWPORT,
  MAX_ZOOM,
  MIN_ZOOM,
  pan,
  resetViewport,
  type Viewport,
  zoomAt,
} from "@/lib/flow-canvas";
import {
  FLOW_DRAG_MIME,
  type FlowNode,
  type FlowNodeType,
  getNodeKind,
  nextFlowNodeId,
} from "@/lib/flow-nodes";
import { type AnyNodeConfig } from "@/lib/flow-node-config";

import { NodePalette } from "./node-palette";
import { NodeConfigSidebar } from "./node-config-sidebar";

export interface FlowEditorProps {
  agentId: string;
  initialNodes?: FlowNode[];
  /**
   * Test seam: when set, drag-from-palette uses this type instead of
   * reading from ``DataTransfer`` (jsdom drops the payload silently).
   */
  pendingDragType?: FlowNodeType | null;
}

export function FlowEditor(props: FlowEditorProps) {
  const [viewport, setViewport] = useState<Viewport>(DEFAULT_VIEWPORT);
  const [nodes, setNodes] = useState<FlowNode[]>(props.initialNodes ?? []);
  const [pending, setPending] = useState<FlowNodeType | null>(
    props.pendingDragType ?? null,
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [configs, setConfigs] = useState<Record<string, AnyNodeConfig>>({});
  const dragRef = useRef<{ x: number; y: number } | null>(null);

  function onMouseDown(e: React.MouseEvent) {
    dragRef.current = { x: e.clientX, y: e.clientY };
  }
  function onMouseMove(e: React.MouseEvent) {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.x;
    const dy = e.clientY - dragRef.current.y;
    dragRef.current = { x: e.clientX, y: e.clientY };
    setViewport((v) => pan(v, dx, dy));
  }
  function onMouseUp() {
    dragRef.current = null;
  }
  function onWheel(e: React.WheelEvent) {
    const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    setViewport((v) => zoomAt(v, factor, e.clientX, e.clientY));
  }
  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
  }
  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    const fromPayload = e.dataTransfer
      ? (e.dataTransfer.getData(FLOW_DRAG_MIME) as FlowNodeType)
      : ("" as FlowNodeType);
    const type: FlowNodeType | null =
      (fromPayload as FlowNodeType) || pending;
    if (!type) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;
    // Convert to world coords via current viewport.
    const worldX = (screenX - viewport.x) / viewport.zoom;
    const worldY = (screenY - viewport.y) / viewport.zoom;
    const node: FlowNode = {
      id: nextFlowNodeId(type),
      type,
      x: worldX,
      y: worldY,
    };
    setNodes((prev) => [...prev, node]);
    setPending(null);
  }
  function zoomIn() {
    setViewport((v) => zoomAt(v, 1.2, 0, 0));
  }
  function zoomOut() {
    setViewport((v) => zoomAt(v, 1 / 1.2, 0, 0));
  }
  function reset() {
    setViewport(resetViewport());
  }

  const transform = `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`;
  const zoomPct = Math.round(viewport.zoom * 100);
  const selectedNode = selectedId
    ? nodes.find((n) => n.id === selectedId) ?? null
    : null;

  return (
    <section
      className="flex h-[640px] w-full overflow-hidden rounded-lg border bg-zinc-50"
      data-testid="flow-editor"
    >
      <NodePalette onDragStart={(type) => setPending(type)} />
      <div className="flex flex-1 flex-col">
        <header
          className="flex items-center justify-between border-b bg-white px-4 py-2"
          data-testid="flow-toolbar"
        >
          <span className="font-mono text-xs text-zinc-500">
            agent-id: {props.agentId}
          </span>
          <div className="flex items-center gap-2">
            <button
              aria-label="Zoom out"
              className="rounded border px-2 py-1 text-sm hover:bg-zinc-100 disabled:opacity-40"
              data-testid="flow-zoom-out"
              disabled={viewport.zoom <= MIN_ZOOM + 1e-9}
              onClick={zoomOut}
              type="button"
            >
              −
            </button>
            <span
              className="min-w-[3rem] text-center text-xs"
              data-testid="flow-zoom-pct"
            >
              {zoomPct}%
            </span>
            <button
              aria-label="Zoom in"
              className="rounded border px-2 py-1 text-sm hover:bg-zinc-100 disabled:opacity-40"
              data-testid="flow-zoom-in"
              disabled={viewport.zoom >= MAX_ZOOM - 1e-9}
              onClick={zoomIn}
              type="button"
            >
              +
            </button>
            <button
              className="rounded border px-2 py-1 text-sm hover:bg-zinc-100"
              data-testid="flow-reset"
              onClick={reset}
              type="button"
            >
              Reset
            </button>
          </div>
        </header>
        <div
          aria-label="Flow canvas viewport"
          className="relative flex-1 cursor-grab overflow-hidden active:cursor-grabbing"
          data-testid="flow-viewport"
          onDragOver={onDragOver}
          onDrop={onDrop}
          onMouseDown={onMouseDown}
          onMouseLeave={onMouseUp}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onWheel={onWheel}
          role="application"
        >
          <div
            className="absolute inset-0"
            data-testid="flow-world"
            style={{
              transform,
              transformOrigin: "0 0",
              backgroundImage:
                "radial-gradient(circle, #d4d4d8 1px, transparent 1px)",
              backgroundSize: "24px 24px",
              backgroundPosition: "0 0",
            }}
          >
            {nodes.map((n) => {
              const kind = getNodeKind(n.type);
              const isSelected = selectedId === n.id;
              return (
                <button
                  className={`absolute flex min-w-[7rem] -translate-x-1/2 -translate-y-1/2 items-center gap-2 rounded-lg border bg-white px-3 py-2 text-sm shadow-sm hover:bg-zinc-50 ${isSelected ? "ring-2 ring-blue-500" : ""}`}
                  data-testid={`flow-node-${n.id}`}
                  data-node-type={n.type}
                  key={n.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedId(n.id);
                  }}
                  onMouseDown={(e) => e.stopPropagation()}
                  style={{ left: n.x, top: n.y }}
                  type="button"
                >
                  <span
                    aria-hidden
                    className={`flex h-6 w-6 items-center justify-center rounded text-base ${kind.color}`}
                  >
                    {kind.icon}
                  </span>
                  <span className="font-medium">{kind.label}</span>
                </button>
              );
            })}
          </div>
          {nodes.length === 0 ? (
            <div
              className="pointer-events-none absolute inset-0 flex items-center justify-center"
              data-testid="flow-placeholder"
            >
              <div className="rounded-lg border border-dashed border-zinc-300 bg-white/80 px-6 py-4 text-center text-sm text-zinc-500">
                <p className="font-medium">Flow canvas is empty.</p>
                <p className="text-xs">
                  Drag a node from the palette to get started.
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </div>
      {selectedNode ? (
        <NodeConfigSidebar
          config={configs[selectedNode.id]}
          node={selectedNode}
          onClose={() => setSelectedId(null)}
          onPersist={(next) =>
            setConfigs((prev) => ({ ...prev, [selectedNode.id]: next }))
          }
        />
      ) : null}
    </section>
  );
}
