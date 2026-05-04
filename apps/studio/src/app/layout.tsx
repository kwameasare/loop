import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { AuthProvider } from "@/components/auth/auth-provider";
import { AppErrorBoundary } from "@/components/error-boundary";
import { ToastProvider } from "@/lib/toast";

/**
 * Top-level section links. Each entry must point at a route that has its
 * own ``page.tsx`` (verified at edit time) so a click never lands on a
 * dynamic-route 404. The "real" navigation (workspace switcher, search,
 * search-anywhere) lives behind stories in epic E10; until then this
 * gives reviewers a way to walk the studio without typing URLs.
 */
const NAV_LINKS: ReadonlyArray<{ href: string; label: string }> = [
  { href: "/agents", label: "Agents" },
  { href: "/workspaces/new", label: "Workspaces" },
  { href: "/inbox", label: "Inbox" },
  { href: "/traces", label: "Traces" },
  { href: "/costs", label: "Costs" },
  { href: "/billing", label: "Billing" },
  { href: "/evals", label: "Evals" },
];

export const metadata: Metadata = {
  title: "Loop Studio",
  description: "Build, deploy, and observe agents.",
};

/**
 * S912: read Auth0 tenant configuration from server-side env vars so
 * the same studio bundle works against dev / staging / prod without a
 * rebuild. ``LOOP_AUTH0_*`` is the operator-facing name; the
 * ``NEXT_PUBLIC_AUTH0_*`` aliases remain supported for compatibility
 * with the older static-build path.
 */
function readAuth0ConfigFromEnv() {
  const domain =
    process.env.LOOP_AUTH0_DOMAIN || process.env.NEXT_PUBLIC_AUTH0_DOMAIN || "";
  const clientId =
    process.env.LOOP_AUTH0_CLIENT_ID ||
    process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID ||
    "";
  const audience =
    process.env.LOOP_AUTH0_AUDIENCE ||
    process.env.NEXT_PUBLIC_AUTH0_AUDIENCE ||
    undefined;
  if (!domain || !clientId) return undefined;
  return { domain, clientId, audience };
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const auth0Config = readAuth0ConfigFromEnv();
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased" suppressHydrationWarning>
        <ToastProvider>
          <AuthProvider config={auth0Config}>
            <AppErrorBoundary>
              <header className="border-border bg-background sticky top-0 z-10 border-b">
                <nav
                  aria-label="Studio sections"
                  className="container mx-auto flex h-14 items-center gap-1 px-4 text-sm"
                >
                  <Link
                    href="/"
                    className="hover:text-foreground/90 mr-4 font-semibold tracking-tight"
                  >
                    Loop Studio
                  </Link>
                  {NAV_LINKS.map(({ href, label }) => (
                    <Link
                      key={href}
                      href={href}
                      className="text-muted-foreground hover:text-foreground hover:bg-muted rounded-md px-3 py-1.5 transition-colors"
                    >
                      {label}
                    </Link>
                  ))}
                </nav>
              </header>
              {children}
            </AppErrorBoundary>
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
