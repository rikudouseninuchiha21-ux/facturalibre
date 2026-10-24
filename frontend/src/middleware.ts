import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE_NAME } from "@/lib/session";

const PUBLIC_PATHS = new Set(["/", "/login", "/register"]);

/**
 * Protección perimetral de páginas.
 *
 * El middleware solo verifica la presencia de la cookie; la validez real de la
 * sesión la impone el backend en cada endpoint con `get_current_user` (401).
 */
export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.has(pathname)) {
    return NextResponse.next();
  }

  const session = request.cookies.get(SESSION_COOKIE_NAME);
  if (!session?.value) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Se protegen las páginas, pero no:
     * - /api (el backend aplica su propia autenticación)
     * - assets internos de Next.js
     * - archivos públicos con extensión (favicon, iconos, imágenes)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|icon.svg|.*\\..*).*)",
  ],
};
