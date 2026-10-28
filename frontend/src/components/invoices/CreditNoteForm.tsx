"use client";

import { useRouter } from "next/navigation";
import {
  useMemo,
  useReducer,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ApiError,
  createCreditNote,
  type CreditNoteCreateInput,
  type Invoice,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const fieldClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

const numberFieldClassName = `${fieldClassName} tabular-nums`;

type DraftLineField =
  | "description"
  | "quantity"
  | "unitPrice"
  | "taxRate";

interface DraftLine {
  key: string;
  invoiceLineId: string;
  description: string;
  quantity: string;
  unitPrice: string;
  taxRate: string;
}

type DraftLineAction =
  | { type: "add"; key: string }
  | { type: "remove"; key: string }
  | {
      type: "update";
      key: string;
      field: DraftLineField;
      value: string;
    };

interface CreditNoteFormProps {
  invoice: Invoice;
  onClose: () => void;
}

function createBlankLine(key: string): DraftLine {
  return {
    key,
    invoiceLineId: "",
    description: "",
    quantity: "1",
    unitPrice: "0",
    taxRate: "0",
  };
}

function generateUuidV4(): string {
  return crypto.randomUUID();
}

const initialLines: DraftLine[] = [createBlankLine("initial-line")];

function linesReducer(
  state: DraftLine[],
  action: DraftLineAction,
): DraftLine[] {
  switch (action.type) {
    case "add":
      return [...state, createBlankLine(action.key)];
    case "remove":
      return state.filter((line) => line.key !== action.key);
    case "update":
      return state.map((line) =>
        line.key === action.key
          ? { ...line, [action.field]: action.value }
          : line,
      );
  }
}

function parseNumber(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function roundMoney(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function calculateLineAmounts(line: DraftLine): {
  subtotal: number;
  tax: number;
  total: number;
} {
  const quantity = parseNumber(line.quantity);
  const unitPrice = parseNumber(line.unitPrice);
  const taxRate = parseNumber(line.taxRate);

  const subtotal = roundMoney(quantity * unitPrice);
  const tax = roundMoney((subtotal * taxRate) / 100);

  return {
    subtotal,
    tax,
    total: roundMoney(subtotal + tax),
  };
}

function money(value: number): string {
  return formatCurrency(String(value), "COP");
}

export function CreditNoteForm({
  invoice,
  onClose,
}: CreditNoteFormProps) {
  const router = useRouter();
  const [lines, dispatch] = useReducer(linesReducer, initialLines);
  const [issueDate, setIssueDate] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const idempotencyKeyRef = useRef<string | null>(null);

  const lineAmounts = useMemo(
    () => lines.map((line) => calculateLineAmounts(line)),
    [lines],
  );

  const totals = useMemo(
    () =>
      lineAmounts.reduce(
        (accumulator, line) => ({
          subtotal: roundMoney(accumulator.subtotal + line.subtotal),
          tax: roundMoney(accumulator.tax + line.tax),
          total: roundMoney(accumulator.total + line.total),
        }),
        { subtotal: 0, tax: 0, total: 0 },
      ),
    [lineAmounts],
  );

  const maxBalance = Number(invoice.balance);

  function markFormChanged(): void {
    idempotencyKeyRef.current = null;
    setError(null);
  }

  function dispatchLineAction(action: DraftLineAction): void {
    markFormChanged();
    dispatch(action);
  }

  function handleIssueDateChange(value: string): void {
    markFormChanged();
    setIssueDate(value);
  }

  function validateDraft(): string | null {
    if (!issueDate) {
      return "La fecha de emisión es obligatoria.";
    }
    if (lines.length === 0) {
      return "Agrega al menos una línea a la nota crédito.";
    }

    for (const [index, line] of lines.entries()) {
      if (!line.description.trim()) {
        return `Línea ${index + 1}: la descripción es obligatoria.`;
      }

      const quantity = parseNumber(line.quantity);
      if (!Number.isFinite(quantity) || quantity <= 0) {
        return `Línea ${index + 1}: la cantidad debe ser mayor que cero.`;
      }

      const unitPrice = parseNumber(line.unitPrice);
      if (!Number.isFinite(unitPrice) || unitPrice < 0) {
        return `Línea ${index + 1}: el precio unitario no puede ser negativo.`;
      }

      const taxRate = parseNumber(line.taxRate);
      if (!Number.isFinite(taxRate) || taxRate < 0 || taxRate > 100) {
        return `Línea ${index + 1}: la tasa de impuesto debe estar entre 0 y 100.`;
      }
    }

    const total = totals.total;
    if (total > maxBalance) {
      return `El total de la nota crédito (${money(total)}) excede el balance pendiente de la factura (${money(maxBalance)}).`;
    }

    return null;
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    const validationError = validateDraft();
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const idempotencyKey =
        idempotencyKeyRef.current ?? generateUuidV4();
      idempotencyKeyRef.current = idempotencyKey;

      const payload: CreditNoteCreateInput = {
        issue_date: issueDate,
        lines: lines.map((line) => ({
          invoice_line_id: line.invoiceLineId || undefined,
          description: line.description.trim(),
          quantity: line.quantity.trim(),
          unit_price: line.unitPrice.trim() || "0",
          tax_rate: line.taxRate.trim() || "0",
        })),
      };

      await createCreditNote(invoice.id, payload, idempotencyKey);
      idempotencyKeyRef.current = null;
      router.refresh();
      onClose();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo crear la nota crédito: ${cause.message}`
          : "No se pudo crear la nota crédito. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Datos generales</CardTitle>
          <CardDescription>
            Selecciona la fecha de emisión y las líneas a devolver.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 lg:grid-cols-4">
            <div className="lg:col-span-2">
              <label
                htmlFor="credit-note-issue-date"
                className="block text-sm font-medium text-slate-700"
              >
                Fecha de emisión{" "}
                <span className="text-red-600" aria-hidden="true">
                  *
                </span>
              </label>
              <input
                id="credit-note-issue-date"
                name="issue_date"
                type="date"
                required
                value={issueDate}
                onChange={(event) => handleIssueDateChange(event.target.value)}
                disabled={isSubmitting}
                className={fieldClassName}
              />
            </div>
            <div className="flex items-end">
              <span className="text-sm font-medium text-slate-600">
                Balance disponible:
              </span>
              <span className="ml-2 text-lg font-semibold tabular-nums text-slate-950">
                {money(maxBalance)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Líneas a devolver</CardTitle>
            <CardDescription>
              La cantidad devuelta no puede exceder la cantidad original de
              cada línea de la factura.
            </CardDescription>
          </div>
          <button
            type="button"
            onClick={() => dispatchLineAction({ type: "add", key: generateUuidV4() })}
            disabled={isSubmitting}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span aria-hidden="true">+</span>
            Agregar Línea
          </button>
        </CardHeader>
        <CardContent className="space-y-4">
          {lines.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <p className="font-medium text-slate-700">
                La nota crédito no tiene líneas
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Usa “Agregar Línea” para incluir al menos una línea.
              </p>
            </div>
          ) : (
            lines.map((line, index) => {
              const amounts = lineAmounts[index] ?? {
                subtotal: 0,
                tax: 0,
                total: 0,
              };

              return (
                <article
                  key={line.key}
                  className="rounded-2xl border border-slate-200 bg-slate-50/60 p-4"
                >
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold text-slate-800">
                      Línea {index + 1}
                    </h3>
                    <button
                      type="button"
                      onClick={() =>
                        dispatchLineAction({ type: "remove", key: line.key })
                      }
                      disabled={isSubmitting}
                      aria-label={`Eliminar línea ${index + 1}`}
                      className="rounded-md px-2 py-1 text-xs font-semibold text-red-600 transition-colors hover:bg-red-50 hover:text-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Eliminar Línea
                    </button>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
                    <div className="xl:col-span-4">
                      <label
                        htmlFor={`cn-line-${line.key}-description`}
                        className="block text-xs font-semibold uppercase tracking-wide text-slate-500"
                      >
                        Descripción{" "}
                        <span className="text-red-600" aria-hidden="true">
                          *
                        </span>
                      </label>
                      <input
                        id={`cn-line-${line.key}-description`}
                        type="text"
                        value={line.description}
                        onChange={(event) =>
                          dispatchLineAction({
                            type: "update",
                            key: line.key,
                            field: "description",
                            value: event.target.value,
                          })
                        }
                        disabled={isSubmitting}
                        className={fieldClassName}
                        placeholder="Descripción del producto devuelto"
                      />
                    </div>

                    <div className="xl:col-span-2">
                      <label
                        htmlFor={`cn-line-${line.key}-quantity`}
                        className="block text-xs font-semibold uppercase tracking-wide text-slate-500"
                      >
                        Cantidad{" "}
                        <span className="text-red-600" aria-hidden="true">
                          *
                        </span>
                      </label>
                      <input
                        id={`cn-line-${line.key}-quantity`}
                        type="number"
                        min="0.0001"
                        step="0.0001"
                        inputMode="decimal"
                        required
                        value={line.quantity}
                        onChange={(event) =>
                          dispatchLineAction({
                            type: "update",
                            key: line.key,
                            field: "quantity",
                            value: event.target.value,
                          })
                        }
                        disabled={isSubmitting}
                        className={numberFieldClassName}
                      />
                    </div>

                    <div className="xl:col-span-3">
                      <label
                        htmlFor={`cn-line-${line.key}-unit-price`}
                        className="block text-xs font-semibold uppercase tracking-wide text-slate-500"
                      >
                        Precio unitario{" "}
                        <span className="text-red-600" aria-hidden="true">
                          *
                        </span>
                      </label>
                      <input
                        id={`cn-line-${line.key}-unit-price`}
                        type="number"
                        min="0"
                        step="0.01"
                        inputMode="decimal"
                        required
                        value={line.unitPrice}
                        onChange={(event) =>
                          dispatchLineAction({
                            type: "update",
                            key: line.key,
                            field: "unitPrice",
                            value: event.target.value,
                          })
                        }
                        disabled={isSubmitting}
                        className={numberFieldClassName}
                      />
                    </div>

                    <div className="xl:col-span-3">
                      <label
                        htmlFor={`cn-line-${line.key}-tax-rate`}
                        className="block text-xs font-semibold uppercase tracking-wide text-slate-500"
                      >
                        Tasa de impuesto %
                      </label>
                      <input
                        id={`cn-line-${line.key}-tax-rate`}
                        type="number"
                        min="0"
                        max="100"
                        step="0.0001"
                        inputMode="decimal"
                        value={line.taxRate}
                        onChange={(event) =>
                          dispatchLineAction({
                            type: "update",
                            key: line.key,
                            field: "taxRate",
                            value: event.target.value,
                          })
                        }
                        disabled={isSubmitting}
                        className={numberFieldClassName}
                      />
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap justify-end gap-x-6 gap-y-1 border-t border-slate-200 pt-3 text-sm">
                    <span className="text-slate-500">
                      Subtotal:{" "}
                      <span className="font-medium tabular-nums text-slate-800">
                        {money(amounts.subtotal)}
                      </span>
                    </span>
                    <span className="text-slate-500">
                      Impuesto:{" "}
                      <span className="font-medium tabular-nums text-slate-800">
                        {money(amounts.tax)}
                      </span>
                    </span>
                    <span className="text-slate-700">
                      Total línea:{" "}
                      <span className="font-semibold tabular-nums text-slate-950">
                        {money(amounts.total)}
                      </span>
                    </span>
                  </div>
                </article>
              );
            })
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Resumen</CardTitle>
          <CardDescription>
            Cálculo preliminar en el navegador. El backend vuelve a calcular y
            redondear los importes al guardar.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="ml-auto max-w-md space-y-2 text-sm">
            <div className="flex items-center justify-between gap-4 text-slate-600">
              <span>Subtotal general</span>
              <span className="font-medium tabular-nums text-slate-950">
                {money(totals.subtotal)}
              </span>
            </div>
            <div className="flex items-center justify-between gap-4 text-slate-600">
              <span>Total impuestos</span>
              <span className="font-medium tabular-nums text-slate-950">
                {money(totals.tax)}
              </span>
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-slate-200 pt-2 text-base font-semibold text-slate-950">
              <span>Total nota crédito</span>
              <span className="tabular-nums">{money(totals.total)}</span>
            </div>
            <p className="text-right text-xs font-medium uppercase tracking-wide text-slate-400">
              Moneda: COP
            </p>
          </div>

          {error ? (
            <div
              id="credit-note-form-error"
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {error}
            </div>
          ) : null}

          <div className="flex flex-wrap justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancelar
            </button>
            <Button
              type="submit"
              disabled={isSubmitting}
              aria-describedby={error ? "credit-note-form-error" : undefined}
            >
              {isSubmitting
                ? "Guardando..."
                : "Guardar Nota Crédito (Borrador)"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </form>
  );
}
