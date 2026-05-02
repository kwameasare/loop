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
import { FLOW_DOT_GRID } from "@/lib/design-tokens";

export interface FlowCanvasProps {
  agentId: string;
}

export function FlowCanvas(props: FlowCanvasProps) {
  const [viewport, setViewport] = useState<Viewport>(DEFAULT_VIEWPORT);
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

  return (
    <section
      className="flex h-[640px] w-full flex-col rounded-lg border bg-zinc-50"
      data-testid="flow-canvas"
    >
      <header
        className="flex items-center justify-between border-b bg-white px-4 py-2"
        data-testid="flow-toolbar"
      >
        <div className="flex items-center gap-2 text-sm">
          <span className="font-mono text-xs text-zinc-500">
            agent-id: {props.agentId}
          </span>
        </div>
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
              `radial-gradient(circle, ${FLOW_DOT_GRID} 1px, transparent 1px)`,
            backgroundSize: "24px 24px",
            backgroundPosition: "0 0",
          }}
        />
        <div
          className="pointer-events-none absolute inset-0 flex items-center justify-center"
          data-testid="flow-placeholder"
        >
          <div className="rounded-lg border border-dashed border-zinc-300 bg-white/80 px-6 py-4 text-center text-sm text-zinc-500">
            <p className="font-medium">Flow canvas is empty.</p>
            <p className="text-xs">
              Node palette and edge editing arrive in S461.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
