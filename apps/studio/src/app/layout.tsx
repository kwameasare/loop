import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Loop Studio",
  description: "Build, deploy, and observe agents.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
