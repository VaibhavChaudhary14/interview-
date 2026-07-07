/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    // BACKEND_URL is runtime-only to avoid Next.js build-time inlining
    const apiBase =
      process.env.BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      "http://localhost:8000";
    // Strip /api/v1 suffix if present to avoid path duplication
    const backendBase = apiBase.replace(/\/api\/v1\/?$/, "");
    return [
      {
        source: "/api/:path*",
        destination: `${backendBase}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
