import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth/auth-provider";
import { AppErrorBoundary } from "@/components/error-boundary";
import { ToastProvider } from "@/lib/toast";

export const metadata: Metadata = {
  title: "Loop Studio",
  description: "Build, deploy, and observe agents.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <ToastProvider>
          <AuthProvider>
            <AppErrorBoundary>{children}</AppErrorBoundary>
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
