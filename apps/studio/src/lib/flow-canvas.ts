/**
 * Geometry helpers for the flow canvas. Kept independent of React so they
 * can be tested without DOM emulation.
 */

export interface Viewport {
  x: number;
  y: number;
  zoom: number;
}

export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 4;
export const DEFAULT_VIEWPORT: Viewport = { x: 0, y: 0, zoom: 1 };

export function clampZoom(z: number): number {
  if (Number.isNaN(z)) return 1;
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));
}

/**
 * Pan the viewport by ``dx``/``dy`` screen pixels. Uses simple subtraction
 * so dragging a node "right" reveals more of the world to the right.
 */
export function pan(v: Viewport, dx: number, dy: number): Viewport {
  return { ...v, x: v.x + dx, y: v.y + dy };
}

/**
 * Zoom toward a screen-space focal point ``(fx, fy)``. The world point
 * under the focal stays put.
 */
export function zoomAt(
  v: Viewport,
  factor: number,
  fx: number,
  fy: number,
): Viewport {
  const nextZoom = clampZoom(v.zoom * factor);
  if (nextZoom === v.zoom) return v;
  // World point under focal: w = (f - offset) / zoom
  const wx = (fx - v.x) / v.zoom;
  const wy = (fy - v.y) / v.zoom;
  // After zoom, we want the same world point under the same focal:
  // f = w * nextZoom + offset → offset = f - w * nextZoom
  return {
    x: fx - wx * nextZoom,
    y: fy - wy * nextZoom,
    zoom: nextZoom,
  };
}

export function resetViewport(): Viewport {
  return { ...DEFAULT_VIEWPORT };
}
