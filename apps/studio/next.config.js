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
};

module.exports = nextConfig;
