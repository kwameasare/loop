import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth/auth-provider";
import { AppErrorBoundary } from "@/components/error-boundary";
import { AppShell } from "@/components/shell/app-shell";
import { ToastProvider } from "@/lib/toast";

export const metadata: Metadata = {
  title: "Loop Studio",
  description: "Build, deploy, and observe agents.",
  robots: {
    index: false,
    follow: false,
    googleBot: {
      index: false,
      follow: false,
    },
  },
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
  return {
    domain,
    clientId,
    ...(audience ? { audience } : {}),
  };
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const auth0Config = readAuth0ConfigFromEnv();
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased" suppressHydrationWarning>
        <ToastProvider>
          <AuthProvider {...(auth0Config ? { config: auth0Config } : {})}>
            <AppErrorBoundary>
              <AppShell>{children}</AppShell>
            </AppErrorBoundary>
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
