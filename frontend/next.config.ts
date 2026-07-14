import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // Backend serves the static export via Starlette's StaticFiles(html=True),
  // which only resolves "<path>/index.html" for a directory request - not
  // Next's default flat "<path>.html" files. Trailing slashes make Next emit
  // the former, matching what the backend can actually serve.
  trailingSlash: true,
};

export default nextConfig;
