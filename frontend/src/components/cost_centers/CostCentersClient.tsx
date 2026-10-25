"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ApiError,
  createCostCenter,
  deleteCostCenter,
  updateCostCenter,
  type CostCenter,
} from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-amber-600 focus:ring-2 focus:ring-amber-500/10 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-500";

interface CostCentersClientProps {
  initialCostCenters: CostCenter[];
}

export function CostCentersClient({ initialCostCenters }: CostCentersClientProps) {
  const router = useRouter();
  const [centers, setCenters] = useState<CostCenter[]>(initialCostCenters);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function handleCreate(
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);
    try {
      const created = await createCostCenter({
        code: code.trim(),
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setCenters((current) =>
        [...current, created].sort((a, b) => a.code.localeCompare(b.code)),
      );
      setCode("");
      setName("");
      setDescription("");
      setSuccess(`Centro de costo ${created.code} creado correctamente.`);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo crear el centro de costo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleToggleActive(center: CostCenter): Promise<void> {
    setBusyId(center.id);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateCostCenter(center.id, {
        is_active: !center.is_active,
      });
      setCenters((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo actualizar el centro de costo.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(center: CostCenter): Promise<void> {
    setBusyId(center.id);
    setError(null);
    setSuccess(null);
    try {
      await deleteCostCenter(center.id);
      setCenters((current) =>
        current.filter((item) => item.id !== center.id),
      );
      setSuccess(
        center.is_active
          ? `Centro ${center.code} desactivado (está referenciado por documentos o presupuestos).`
          : `Centro ${center.code} eliminado.`,
      );
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo eliminar el centro de costo.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Nuevo Centro de Costo</CardTitle>
          <CardDescription>
            El código debe ser único (por ejemplo CC-VEN). Los centros
            referenciados por presupuestos o asientos no se eliminan: se
            desactivan.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-6">
            <div className="grid gap-6 md:grid-cols-3">
              <div className="space-y-2">
                <label
                  htmlFor="cost-center-code"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Código{" "}
                  <span className="text-red-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="cost-center-code"
                  type="text"
                  required
                  maxLength={20}
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  disabled={isSubmitting}
                  className={inputClassName}
                  placeholder="CC-VEN"
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="cost-center-name"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Nombre{" "}
                  <span className="text-red-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="cost-center-name"
                  type="text"
                  required
                  maxLength={100}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  disabled={isSubmitting}
                  className={inputClassName}
                  placeholder="Ventas"
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="cost-center-description"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Descripción
                </label>
                <input
                  id="cost-center-description"
                  type="text"
                  maxLength={2000}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  disabled={isSubmitting}
                  className={inputClassName}
                  placeholder="Área comercial y de ventas"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center justify-center rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 px-4 py-2 text-sm font-semibold text-zinc-950 shadow-sm transition-colors hover:from-amber-300 hover:to-amber-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? "Creando..." : "Crear Centro de Costo"}
              </button>
            </div>

            {error ? (
              <div
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              >
                {error}
              </div>
            ) : null}
            {success ? (
              <div
                role="status"
                className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
              >
                {success}
              </div>
            ) : null}
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {centers.length} centro{centers.length === 1 ? "" : "s"} de costo
            registrado{centers.length === 1 ? "" : "s"}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {centers.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay centros de costo
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Crea el primero con el formulario de arriba.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de centros de costo</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Código</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Descripción</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {centers.map((center) => (
                  <TableRow key={center.id}>
                    <TableCell className="font-mono text-xs font-semibold text-slate-950">
                      {center.code}
                    </TableCell>
                    <TableCell className="font-medium text-slate-950">
                      {center.name}
                    </TableCell>
                    <TableCell className="max-w-md text-slate-600">
                      {center.description ?? "—"}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${
                          center.is_active
                            ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                            : "bg-zinc-100 text-zinc-500 ring-zinc-200"
                        }`}
                      >
                        {center.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => void handleToggleActive(center)}
                          disabled={busyId === center.id}
                          className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-700 shadow-sm transition-colors hover:border-zinc-400 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {center.is_active ? "Desactivar" : "Activar"}
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDelete(center)}
                          disabled={busyId === center.id}
                          className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 shadow-sm transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Eliminar
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
