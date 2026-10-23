/**
 * En desarrollo, `BACKEND_INTERNAL_URL` apunta al backend en el host.
 * En Docker Compose se define como `http://backend:8000`.
 *
 * El navegador llama siempre a `/api/v1/...` (mismo origen) y Next.js
 * reenvía la petición al backend, evitando CORS.
 */
const backendInternalUrl = (
  process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // El README usa 127.0.0.1 y el frontend se publica en ese host. Sin esta
  // allowlist, Next.js 16 bloquea los recursos de desarrollo y el formulario
  // no se hidrata, provocando un submit GET nativo.
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendInternalUrl}/api/:path*`,
      },
    ];
  },
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
