import type { Metadata } from "next";

import { SettingsForm } from "@/components/settings/SettingsForm";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getCompanySettings } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Configuración",
};

export default async function SettingsPage() {
  const cookieHeader = await getSessionCookieHeader();

  let companySettings: Awaited<
    ReturnType<typeof getCompanySettings>
  > | null = null;
  let error: string | null = null;

  try {
    companySettings = await getCompanySettings(cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo cargar la configuración de la empresa.";
  }

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Configuración de la Empresa
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Administra los datos de tu empresa. Esta información se utiliza en
          las facturas y reportes generados.
        </p>
      </header>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Datos de la Empresa</CardTitle>
          <CardDescription>
            Actualiza los datos de tu empresa. Esta información se muestra en
            las facturas emitidas.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {companySettings ? (
            <SettingsForm companySettings={companySettings} />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
