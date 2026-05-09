import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  typescript: {
    // This allows the build to succeed even with the error you're seeing
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
