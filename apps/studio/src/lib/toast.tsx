"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type ToastTone = "info" | "success" | "error";

export interface ToastInput {
  /** Headline shown in bold. */
  title: string;
  /** Optional supporting text. */
  description?: string;
  /** Stable error/event code, e.g. "E_LOOP_429". */
  code?: string;
  /** Server request id for support correlation. */
  requestId?: string;
  /** Auto-dismiss after ms (default 6000). 0 keeps it sticky. */
  durationMs?: number;
}

export interface Toast extends ToastInput {
  id: string;
  tone: ToastTone;
  createdAt: number;
}

interface ToastContextValue {
  toasts: Toast[];
  push: (tone: ToastTone, input: ToastInput) => string;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let externalPush: ((tone: ToastTone, input: ToastInput) => string) | null =
  null;

/**
 * Sonner-compatible toast API. Bind a provider once and call
 * ``toast.error({ title, code, requestId })`` from anywhere.
 */
export const toast = {
  info: (input: ToastInput | string) =>
    callPush("info", normalize(input)),
  success: (input: ToastInput | string) =>
    callPush("success", normalize(input)),
  error: (input: ToastInput | string) =>
    callPush("error", normalize(input)),
};

function normalize(input: ToastInput | string): ToastInput {
  return typeof input === "string" ? { title: input } : input;
}

function callPush(tone: ToastTone, input: ToastInput): string {
  if (externalPush) return externalPush(tone, input);
  if (typeof console !== "undefined") {
    console.warn("[toast] no <ToastProvider> mounted; dropping toast", {
      tone,
      input,
    });
  }
  return "";
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counter = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (tone: ToastTone, input: ToastInput) => {
      counter.current += 1;
      const id = `t_${counter.current}`;
      const toastEntry: Toast = {
        ...input,
        id,
        tone,
        createdAt: Date.now(),
      };
      setToasts((prev) => [...prev, toastEntry]);
      const duration = input.durationMs ?? 6000;
      if (duration > 0 && typeof window !== "undefined") {
        window.setTimeout(() => dismiss(id), duration);
      }
      return id;
    },
    [dismiss],
  );

  useEffect(() => {
    externalPush = push;
    return () => {
      if (externalPush === push) externalPush = null;
    };
  }, [push]);

  // Bind synchronously during render too so callers from
  // ``componentDidCatch`` (which fires before parent useEffects) still
  // see a live push function.
  if (externalPush !== push) externalPush = push;

  const value = useMemo(
    () => ({ toasts, push, dismiss }),
    [toasts, push, dismiss],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToasts(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToasts must be used inside <ToastProvider>");
  }
  return ctx;
}

function toneClass(tone: ToastTone): string {
  switch (tone) {
    case "error":
      return "border-red-300 bg-red-50 text-red-900";
    case "success":
      return "border-green-300 bg-green-50 text-green-900";
    default:
      return "border-slate-300 bg-white text-slate-900";
  }
}

function ToastViewport({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  return (
    <ol
      data-testid="toast-viewport"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <li
          key={t.id}
          data-testid={`toast-${t.tone}`}
          data-toast-id={t.id}
          className={`pointer-events-auto rounded-md border px-3 py-2 shadow-sm ${toneClass(t.tone)}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold">{t.title}</p>
              {t.description ? (
                <p className="text-xs">{t.description}</p>
              ) : null}
              {t.code || t.requestId ? (
                <p
                  className="mt-1 font-mono text-[11px] text-muted-foreground"
                  data-testid={`toast-meta-${t.id}`}
                >
                  {t.code ? <span>code={t.code}</span> : null}
                  {t.code && t.requestId ? <span> · </span> : null}
                  {t.requestId ? (
                    <span>request_id={t.requestId}</span>
                  ) : null}
                </p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => onDismiss(t.id)}
              data-testid={`toast-dismiss-${t.id}`}
              className="text-xs text-muted-foreground hover:underline"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        </li>
      ))}
    </ol>
  );
}
