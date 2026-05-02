import { describe, expect, it } from "vitest";

import {
  DEFAULT_VIEWPORT,
  MAX_ZOOM,
  MIN_ZOOM,
  clampZoom,
  pan,
  resetViewport,
  zoomAt,
} from "./flow-canvas";

describe("flow-canvas geometry", () => {
  it("clampZoom respects min/max bounds", () => {
    expect(clampZoom(0.01)).toBe(MIN_ZOOM);
    expect(clampZoom(99)).toBe(MAX_ZOOM);
    expect(clampZoom(1.5)).toBe(1.5);
    expect(clampZoom(NaN)).toBe(1);
  });

  it("pan adds screen-space deltas to the viewport offset", () => {
    expect(pan({ x: 10, y: 20, zoom: 1 }, 5, -3)).toEqual({
      x: 15,
      y: 17,
      zoom: 1,
    });
  });

  it("zoomAt keeps the focal world point under the cursor", () => {
    const before = { x: 0, y: 0, zoom: 1 };
    const fx = 200;
    const fy = 100;
    const after = zoomAt(before, 2, fx, fy);
    expect(after.zoom).toBe(2);
    // World point at focal before: (fx - 0)/1 = 200, 100
    // World point at focal after: (fx - after.x)/2
    expect((fx - after.x) / after.zoom).toBe(200);
    expect((fy - after.y) / after.zoom).toBe(100);
  });

  it("zoomAt is a no-op when at the zoom limit", () => {
    const v = { x: 5, y: 5, zoom: MAX_ZOOM };
    expect(zoomAt(v, 2, 0, 0)).toBe(v);
  });

  it("resetViewport returns a fresh default", () => {
    const a = resetViewport();
    const b = resetViewport();
    expect(a).toEqual(DEFAULT_VIEWPORT);
    expect(a).not.toBe(b);
  });
});
