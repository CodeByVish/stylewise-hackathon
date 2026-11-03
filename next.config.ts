import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // the dev server only serves its scripts to localhost by default; also allow 127.0.0.1
  allowedDevOrigins: ["127.0.0.1"],
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
