import type { Metadata } from "next";

import { LoginForm } from "@/components/auth/LoginForm";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Iniciar sesión",
};

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-violet-100 via-violet-50 to-white px-4 py-16">
      <div className="mb-8 flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-full bg-violet-600 text-sm font-bold text-white shadow-lg shadow-violet-500/30">
          V
        </div>
        <span className="text-2xl font-bold tracking-tight text-slate-950">
          VANTAGE
        </span>
      </div>
      <Card className="w-full max-w-md shadow-xl shadow-violet-500/10">
        <CardHeader>
          <CardTitle>Iniciar sesión</CardTitle>
          <CardDescription>
            Accede con el usuario administrador de VANTAGE. La sesión
            permanece activa durante 24 horas.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm />
        </CardContent>
      </Card>
    </div>
  );
}
