"use client";

import { useState, type FormEvent } from "react";

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
import {
  ApiError,
  createFixedAsset,
  depreciateFixedAsset,
  type FixedAsset,
  type FixedAssetCreateInput,
} from "@/lib/api";
import { formatCurrency, formatMonth } from "@/lib/format";

const inputClassName =
  "mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 shadow-sm outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-500";

const numberFieldClassName = `${inputClassName} tabular-nums`;

interface AssetsClientProps {
  initialAssets: FixedAsset[];
  initialError: string | null;
  currentMonth: number;
  currentYear: number;
  today: string;
}

function statusBadge(asset: FixedAsset) {
  if (asset.status === "DISPOSED") {
    return (
      <span className="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-semibold text-zinc-600 ring-1 ring-inset ring-zinc-200">
        Dado de baja
      </span>
    );
  }

  if (asset.is_fully_depreciated) {
    return (
      <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800 ring-1 ring-inset ring-amber-200">
        Totalmente depreciado
      </span>
    );
  }

  return (
    <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
      Activo
    </span>
  );
}

function totalOf(
  assets: FixedAsset[],
  field: "initial_cost" | "accumulated_depreciation" | "current_value",
): string {
  const total = assets.reduce((sum, asset) => sum + Number(asset[field]), 0);
  return Number.isFinite(total) ? total.toFixed(2) : "0.00";
}

export function AssetsClient({
  initialAssets,
  initialError,
  currentMonth,
  currentYear,
  today,
}: AssetsClientProps) {
  const [assets, setAssets] = useState<FixedAsset[]>(initialAssets);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(today);
  const [initialCost, setInitialCost] = useState("");
  const [salvageValue, setSalvageValue] = useState("0.00");
  const [usefulLifeMonths, setUsefulLifeMonths] = useState("12");
  const [error, setError] = useState<string | null>(initialError);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [depreciatingId, setDepreciatingId] = useState<string | null>(null);

  const totalCost = totalOf(assets, "initial_cost");
  const totalAccumulated = totalOf(assets, "accumulated_depreciation");
  const totalCurrent = totalOf(assets, "current_value");

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedCode = code.trim();
    const trimmedName = name.trim();
    const trimmedCost = initialCost.trim();
    const trimmedSalvage = salvageValue.trim();
    const trimmedLife = usefulLifeMonths.trim();

    if (!trimmedCode || !trimmedName || !purchaseDate) {
      setError("Código, nombre y fecha de compra son obligatorios.");
      setSuccess(null);
      return;
    }

    const numericCost = Number(trimmedCost);
    const numericSalvage = Number(trimmedSalvage);
    const numericLife = Number(trimmedLife);

    if (!Number.isFinite(numericCost) || numericCost <= 0) {
      setError("El costo inicial debe ser un número mayor que cero.");
      setSuccess(null);
      return;
    }

    if (!Number.isFinite(numericSalvage) || numericSalvage < 0) {
      setError("El valor de salvamento debe ser un número mayor o igual a cero.");
      setSuccess(null);
      return;
    }

    if (numericSalvage >= numericCost) {
      setError("El valor de salvamento debe ser menor que el costo inicial.");
      setSuccess(null);
      return;
    }

    if (!Number.isInteger(numericLife) || numericLife <= 0) {
      setError("La vida útil debe ser un número entero de meses mayor que cero.");
      setSuccess(null);
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      const payload: FixedAssetCreateInput = {
        code: trimmedCode,
        name: trimmedName,
        purchase_date: purchaseDate,
        initial_cost: trimmedCost,
        salvage_value: trimmedSalvage,
        useful_life_months: numericLife,
      };
      const created = await createFixedAsset(payload);

      setAssets((previous) =>
        [...previous, created].sort((left, right) =>
          left.code.localeCompare(right.code),
        ),
      );
      setCode("");
      setName("");
      setPurchaseDate(today);
      setInitialCost("");
      setSalvageValue("0.00");
      setUsefulLifeMonths("12");
      setSuccess(`Activo ${created.code} registrado correctamente.`);
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo registrar el activo: ${cause.message}`
          : "No se pudo registrar el activo. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDepreciate(asset: FixedAsset): Promise<void> {
    setError(null);
    setSuccess(null);
    setDepreciatingId(asset.id);

    try {
      const updated = await depreciateFixedAsset(asset.id, {
        month: currentMonth,
        year: currentYear,
      });
      setAssets((previous) =>
        previous.map((item) => (item.id === updated.id ? updated : item)),
      );
      setSuccess(
        `Depreciación de ${formatMonth(currentMonth)} ${currentYear} registrada para ${updated.code}.`,
      );
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo depreciar el activo: ${cause.message}`
          : "No se pudo depreciar el activo. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setDepreciatingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-3xl border border-amber-500/20 bg-gradient-to-br from-zinc-950 via-zinc-900 to-amber-950 p-6 text-white shadow-xl shadow-amber-950/10 md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-2xl">
            <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-amber-300/80">
              Contabilidad · Activos fijos
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight md:text-4xl">
              Activos Fijos
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-zinc-300">
              Controla el costo, la depreciación acumulada y el valor neto de
              los bienes de la empresa con depreciación mensual por línea
              recta.
            </p>
          </div>
          <div className="rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-right">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-amber-200/80">
              Método contable
            </p>
            <p className="mt-1 text-lg font-semibold text-amber-200">
              Línea recta
            </p>
            <p className="mt-1 text-xs text-zinc-400">
              Débito 5160 · Crédito 1592
            </p>
          </div>
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 backdrop-blur">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-400">
              Costo total
            </p>
            <p className="mt-2 text-xl font-bold tabular-nums text-white">
              {formatCurrency(totalCost, "COP")}
            </p>
          </div>
          <div className="rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-amber-200/80">
              Depreciación acumulada
            </p>
            <p className="mt-2 text-xl font-bold tabular-nums text-amber-200">
              {formatCurrency(totalAccumulated, "COP")}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 backdrop-blur">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-400">
              Valor actual
            </p>
            <p className="mt-2 text-xl font-bold tabular-nums text-white">
              {formatCurrency(totalCurrent, "COP")}
            </p>
          </div>
        </div>
      </section>

      <Card className="border-amber-200/70 bg-gradient-to-br from-white via-amber-50/30 to-white shadow-md shadow-amber-500/5">
        <CardHeader>
          <CardTitle>Registrar activo fijo</CardTitle>
          <CardDescription>
            El costo, el valor de salvamento y la vida útil definen la cuota
            mensual. La fecha de compra debe ser anterior o igual al mes que se
            deprecia.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <div>
                <label
                  htmlFor="asset-code"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Código{" "}
                  <span className="text-amber-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="asset-code"
                  name="code"
                  type="text"
                  required
                  maxLength={50}
                  autoComplete="off"
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  disabled={isSubmitting}
                  className={inputClassName}
                  placeholder="Ej. VEH-001"
                />
              </div>

              <div className="md:col-span-1 xl:col-span-2">
                <label
                  htmlFor="asset-name"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Nombre{" "}
                  <span className="text-amber-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="asset-name"
                  name="name"
                  type="text"
                  required
                  maxLength={200}
                  autoComplete="off"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  disabled={isSubmitting}
                  className={inputClassName}
                  placeholder="Ej. Camioneta de reparto"
                />
              </div>

              <div>
                <label
                  htmlFor="asset-purchase-date"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Fecha de compra{" "}
                  <span className="text-amber-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="asset-purchase-date"
                  name="purchase_date"
                  type="date"
                  required
                  value={purchaseDate}
                  onChange={(event) => setPurchaseDate(event.target.value)}
                  disabled={isSubmitting}
                  className={inputClassName}
                />
              </div>

              <div>
                <label
                  htmlFor="asset-initial-cost"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Costo inicial{" "}
                  <span className="text-amber-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="asset-initial-cost"
                  name="initial_cost"
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  inputMode="decimal"
                  value={initialCost}
                  onChange={(event) => setInitialCost(event.target.value)}
                  disabled={isSubmitting}
                  className={numberFieldClassName}
                  placeholder="Ej. 12000000.00"
                />
              </div>

              <div>
                <label
                  htmlFor="asset-salvage-value"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Valor de salvamento
                </label>
                <input
                  id="asset-salvage-value"
                  name="salvage_value"
                  type="number"
                  min="0"
                  step="0.01"
                  inputMode="decimal"
                  value={salvageValue}
                  onChange={(event) => setSalvageValue(event.target.value)}
                  disabled={isSubmitting}
                  className={numberFieldClassName}
                  placeholder="0.00"
                />
              </div>

              <div>
                <label
                  htmlFor="asset-useful-life"
                  className="block text-sm font-medium text-zinc-700"
                >
                  Vida útil (meses){" "}
                  <span className="text-amber-600" aria-hidden="true">
                    *
                  </span>
                </label>
                <input
                  id="asset-useful-life"
                  name="useful_life_months"
                  type="number"
                  required
                  min="1"
                  step="1"
                  inputMode="numeric"
                  value={usefulLifeMonths}
                  onChange={(event) => setUsefulLifeMonths(event.target.value)}
                  disabled={isSubmitting}
                  className={numberFieldClassName}
                  placeholder="Ej. 60"
                />
              </div>
            </div>

            {error ? (
              <p
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              >
                {error}
              </p>
            ) : null}

            {success ? (
              <p
                role="status"
                className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
              >
                {success}
              </p>
            ) : null}

            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-gradient-to-r from-amber-500 to-amber-600 shadow-amber-500/30 hover:from-amber-400 hover:to-amber-500 sm:w-auto"
              >
                {isSubmitting ? "Registrando..." : "Registrar activo"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-zinc-200/80 shadow-sm">
        <CardHeader className="border-b border-zinc-100 bg-gradient-to-r from-zinc-50 via-white to-amber-50/50">
          <CardTitle>Portafolio de activos</CardTitle>
          <CardDescription>
            {assets.length === 0
              ? "Aún no hay activos registrados."
              : `${assets.length} activo${assets.length === 1 ? "" : "s"} registrado${assets.length === 1 ? "" : "s"}.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {assets.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-amber-200 bg-amber-50/40 px-6 py-12 text-center">
              <p className="font-semibold text-zinc-800">
                Tu portafolio de activos está vacío
              </p>
              <p className="mt-1 text-sm text-zinc-500">
                Usa el formulario superior para registrar el primer bien y
                comenzar a depreciarlo.
              </p>
            </div>
          ) : (
            <Table>
              <caption className="sr-only">
                Listado de activos fijos con su depreciación acumulada y valor
                actual
              </caption>
              <TableHeader>
                <TableRow className="bg-zinc-50/80">
                  <TableHead>Código</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead className="text-right">Costo</TableHead>
                  <TableHead className="text-right">
                    Depreciación acumulada
                  </TableHead>
                  <TableHead className="text-right">Valor actual</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acción</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {assets.map((asset) => {
                  const isBusy = depreciatingId === asset.id;
                  const cannotDepreciate =
                    asset.status !== "ACTIVE" || asset.is_fully_depreciated;

                  return (
                    <TableRow key={asset.id}>
                      <TableCell className="font-mono text-xs font-semibold text-amber-700">
                        {asset.code}
                      </TableCell>
                      <TableCell className="font-medium text-zinc-950">
                        <span className="block">{asset.name}</span>
                        <span className="mt-0.5 block text-xs font-normal text-zinc-400">
                          Compra: {asset.purchase_date} · {asset.useful_life_months} meses
                        </span>
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-zinc-800">
                        {formatCurrency(asset.initial_cost, "COP")}
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-medium text-amber-700">
                        {formatCurrency(asset.accumulated_depreciation, "COP")}
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-semibold text-zinc-950">
                        {formatCurrency(asset.current_value, "COP")}
                      </TableCell>
                      <TableCell>{statusBadge(asset)}</TableCell>
                      <TableCell className="text-right">
                        <button
                          type="button"
                          onClick={() => handleDepreciate(asset)}
                          disabled={isBusy || cannotDepreciate || depreciatingId !== null}
                          title={
                            cannotDepreciate
                              ? "El activo no está activo o ya está totalmente depreciado"
                              : `Depreciar ${formatMonth(currentMonth)} ${currentYear}`
                          }
                          className="inline-flex items-center justify-center rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800 shadow-sm transition-colors hover:border-amber-400 hover:bg-amber-100 disabled:cursor-not-allowed disabled:border-zinc-200 disabled:bg-zinc-50 disabled:text-zinc-400"
                        >
                          {isBusy ? "Depreciando..." : "Depreciar Mes Actual"}
                        </button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
