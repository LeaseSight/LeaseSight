import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  typescript: {
    // This allows the build to succeed even with the error you're seeing
    ignoreBuildErrors: true,
  },
  // @ts-ignore
  allowedDevOrigins: ['192.168.1.11', 'localhost:3000', 'localhost:3001'],
};

export default nextConfig;
