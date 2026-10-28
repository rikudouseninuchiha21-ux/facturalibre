import type { Metadata } from "next";

import { RegisterForm } from "@/components/auth/RegisterForm";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Registro inicial",
};

export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-violet-100 via-violet-50 to-white px-4 py-16">
      <Card className="w-full max-w-lg shadow-xl shadow-violet-500/5">
        <CardHeader>
          <CardTitle>Crear administrador inicial</CardTitle>
          <CardDescription>
            El registro público solo está disponible mientras no exista ningún
            usuario. Después de crear el primero, el alta de más usuarios
            requiere una funcionalidad administrativa pendiente.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RegisterForm />
        </CardContent>
      </Card>
    </div>
  );
}
