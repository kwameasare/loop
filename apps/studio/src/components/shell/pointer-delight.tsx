"use client";

import { useEffect, useRef } from "react";

/**
 * A soft aurora glow that lazily follows the pointer at distance — no
 * crosshair, no box, no animated cursor cosplay. Just a slow radial bloom
 * that warms the area near where the user is reading. Disabled under
 * prefers-reduced-motion, coarse pointers, and touch devices.
 */
export function PointerDelight() {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (
      typeof window === "undefined" ||
      typeof window.matchMedia !== "function" ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      window.matchMedia("(pointer: coarse)").matches
    ) {
      return;
    }

    const el = ref.current;
    if (!el) return;

    const size = 640;
    const half = size / 2;
    let frame = 0;
    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 3;
    let currentX = targetX;
    let currentY = targetY;
    let visible = false;

    const tick = () => {
      currentX += (targetX - currentX) * 0.06;
      currentY += (targetY - currentY) * 0.06;
      el.style.transform = `translate3d(${currentX - half}px, ${currentY - half}px, 0)`;
      frame = window.requestAnimationFrame(tick);
    };
    tick();

    const onMove = (event: PointerEvent) => {
      targetX = event.clientX;
      targetY = event.clientY;
      if (!visible) {
        visible = true;
        el.style.opacity = "1";
      }
    };
    const onLeave = () => {
      visible = false;
      el.style.opacity = "0";
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerleave", onLeave);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  return (
    <div
      ref={ref}
      aria-hidden="true"
      data-testid="pointer-delight"
      className="pointer-light pointer-events-none fixed left-0 top-0 z-0 h-[640px] w-[640px] opacity-0 transition-opacity duration-gentle ease-standard"
    />
  );
}
