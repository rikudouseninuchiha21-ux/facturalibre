"use client";

import { useState, useEffect } from "react";

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
  getUsers,
  updateUser,
  type UserItem,
} from "@/lib/api";

interface UserRowProps {
  user: UserItem;
  isCurrentUser?: boolean;
  onToggle: (userId: string, isActive: boolean) => Promise<void>;
}

function UserRow({ user, isCurrentUser = false, onToggle }: UserRowProps) {
  const [isUpdating, setIsUpdating] = useState(false);

  const handleToggle = async () => {
    setIsUpdating(true);
    try {
      await onToggle(user.id, !user.is_active);
    } finally {
      setIsUpdating(false);
    }
  };

  const roleLabel: Record<string, string> = {
    ADMIN: "Administrador",
    issued: "Emitida",
    void: "Anulada",
    ACCOUNTANT: "Contador",
    CASHIER: "Cajero",
  };

  const statusClass = user.is_active ? "text-emerald-600" : "text-red-600";
  const statusLabel = user.is_active ? "Activo" : "Inactivo";
  const buttonClass = user.is_active
    ? "border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700"
    : "border-emerald-200 text-emerald-700 hover:bg-emerald-50 hover:text-emerald-700";

  return (
    <TableRow key={user.id}>
      <TableCell className="text-zinc-900">{user.full_name}</TableCell>
      <TableCell className="text-zinc-900">{user.email}</TableCell>
      <TableCell className="text-zinc-900">
        <span className="px-2 py-1 rounded text-xs font-medium">
          {roleLabel[user.role] || user.role}
        </span>
      </TableCell>
      <TableCell className="text-zinc-900">
        <span className={`font-medium ${statusClass}`}>
          {statusLabel}
        </span>
      </TableCell>
      <TableCell className="text-right">
        {isCurrentUser ? (
          <span className="text-xs text-zinc-500">Tú</span>
        ) : (
          <button
            type="button"
            onClick={handleToggle}
            disabled={isUpdating}
            className={`inline-flex items-center justify-center rounded-md px-3 py-1 text-xs font-bold transition-colors ${buttonClass}`}
          >
            {user.is_active ? "Desactivar" : "Activar"}
          </button>
        )}
      </TableCell>
    </TableRow>
  );
}

export default function UsersPage() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function handleToggleUser(
    userId: string,
    isActive: boolean,
  ): Promise<void> {
    try {
      await updateUser(userId, { is_active: !isActive });
      setUsers((prev) =>
        prev.map((u) =>
          u.id === userId ? { ...u, is_active: !isActive } : u,
        ),
      );
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo actualizar el usuario.",
      );
    }
  }

  useEffect(() => {
    let isMounted = true;

    async function load() {
      setIsLoading(true);
      try {
        const usersData = await getUsers();
        if (isMounted) {
          setUsers(usersData);
        }
      } catch (cause) {
        if (isMounted) {
          setError(
            cause instanceof ApiError
              ? cause.message
              : "No se pudo cargar la lista de usuarios.",
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-950">
            Gestión de Usuarios
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Administra los usuarios del sistema. Solo los administradores
            pueden crear, editar y desactivar usuarios.
          </p>
        </div>
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
          <CardTitle>Usuarios Registrados</CardTitle>
          <CardDescription>
            Lista de usuarios del sistema con su estado y rol.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <caption className="sr-only">Usuarios del sistema</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Rol</TableHead>
                  <TableHead className="text-right">Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-zinc-500 py-8">
                      Cargando usuarios...
                    </TableCell>
                  </TableRow>
                ) : users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-zinc-500 py-8">
                      No hay usuarios registrados.
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <UserRow
                      key={user.id}
                      user={user}
                      isCurrentUser={false}
                      onToggle={handleToggleUser}
                    />
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
