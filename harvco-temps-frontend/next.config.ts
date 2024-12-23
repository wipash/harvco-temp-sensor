import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone',
  swcMinify: true,
  reactStrictMode: true,
};

export default nextConfig;
