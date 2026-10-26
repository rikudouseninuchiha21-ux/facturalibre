"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowRight, Download, Filter, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
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
import type { AgingReport, CustomerAging } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

const inputClassName =
  "block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-amber-600 focus:ring-2 focus:ring-amber-500/10";

const BUCKET_OPTIONS = [
  { value: "all", label: "Todos los clientes" },
  { value: "current", label: "Con cartera corriente" },
  { value: "d0_30", label: "Vencido 0 – 30 días" },
  { value: "d31_60", label: "Vencido 31 – 60 días" },
  { value: "d61_90", label: "Vencido 61 – 90 días" },
  { value: "d91_120", label: "Vencido 91 – 120 días" },
  { value: "d120_plus", label: "Vencido 120+ días" },
] as const;

type BucketFilter = (typeof BUCKET_OPTIONS)[number]["value"];

interface AgingClientProps {
  initialReport: AgingReport;
}

function csvCell(value: string): string {
  return `"${value.replaceAll('"', '""')}"`;
}

function hasBucket(row: CustomerAging, bucket: BucketFilter): boolean {
  if (bucket === "all") return true;
  if (bucket === "current") return Number(row.current) > 0;
  return Number(row[bucket]) > 0;
}

export function AgingClient({ initialReport }: AgingClientProps) {
  const router = useRouter();
  const [asOfDate, setAsOfDate] = useState(initialReport.as_of_date);
  const [search, setSearch] = useState("");
  const [bucket, setBucket] = useState<BucketFilter>("all");

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return initialReport.by_customer.filter((row) => {
      if (!hasBucket(row, bucket)) return false;
      if (term && !row.contact_name.toLowerCase().includes(term)) return false;
      return true;
    });
  }, [initialReport.by_customer, search, bucket]);

  const filteredTotal = useMemo(
    () =>
      filtered.reduce((sum, row) => sum + Number(row.total), 0).toFixed(2),
    [filtered],
  );

  function applyDate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    router.push(
      asOfDate
        ? `/receivables/aging?as_of_date=${encodeURIComponent(asOfDate)}`
        : "/receivables/aging",
    );
  }

  function exportCsv() {
    const headers = [
      "Cliente",
      "Corriente",
      "0-30",
      "31-60",
      "61-90",
      "91-120",
      "120+",
      "Total",
      "Facturas",
    ];
    const lines = [
      headers.map(csvCell).join(","),
      ...filtered.map((row) =>
        [
          row.contact_name,
          row.current,
          row.d0_30,
          row.d31_60,
          row.d61_90,
          row.d91_120,
          row.d120_plus,
          row.total,
          String(row.invoice_count),
        ]
          .map(csvCell)
          .join(","),
      ),
    ];
    const blob = new Blob([`\uFEFF${lines.join("\n")}`], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `aging-cartera-${initialReport.as_of_date}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Filtros del reporte</CardTitle>
          <CardDescription>
            Fecha de corte, cliente y rango de vencimiento. El aging se calcula
            en el backend con los pagos y notas crédito reales.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={applyDate}
            className="grid gap-4 md:grid-cols-[1fr_1fr_auto]"
          >
            <div>
              <label
                htmlFor="aging-date"
                className="mb-1 block text-sm font-medium text-zinc-700"
              >
                Fecha de corte
              </label>
              <input
                id="aging-date"
                type="date"
                value={asOfDate}
                onChange={(event) => setAsOfDate(event.target.value)}
                className={inputClassName}
              />
            </div>
            <div>
              <label
                htmlFor="aging-bucket"
                className="mb-1 block text-sm font-medium text-zinc-700"
              >
                Rango
              </label>
              <select
                id="aging-bucket"
                value={bucket}
                onChange={(event) =>
                  setBucket(event.target.value as BucketFilter)
                }
                className={inputClassName}
              >
                {BUCKET_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <Button type="submit" className="w-full md:w-auto">
                <Filter className="mr-2 size-4" aria-hidden="true" />
                Aplicar fecha
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-zinc-950">
            Aging al {formatDate(initialReport.as_of_date)}
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            {filtered.length} de {initialReport.by_customer.length} clientes ·{" "}
            {formatCurrency(filteredTotal)} filtrado
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-400"
              aria-hidden="true"
            />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar cliente"
              aria-label="Buscar cliente"
              className={`${inputClassName} pl-9`}
            />
          </div>
          <Button onClick={exportCsv} className="bg-zinc-900 hover:bg-zinc-800">
            <Download className="mr-2 size-4" aria-hidden="true" />
            Exportar CSV
          </Button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white px-6 py-16 text-center">
          <Search className="size-10 text-amber-500" aria-hidden="true" />
          <p className="mt-3 font-semibold text-zinc-900">
            Sin clientes para este filtro
          </p>
          <p className="mt-1 max-w-md text-sm text-zinc-500">
            Ajusta el rango, la búsqueda o la fecha de corte para ver cartera
            pendiente.
          </p>
        </div>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Cliente</TableHead>
                  <TableHead className="text-right">Corriente</TableHead>
                  <TableHead className="text-right">0 – 30</TableHead>
                  <TableHead className="text-right">31 – 60</TableHead>
                  <TableHead className="text-right">61 – 90</TableHead>
                  <TableHead className="text-right">91 – 120</TableHead>
                  <TableHead className="text-right">120+</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Facturas</TableHead>
                  <TableHead className="text-right">Detalle</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((row) => (
                  <TableRow key={row.contact_id}>
                    <TableCell className="min-w-44 font-medium text-zinc-900">
                      {row.contact_name}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-emerald-700">
                      {formatCurrency(row.current)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-amber-700">
                      {formatCurrency(row.d0_30)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-amber-800">
                      {formatCurrency(row.d31_60)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-orange-700">
                      {formatCurrency(row.d61_90)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-red-600">
                      {formatCurrency(row.d91_120)}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums text-red-700">
                      {formatCurrency(row.d120_plus)}
                    </TableCell>
                    <TableCell className="text-right font-bold tabular-nums text-zinc-950">
                      {formatCurrency(row.total)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-zinc-600">
                      {row.invoice_count}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link
                        href={`/receivables/customers/${row.contact_id}`}
                        className="inline-flex items-center gap-1 text-sm font-semibold text-amber-700 hover:text-amber-900"
                      >
                        Ver
                        <ArrowRight className="size-3.5" aria-hidden="true" />
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
