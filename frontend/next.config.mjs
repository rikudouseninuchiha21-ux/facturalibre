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


/** Cabeceras de seguridad (Fase 39B), espejo de las del backend. */
const securityHeaders = [
  { key: "Content-Security-Policy", value: "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
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
