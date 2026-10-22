import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const sections = [
  {
    href: "/contacts",
    title: "Contactos",
    description:
      "Consulta los clientes y proveedores registrados en el backend.",
  },
  {
    href: "/invoices",
    title: "Facturas",
    description:
      "Revisa el estado, el total y el saldo pendiente de cada factura.",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-8">
      <section className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-widest text-blue-600">
          Facturación electrónica
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
          FacturaLibre - MVP
        </h1>
        <p className="mt-3 text-base leading-7 text-slate-600">
          Interfaz administrativa mínima para consultar la información
          gestionada por la API. Esta primera parte del frontend prioriza el
          listado de datos; los formularios y la autenticación llegan en fases
          posteriores.
        </p>
      </section>

      <section aria-labelledby="accesos-rapidos">
        <h2 id="accesos-rapidos" className="sr-only">
          Accesos rápidos
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {sections.map((section) => (
            <Link
              key={section.href}
              href={section.href}
              className="group block h-full"
            >
              <Card className="h-full transition duration-200 group-hover:-translate-y-0.5 group-hover:border-blue-300 group-hover:shadow-md">
                <CardHeader>
                  <CardTitle>{section.title}</CardTitle>
                  <CardDescription>{section.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-sm font-semibold text-blue-600 group-hover:text-blue-700">
                    Ver listado <span aria-hidden="true">→</span>
                  </span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Estado de la fase</CardTitle>
          <CardDescription>
            Scaffold de Next.js con App Router, TypeScript, Tailwind CSS y
            componentes reutilizables.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
            <li>Consulta de contactos y facturas desde el backend.</li>
            <li>Proxy same-origin para evitar CORS en el navegador.</li>
            <li>Sin formularios de creación o edición.</li>
            <li>Sin autenticación ni estado global.</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
