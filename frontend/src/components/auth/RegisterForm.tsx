"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, login, register } from "@/lib/api";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const MIN_PASSWORD_LENGTH = 8;

export function RegisterForm() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedName = fullName.trim();
    const trimmedEmail = email.trim();

    if (!trimmedName) {
      setError("El nombre completo es obligatorio.");
      return;
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(
        `La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`,
      );
      return;
    }
    if (password !== passwordConfirmation) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await register({
        full_name: trimmedName,
        email: trimmedEmail,
        password,
      });
      // El registro no crea sesión; se inicia inmediatamente para dejar al
      // administrador dentro del dashboard.
      await login({ email: trimmedEmail, password });
      router.replace("/dashboard");
      router.refresh();
    } catch (cause) {
      if (cause instanceof ApiError) {
        setError(cause.message);
      } else {
        setError("No se pudo crear el usuario. Revisa tu conexión.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="register-full-name"
          className="block text-sm font-medium text-slate-700"
        >
          Nombre completo
        </label>
        <input
          id="register-full-name"
          name="full_name"
          type="text"
          required
          maxLength={200}
          autoComplete="name"
          autoFocus
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          disabled={isSubmitting}
          className={inputClassName}
          placeholder="Administrador Inicial"
        />
      </div>

      <div>
        <label
          htmlFor="register-email"
          className="block text-sm font-medium text-slate-700"
        >
          Email
        </label>
        <input
          id="register-email"
          name="email"
          type="email"
          required
          maxLength={254}
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={isSubmitting}
          className={inputClassName}
          placeholder="admin@empresa.com"
        />
      </div>

      <div>
        <label
          htmlFor="register-password"
          className="block text-sm font-medium text-slate-700"
        >
          Contraseña
        </label>
        <input
          id="register-password"
          name="password"
          type="password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          maxLength={72}
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={isSubmitting}
          className={inputClassName}
          placeholder="Mínimo 8 caracteres"
        />
      </div>

      <div>
        <label
          htmlFor="register-password-confirmation"
          className="block text-sm font-medium text-slate-700"
        >
          Confirmar contraseña
        </label>
        <input
          id="register-password-confirmation"
          name="password_confirmation"
          type="password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          maxLength={72}
          autoComplete="new-password"
          value={passwordConfirmation}
          onChange={(event) => setPasswordConfirmation(event.target.value)}
          disabled={isSubmitting}
          className={inputClassName}
          placeholder="Repite la contraseña"
        />
      </div>

      {error ? (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {error}
        </p>
      ) : null}

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Creando usuario..." : "Crear Administrador"}
      </Button>

      <p className="text-center text-sm text-slate-600">
        ¿Ya tienes cuenta?{" "}
        <Link
          href="/login"
          className="font-semibold text-violet-600 hover:text-violet-700"
        >
          Iniciar sesión
        </Link>
      </p>
    </form>
  );
}
