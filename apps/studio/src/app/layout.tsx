import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth/auth-provider";
import { AppErrorBoundary } from "@/components/error-boundary";
import { AppShell } from "@/components/shell/app-shell";
import { ThemeRuntime } from "@/components/shell/theme-runtime";
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

const THEME_BOOT_SCRIPT = `
(() => {
  try {
    const stored = window.localStorage.getItem("loop.settings.theme") || "dark";
    const systemDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
    const dark = stored === "dark" || (stored === "system" && systemDark);
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    document.documentElement.style.colorScheme = dark ? "dark" : "light";
  } catch {
    document.documentElement.classList.add("dark");
    document.documentElement.dataset.theme = "dark";
    document.documentElement.style.colorScheme = "dark";
  }
})();
`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const auth0Config = readAuth0ConfigFromEnv();
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
      </head>
      <body className="min-h-screen antialiased" suppressHydrationWarning>
        <ToastProvider>
          <ThemeRuntime />
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
