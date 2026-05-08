"use client";

import { useEffect, useState } from "react";

interface PointerState {
  x: number;
  y: number;
  visible: boolean;
}

export function PointerDelight() {
  const [pointer, setPointer] = useState<PointerState>({
    x: 0,
    y: 0,
    visible: false,
  });

  useEffect(() => {
    if (
      typeof window === "undefined" ||
      typeof window.matchMedia !== "function" ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      window.matchMedia("(pointer: coarse)").matches
    ) {
      return;
    }

    let frame = 0;
    const show = (event: PointerEvent) => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        setPointer({ x: event.clientX, y: event.clientY, visible: true });
      });
    };
    const hide = () => setPointer((current) => ({ ...current, visible: false }));

    window.addEventListener("pointermove", show, { passive: true });
    window.addEventListener("pointerleave", hide);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", show);
      window.removeEventListener("pointerleave", hide);
    };
  }, []);

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed z-50 hidden h-7 w-7 -translate-x-1/2 -translate-y-1/2 rounded-[5px] border border-primary/45 opacity-0 shadow-[0_0_24px_hsl(var(--primary)/0.18)] transition-opacity duration-swift ease-standard md:block"
      data-visible={pointer.visible}
      data-testid="pointer-delight"
      style={{
        left: pointer.x,
        top: pointer.y,
        opacity: pointer.visible ? 1 : 0,
      }}
    >
      <span className="absolute left-1/2 top-1/2 h-px w-10 -translate-x-1/2 bg-primary/35" />
      <span className="absolute left-1/2 top-1/2 h-10 w-px -translate-y-1/2 bg-primary/35" />
    </div>
  );
}
