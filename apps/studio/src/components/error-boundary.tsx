"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

import { toast } from "@/lib/toast";

export interface AppErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface State {
  error: Error | null;
}

interface ErrorWithMeta extends Error {
  code?: string;
  requestId?: string;
  request_id?: string;
}

/**
 * Catches render errors anywhere below it. Surfaces a red toast with
 * the error code + request_id (if present on the error object) and
 * keeps the rest of the app interactive via a fallback render.
 */
export class AppErrorBoundary extends Component<AppErrorBoundaryProps, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    const meta = error as ErrorWithMeta;
    const requestId = meta.requestId ?? meta.request_id;
    toast.error({
      title: "Something broke while rendering this view.",
      description: error.message,
      ...(meta.code ? { code: meta.code } : {}),
      ...(requestId ? { requestId } : {}),
    });
    if (process.env.NODE_ENV !== "production") {
      console.error("[AppErrorBoundary]", error, info);
    }
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (error) {
      const fallback = this.props.fallback;
      if (fallback) return fallback(error, this.reset);
      return (
        <div
          data-testid="error-boundary-fallback"
          className="rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-900"
        >
          <p className="font-semibold">Something went wrong.</p>
          <p className="mt-1 text-xs">{error.message}</p>
          <button
            type="button"
            onClick={this.reset}
            data-testid="error-boundary-reset"
            className="mt-2 rounded-md border border-red-300 px-2 py-1 text-xs"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
