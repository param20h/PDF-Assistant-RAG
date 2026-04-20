import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  // Turbopack config (Next.js 16 default bundler)
  turbopack: {},
};

export default nextConfig;
