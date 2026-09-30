/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  distDir: process.env.MOLE_DIST_DIR || ".next",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.MOLE_API_INTERNAL || "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
};
module.exports = nextConfig;
