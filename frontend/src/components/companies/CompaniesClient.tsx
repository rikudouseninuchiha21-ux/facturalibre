"use client";

import { Building2, ChevronDown, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ApiError,
  assignCompanyUser,
  createCompany,
  getCompanyUsers,
  type CompanyMembership,
  type CompanyUser,
  type User,
} from "@/lib/api";

interface CompaniesClientProps {
  currentUser: User | null;
  companies: CompanyMembership[];
  users: User[];
}

const roleLabels: Record<string, string> = {
  ADMIN: "Administrador",
  ACCOUNTANT: "Contador",
  CASHIER: "Cajero",
};

const inputClassName =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-slate-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20";

function emptyCreateForm() {
  return {
    name: "",
    tax_id: "",
    dv: "",
    email: "",
    phone: "",
    address: "",
  };
}

export function CompaniesClient({
  currentUser,
  companies,
  users,
}: CompaniesClientProps) {
  const router = useRouter();
  const adminCompanies = companies.filter((item) => item.role === "ADMIN");
  const canCreateCompany = currentUser?.role === "ADMIN";

  const [form, setForm] = useState(emptyCreateForm());
  const [isCreating, setIsCreating] = useState(false);
  const [assignCompanyId, setAssignCompanyId] = useState(
    adminCompanies[0]?.company.id ?? "",
  );
  const [assignUserId, setAssignUserId] = useState(users[0]?.id ?? "");
  const [assignRole, setAssignRole] = useState("ACCOUNTANT");
  const [isAssigning, setIsAssigning] = useState(false);
  const [membersCompanyId, setMembersCompanyId] = useState<string | null>(null);
  const [members, setMembers] = useState<CompanyUser[]>([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const effectiveCompanyId = adminCompanies.some(
    (item) => item.company.id === assignCompanyId,
  )
    ? assignCompanyId
    : (adminCompanies[0]?.company.id ?? "");

  function updateField(field: keyof ReturnType<typeof emptyCreateForm>, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    if (!form.name.trim()) {
      setError("El nombre de la empresa es obligatorio.");
      return;
    }

    setIsCreating(true);
    try {
      await createCompany({
        name: form.name.trim(),
        ...(form.tax_id.trim() ? { tax_id: form.tax_id.trim() } : {}),
        ...(form.dv.trim() ? { dv: form.dv.trim() } : {}),
        ...(form.email.trim() ? { email: form.email.trim() } : {}),
        ...(form.phone.trim() ? { phone: form.phone.trim() } : {}),
        ...(form.address.trim() ? { address: form.address.trim() } : {}),
      });
      setForm(emptyCreateForm());
      setMessage("Empresa creada correctamente.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo crear la empresa.",
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function loadMembers(companyId: string) {
    setMembersCompanyId(companyId);
    setIsLoadingMembers(true);
    setError(null);
    try {
      setMembers(await getCompanyUsers(companyId));
    } catch (cause) {
      setMembers([]);
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudieron cargar los usuarios.",
      );
    } finally {
      setIsLoadingMembers(false);
    }
  }

  async function handleAssign(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    if (!effectiveCompanyId || !assignUserId) {
      setError("Selecciona una empresa y un usuario.");
      return;
    }

    setIsAssigning(true);
    try {
      await assignCompanyUser(effectiveCompanyId, {
        user_id: assignUserId,
        role: assignRole,
      });
      setMessage("Usuario asignado correctamente.");
      if (membersCompanyId === effectiveCompanyId) {
        await loadMembers(effectiveCompanyId);
      }
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo asignar el usuario.",
      );
    } finally {
      setIsAssigning(false);
    }
  }

  return (
    <div className="space-y-6">
      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}
      {message ? (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
        >
          {message}
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="size-5 text-violet-600" aria-hidden="true" />
              Nueva empresa
            </CardTitle>
            <CardDescription>
              Solo los administradores pueden crear empresas. El creador queda
              como ADMIN de la nueva empresa.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!canCreateCompany ? (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                No tienes rol ADMIN en la empresa activa. Cambia de empresa desde
                el selector superior o pide acceso a un administrador.
              </p>
            ) : (
              <form className="space-y-4" onSubmit={handleCreate}>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block space-y-1 sm:col-span-2">
                    <span className="text-sm font-medium text-slate-700">
                      Nombre *
                    </span>
                    <input
                      className={inputClassName}
                      value={form.name}
                      onChange={(event) => updateField("name", event.target.value)}
                      placeholder="VANTAGE Colombia S.A.S."
                      required
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-sm font-medium text-slate-700">NIT</span>
                    <input
                      className={inputClassName}
                      value={form.tax_id}
                      onChange={(event) => updateField("tax_id", event.target.value)}
                      placeholder="900123456"
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-sm font-medium text-slate-700">
                      Dígito de verificación
                    </span>
                    <input
                      className={inputClassName}
                      value={form.dv}
                      onChange={(event) => updateField("dv", event.target.value)}
                      placeholder="1"
                      maxLength={2}
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-sm font-medium text-slate-700">
                      Correo
                    </span>
                    <input
                      type="email"
                      className={inputClassName}
                      value={form.email}
                      onChange={(event) => updateField("email", event.target.value)}
                      placeholder="empresa@vantage.co"
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-sm font-medium text-slate-700">
                      Teléfono
                    </span>
                    <input
                      className={inputClassName}
                      value={form.phone}
                      onChange={(event) => updateField("phone", event.target.value)}
                      placeholder="+57 601 000 0000"
                    />
                  </label>
                  <label className="block space-y-1 sm:col-span-2">
                    <span className="text-sm font-medium text-slate-700">
                      Dirección
                    </span>
                    <input
                      className={inputClassName}
                      value={form.address}
                      onChange={(event) => updateField("address", event.target.value)}
                      placeholder="Calle 100 # 15-20, Bogotá D.C."
                    />
                  </label>
                </div>
                <Button type="submit" disabled={isCreating}>
                  {isCreating ? "Creando..." : "Crear empresa"}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="size-5 text-violet-600" aria-hidden="true" />
              Asignar usuario
            </CardTitle>
            <CardDescription>
              Asigna un usuario existente a una empresa y define su rol en ese
              tenant.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {adminCompanies.length === 0 || users.length === 0 ? (
              <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                Necesitas ser ADMIN de una empresa y tener usuarios creados para
                poder asignarlos.
              </p>
            ) : (
              <form className="space-y-4" onSubmit={handleAssign}>
                <label className="block space-y-1">
                  <span className="text-sm font-medium text-slate-700">
                    Empresa
                  </span>
                  <select
                    className={inputClassName}
                    value={effectiveCompanyId}
                    onChange={(event) => setAssignCompanyId(event.target.value)}
                  >
                    {adminCompanies.map((item) => (
                      <option key={item.company.id} value={item.company.id}>
                        {item.company.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block space-y-1">
                  <span className="text-sm font-medium text-slate-700">
                    Usuario
                  </span>
                  <select
                    className={inputClassName}
                    value={assignUserId}
                    onChange={(event) => setAssignUserId(event.target.value)}
                  >
                    {users.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.full_name} — {user.email}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block space-y-1">
                  <span className="text-sm font-medium text-slate-700">Rol</span>
                  <select
                    className={inputClassName}
                    value={assignRole}
                    onChange={(event) => setAssignRole(event.target.value)}
                  >
                    <option value="ADMIN">Administrador</option>
                    <option value="ACCOUNTANT">Contador</option>
                    <option value="CASHIER">Cajero</option>
                  </select>
                </label>
                <Button type="submit" disabled={isAssigning}>
                  {isAssigning ? "Asignando..." : "Asignar usuario"}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Mis empresas</CardTitle>
          <CardDescription>
            {companies.length} empresa{companies.length === 1 ? "" : "s"}{" "}
            disponible{companies.length === 1 ? "" : "s"} en tu cuenta.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {companies.map((item) => {
            const isActive = currentUser?.active_company_id === item.company.id;
            const isAdmin = item.role === "ADMIN";
            return (
              <div
                key={item.company.id}
                className="rounded-xl border border-violet-100 bg-violet-50/40 px-4 py-4"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-slate-950">
                        {item.company.name}
                      </p>
                      {isActive ? (
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-700">
                          Activa
                        </span>
                      ) : null}
                      <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-800">
                        {roleLabels[item.role] ?? item.role}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">
                      NIT: {item.company.tax_id ?? "—"}
                      {item.company.dv ? `-${item.company.dv}` : ""} ·{" "}
                      {item.company.email ?? "Sin correo"}
                    </p>
                  </div>
                  {isAdmin ? (
                    <Button
                      type="button"
                      onClick={() => void loadMembers(item.company.id)}
                      className="shrink-0 border border-violet-200 bg-white text-violet-700 shadow-sm hover:bg-violet-100"
                    >
                      <Users className="mr-2 size-4" aria-hidden="true" />
                      {membersCompanyId === item.company.id ? "Actualizar" : "Ver usuarios"}
                      <ChevronDown
                        className={`ml-2 size-4 transition-transform ${
                          membersCompanyId === item.company.id ? "rotate-180" : ""
                        }`}
                        aria-hidden="true"
                      />
                    </Button>
                  ) : null}
                </div>

                {membersCompanyId === item.company.id ? (
                  <div className="mt-4 rounded-lg border border-violet-100 bg-white p-3">
                    {isLoadingMembers ? (
                      <p className="text-sm text-slate-500">Cargando usuarios...</p>
                    ) : members.length === 0 ? (
                      <p className="text-sm text-slate-500">
                        Esta empresa todavía no tiene usuarios asignados.
                      </p>
                    ) : (
                      <ul className="divide-y divide-slate-100">
                        {members.map((member) => (
                          <li
                            key={member.user_id}
                            className="flex flex-col gap-1 py-2 text-sm sm:flex-row sm:items-center sm:justify-between"
                          >
                            <span className="font-medium text-slate-900">
                              {member.full_name}{" "}
                              <span className="font-normal text-slate-500">
                                ({member.email})
                              </span>
                            </span>
                            <span className="text-xs font-semibold text-violet-700">
                              {roleLabels[member.role] ?? member.role}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ) : null}
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
