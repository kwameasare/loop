const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true",
  openAnalyzer: false,
  generateStatsFile: true,
});

function originFromRaw(raw) {
  if (!raw) return null;
  try {
    return new URL(raw).origin;
  } catch {
    return null;
  }
}

function buildCsp() {
  const cpOrigin = originFromRaw(
    process.env.NEXT_PUBLIC_LOOP_API_URL || process.env.LOOP_CP_API_BASE_URL,
  );
  const dpOrigin = originFromRaw(
    process.env.NEXT_PUBLIC_LOOP_DP_URL || process.env.LOOP_DP_API_BASE_URL,
  );
  const auth0Domain =
    process.env.LOOP_AUTH0_DOMAIN || process.env.NEXT_PUBLIC_AUTH0_DOMAIN;
  const auth0Origin = auth0Domain ? `https://${auth0Domain}` : null;

  const connectSrc = ["'self'", cpOrigin, dpOrigin, auth0Origin]
    .filter(Boolean)
    .join(" ");

  return [
    "default-src 'self'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    `connect-src ${connectSrc}`,
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "object-src 'none'",
    "form-action 'self'",
  ].join("; ");
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Strip browser source maps in production so we don't leak the
  // original module graph (S164: error toast surfaces code+request_id
  // without exposing internals to end-users).
  productionBrowserSourceMaps: false,
  experimental: {
    typedRoutes: true,
  },
  async headers() {
    const csp = buildCsp();
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains; preload",
          },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          { key: "Content-Security-Policy", value: csp },
        ],
      },
    ];
  },
};

module.exports = withBundleAnalyzer(nextConfig);
