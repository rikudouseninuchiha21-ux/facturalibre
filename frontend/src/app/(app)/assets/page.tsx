import type { Metadata } from "next";

import { AssetsClient } from "@/components/assets/AssetsClient";
import { getFixedAssets, type FixedAsset } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Activos Fijos",
};

export default async function AssetsPage() {
  const cookieHeader = await getSessionCookieHeader();

  let assets: FixedAsset[] = [];
  let error: string | null = null;

  try {
    assets = await getFixedAssets(cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de activos fijos.";
  }

  const now = new Date();
  const currentMonth = now.getMonth() + 1;
  const currentYear = now.getFullYear();
  const today = now.toISOString().slice(0, 10);

  return (
    <AssetsClient
      initialAssets={assets}
      initialError={error}
      currentMonth={currentMonth}
      currentYear={currentYear}
      today={today}
    />
  );
}
