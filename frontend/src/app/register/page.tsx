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
    <div className="mx-auto w-full max-w-lg">
      <Card>
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
