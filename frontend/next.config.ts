import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits a self-contained server bundle in .next/standalone with only the
  // node_modules actually reached at runtime. Without it the runtime image has
  // to carry all of node_modules (~700 MB vs ~200 MB) — worth it on a small box.
  output: "standalone",
};

export default nextConfig;
