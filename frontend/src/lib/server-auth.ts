import { cookies } from "next/headers";

import { SESSION_COOKIE_NAME } from "@/lib/session";

/**
 * Obtiene la cookie de sesión para reenviarla desde un Server Component.
 *
 * `fetch` del servidor no comparte el cookie jar del navegador. Sin este
 * reenvío, las páginas protegidas recibirían 401 al llamar al backend.
 */
export async function getSessionCookieHeader(): Promise<string | undefined> {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;

  if (!token) {
    return undefined;
  }

  return `${SESSION_COOKIE_NAME}=${encodeURIComponent(token)}`;
}
