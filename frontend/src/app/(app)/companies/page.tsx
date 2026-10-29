import type { Metadata } from "next";

import {
  ApiError,
  getCompanies,
  getCurrentUser,
  getUsers,
  type CompanyMembership,
  type User,
} from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";
import { CompaniesClient } from "@/components/companies/CompaniesClient";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Empresas",
};

export default async function CompaniesPage() {
  const cookieHeader = await getSessionCookieHeader();

  let currentUser: User | null = null;
  let companies: CompanyMembership[] = [];
  let users: User[] = [];
  let error: string | null = null;

  try {
    const [userResult, companiesResult] = await Promise.all([
      getCurrentUser(cookieHeader),
      getCompanies(cookieHeader),
    ]);
    currentUser = userResult;
    companies = companiesResult;
  } catch (cause) {
    error =
      cause instanceof ApiError
        ? cause.message
        : "No fue posible cargar las empresas.";
  }

  if (!error) {
    try {
      users = await getUsers(cookieHeader);
    } catch {
      // Un usuario sin rol ADMIN en la empresa activa no puede listar usuarios;
      // la página sigue siendo útil para consultar sus empresas.
      users = [];
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wider text-violet-600">
          Administración
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
          Empresas
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Administra las empresas de tu cuenta, cambia de tenant y asigna
          usuarios con el rol que tendrán en cada empresa.
        </p>
      </header>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : (
        <CompaniesClient
          currentUser={currentUser}
          companies={companies}
          users={users}
        />
      )}
    </div>
  );
}
