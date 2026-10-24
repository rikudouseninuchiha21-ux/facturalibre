"use client";

import Link from "next/link";

import {
  BarChart3,
  CreditCard,
  FileText,
  GraduationCap,
  Mail,
  Package,
  Phone,
  ShieldCheck,
  ShoppingCart,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* ====================== HERO ====================== */}
      <section className="flex-1 relative overflow-hidden bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-20 md:py-32">
          <div className="text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600 uppercase tracking-wider">
              ERP para empresas en Colombia
            </span>

            <h1 className="mt-6 text-5xl font-extrabold tracking-tight text-zinc-950 sm:text-6xl lg:text-7xl">
              El ERP que tu<br />
              <span className="text-indigo-600">empresa necesita</span>
            </h1>

            <p className="mt-6 max-w-2xl mx-auto text-lg text-zinc-600 leading-relaxed sm:text-xl">
              Facturación electrónica, inventario, nómina, punto de venta y
              contabilidad en una sola plataforma. Diseñado para cumplir con la
              normativa DIAN y crecer contigo.
            </p>

            <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/login"
                className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-8 py-4 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all hover:bg-indigo-700 hover:shadow-indigo-500/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/30 active:scale-95"
              >
                Iniciar Sesión
              </Link>
              <Link
                href="/register"
                className="flex items-center justify-center gap-2 rounded-xl border border-zinc-200 bg-white px-8 py-4 text-sm font-semibold text-zinc-900 shadow-sm transition-all hover:bg-zinc-50 hover:border-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500/30 active:scale-95"
              >
                Crear cuenta
              </Link>
            </div>
          </div>
        </div>

        {/* Decorative grid accent */}
        <div className="absolute inset-0 -z-10 opacity-30">
          <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_60%_50%_at_50%_0%,var(--tw-gradient-stops))] from-indigo-100 via-transparent to-transparent" />
        </div>
      </section>

      {/* ====================== FEATURES ====================== */}
      <section className="bg-zinc-50 border-t border-zinc-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-20 md:py-28">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-zinc-950 sm:text-4xl">
              Todo lo que tu negocio necesita
            </h2>
            <p className="mt-4 text-lg text-zinc-600">
              Módulos integrados para operar, facturar y contabilizar sin
              fricción.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {[
              {
                title: "Facturación Electrónica",
                description:
                  "Emite y recibe facturas válidas ante la DIAN, con control de pagos y saldo pendiente.",
                icon: FileText,
              },
              {
                title: "Inventario",
                description:
                  "Controla stock por producto y bodega, con entradas, salidas y ajustes en tiempo real.",
                icon: Package,
              },
              {
                title: "Nómina",
                description:
                  "Abre periodos mensuales, calcula deducciones y consulta el estado del cierre.",
                icon: GraduationCap,
              },
              {
                title: "Punto de Venta (POS)",
                description:
                  "Vende rápido desde el mostrador con cobro inmediato y generación de factura.",
                icon: ShoppingCart,
              },
              {
                title: "Compras",
                description:
                  "Registra facturas de proveedores, controla pagos y mantén el al día el inventario.",
                icon: CreditCard,
              },
              {
                title: "Contabilidad (PUC)",
                description:
                  "Plan de cuentas único, asientos contables y estados financieros automatizados.",
                icon: BarChart3,
              },
            ].map((feature) => (
              <Link
                key={feature.title}
                href="/dashboard"
                className="group block"
              >
                <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm hover:border-indigo-300 hover:shadow-md transition-all">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                    <feature.icon className="size-5" />
                  </div>
                  <h3 className="mt-5 text-xl font-semibold tracking-tight text-zinc-950 group-hover:text-indigo-600 transition-colors">
                    {feature.title}
                  </h3>
                  <p className="mt-3 text-sm text-zinc-500 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </Link>
            ))}
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-3 items-center border-t border-zinc-200 pt-12">
            <div className="flex flex-col items-center gap-2 text-center sm:text-left">
              <Mail className="size-5 text-zinc-400" />
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                  Soporte
                </p>
                <p className="text-sm font-medium text-zinc-900">
                  soporte@nexuserp.co
                </p>
              </div>
            </div>
            <div className="flex flex-col items-center gap-2 text-center sm:text-left">
              <Phone className="size-5 text-zinc-400" />
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                  Teléfono
                </p>
                <p className="text-sm font-medium text-zinc-900">+57 300 000 0000</p>
              </div>
            </div>
            <div className="flex flex-col items-center gap-2 text-center sm:text-left">
              <ShieldCheck className="size-5 text-zinc-400" />
              <div>
                <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                  Cumplimiento
                </p>
                <p className="text-sm font-medium text-zinc-900">DIAN Ready</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ====================== FOOTER ====================== */}
      <footer className="border-t border-zinc-200 bg-white py-8">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="size-6 rounded-full bg-indigo-600 text-xs font-bold text-white flex items-center justify-center">
              N
            </div>
            <span className="text-sm font-semibold text-zinc-900">Nexus ERP</span>
          </div>
          <p className="text-sm text-zinc-500">
            © 2026 Nexus ERP. Todos los derechos reservados.
          </p>
        </div>
      </footer>
    </div>
  );
}
