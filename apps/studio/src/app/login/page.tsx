"use client";

/**
 * ``/login`` — Auth0 PKCE redirect when Auth0 is configured, OR
 * a local email-only form when it isn't (local pilot mode).
 *
 * Auth0 path (S151): forwards ``returnTo`` into the Auth0 redirect's
 * ``appState`` so the post-callback route lands the user back where
 * they came from.
 *
 * Local-pilot path: posts the email to ``/api/dev-login`` (server-only
 * route handler that mints a HS256 JWT against
 * ``LOOP_CP_LOCAL_JWT_SECRET`` and exchanges it with cp's
 * ``/v1/auth/exchange``). The returned PASETO is stashed in
 * ``sessionStorage`` (``loop.cp.session``) — the same key the
 * Auth0 callback uses — so the rest of the studio works unchanged.
 *
 * Auth0-configured is detected by ``NEXT_PUBLIC_AUTH0_DOMAIN``. The
 * AuthProvider already throws in NODE_ENV=production when that's
 * unset, so the local-pilot form is only reachable in dev/preview.
 */

import { useAuth0 } from "@auth0/auth0-react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { storeSessionToken } from "@/lib/cp-auth-exchange";
import { useAuth0Configured } from "@/lib/auth-mode";
import { useUser } from "@/lib/use-user";

function Auth0Login({ returnTo }: { returnTo: string }) {
  const { getIdTokenClaims, loginWithRedirect } = useAuth0();
  const { isAuthenticated, isLoading } = useUser();
  const router = useRouter();
  const exchangeRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      if (exchangeRef.current) return;
      exchangeRef.current = true;
      void (async () => {
        try {
          const claims = await getIdTokenClaims();
          const idToken = claims?.__raw;
          if (!idToken) {
            throw new Error("Auth0 returned no id_token for session exchange.");
          }
          const response = await fetch("/api/session", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ id_token: idToken }),
          });
          const text = await response.text();
          if (!response.ok) {
            throw new Error(
              `/api/session returned HTTP ${response.status}: ${text.slice(
                0,
                180,
              )}`,
            );
          }
          storeSessionToken(JSON.parse(text));
          router.replace(returnTo);
        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not establish the Loop control-plane session.",
          );
        }
      })();
      return;
    }
    void loginWithRedirect({ appState: { returnTo } });
  }, [
    getIdTokenClaims,
    isLoading,
    isAuthenticated,
    loginWithRedirect,
    returnTo,
    router,
    retryKey,
  ]);

  if (error) {
    return (
      <main
        className="flex min-h-screen items-center justify-center px-4"
        role="alert"
      >
        <div className="max-w-md rounded-lg border bg-card p-6 text-center shadow-sm">
          <p className="font-medium text-destructive">
            Sign-in could not finish
          </p>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
          <button
            type="button"
            className="mt-4 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-muted"
            onClick={() => {
              exchangeRef.current = false;
              setError(null);
              setRetryKey((value) => value + 1);
            }}
          >
            Retry session exchange
          </button>
        </div>
      </main>
    );
  }

  return (
    <main
      className="flex min-h-screen items-center justify-center"
      role="status"
      aria-label="Redirecting to sign in"
    >
      <p className="text-muted-foreground">
        {isAuthenticated
          ? "Completing control-plane session…"
          : "Redirecting to sign in…"}
      </p>
    </main>
  );
}

function LocalPilotLogin({ returnTo }: { returnTo: string }) {
  const router = useRouter();
  const [email, setEmail] = useState("dev@loop.local");
  const [status, setStatus] = useState<
    | { kind: "idle" }
    | { kind: "submitting" }
    | { kind: "error"; message: string }
  >({ kind: "idle" });

  const submit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setStatus({ kind: "submitting" });
      try {
        const response = await fetch("/api/dev-login", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ email }),
        });
        const text = await response.text();
        if (!response.ok) {
          let parsed: { error?: string } = {};
          try {
            parsed = JSON.parse(text) as { error?: string };
          } catch {
            /* fall through */
          }
          throw new Error(
            parsed.error ?? `dev-login failed: HTTP ${response.status}`,
          );
        }
        const payload = JSON.parse(text) as {
          access_token: string;
          token_type?: string;
          expires_in?: number;
          refresh_token?: string;
        };
        storeSessionToken(payload);
        router.replace(returnTo);
      } catch (err) {
        setStatus({
          kind: "error",
          message: err instanceof Error ? err.message : "Sign-in failed",
        });
      }
    },
    [email, returnTo, router],
  );

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm space-y-4 rounded-lg border bg-card p-6 shadow-sm"
        aria-label="Local pilot sign in"
      >
        <div className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight">
            Sign in (local pilot)
          </h1>
          <p className="text-muted-foreground text-sm">
            No Auth0 configured. Enter any email — the studio will mint a local
            session via cp&apos;s dev exchange. Production deploys require a
            real IdP.
          </p>
        </div>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            data-testid="dev-login-email"
            className="rounded-md border bg-background px-2 py-1.5"
            autoFocus
          />
        </label>
        {status.kind === "error" ? (
          <p
            role="alert"
            data-testid="dev-login-error"
            className="text-destructive text-sm"
          >
            {status.message}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={status.kind === "submitting"}
          data-testid="dev-login-submit"
          className="w-full rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
        >
          {status.kind === "submitting" ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}

function LoginInner() {
  const params = useSearchParams();
  const returnTo = params.get("returnTo") || "/home";
  const auth0Configured = useAuth0Configured();
  if (!auth0Configured) {
    return <LocalPilotLogin returnTo={returnTo} />;
  }
  return <Auth0Login returnTo={returnTo} />;
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main
          className="flex min-h-screen items-center justify-center"
          role="status"
          aria-label="Loading"
        >
          <p className="text-muted-foreground">Loading…</p>
        </main>
      }
    >
      <LoginInner />
    </Suspense>
  );
}
