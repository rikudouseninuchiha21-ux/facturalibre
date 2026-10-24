import type { Metadata } from "next";

import { EmployeeForm } from "@/components/employees/EmployeeForm";
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
import { getEmployees, type Employee } from "@/lib/api";
import { getSessionCookieHeader } from "@/lib/server-auth";
import { formatCurrency } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Empleados",
};

function EmployeeStatus({ isActive }: { isActive: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${
        isActive
          ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
          : "bg-slate-100 text-slate-600 ring-slate-200"
      }`}
    >
      {isActive ? "Activo" : "Inactivo"}
    </span>
  );
}

export default async function EmployeesPage() {
  const cookieHeader = await getSessionCookieHeader();

  let employees: Employee[] = [];
  let error: string | null = null;

  try {
    employees = await getEmployees(cookieHeader);
  } catch (cause) {
    error =
      cause instanceof Error
        ? cause.message
        : "No se pudo consultar el listado de empleados.";
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          Empleados
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Personas vinculadas a la empresa y salario base usado para liquidar la
          nómina.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Nuevo Empleado</CardTitle>
          <CardDescription>
            Registra un empleado con documento único, fecha de inicio y salario
            base. El email es opcional.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <EmployeeForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Listado</CardTitle>
          <CardDescription>
            {error
              ? "No fue posible obtener los datos."
              : `${employees.length} empleado${employees.length === 1 ? "" : "s"} registrado${employees.length === 1 ? "" : "s"}.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
          ) : employees.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                Todavía no hay empleados
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa el formulario de arriba para registrar el primer empleado.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">Listado de empleados</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Documento</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead className="text-right">Salario Base</TableHead>
                  <TableHead>Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {employees.map((employee) => (
                  <TableRow key={employee.id}>
                    <TableCell className="font-mono text-xs font-medium text-slate-950">
                      {employee.document}
                    </TableCell>
                    <TableCell className="font-medium text-slate-950">
                      {employee.first_name} {employee.last_name}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums text-slate-950">
                      {formatCurrency(employee.base_salary)}
                    </TableCell>
                    <TableCell>
                      <EmployeeStatus isActive={employee.is_active} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
