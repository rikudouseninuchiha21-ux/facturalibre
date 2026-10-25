"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

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
  reconcileBankMovement,
  type BankAccount,
  type ReconciliationBankMovement,
  type ReconciliationCandidates,
  type ReconciliationTransactionCandidate,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

const transactionTypeLabels = {
  DEPOSIT: "Depósito",
  WITHDRAWAL: "Retiro",
  TRANSFER: "Transferencia",
} as const;

interface ReconciliationPanelProps {
  account: BankAccount;
  reconciliation: ReconciliationCandidates;
}

export function ReconciliationPanel({
  account,
  reconciliation,
}: ReconciliationPanelProps) {
  const router = useRouter();
  const [selectedMovementId, setSelectedMovementId] = useState<string | null>(
    null,
  );
  const [busyMatchKey, setBusyMatchKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedMovement =
    reconciliation.bank_movements.find(
      (movement) => movement.id === selectedMovementId,
    ) ?? null;

  function handleSelectMovement(movement: ReconciliationBankMovement): void {
    setSelectedMovementId(movement.id);
    setError(null);
  }

  async function handleMatch(
    movement: ReconciliationBankMovement,
    candidate: ReconciliationTransactionCandidate,
  ): Promise<void> {
    const matchKey = `${movement.id}:${candidate.id}`;
    setError(null);
    setBusyMatchKey(matchKey);

    try {
      await reconcileBankMovement(account.id, {
        bank_movement_id: movement.id,
        transaction_id: candidate.id,
      });
      setSelectedMovementId(null);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo conciliar: ${cause.message}`
          : "No se pudo conciliar. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setBusyMatchKey(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conciliación bancaria</CardTitle>
        <CardDescription>
          Selecciona un movimiento del banco y su pago o gasto compatible. Solo
          se muestran montos iguales con una diferencia máxima de 3 días.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error ? (
          <p
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {error}
          </p>
        ) : null}

        {reconciliation.bank_movements.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
            <p className="font-medium text-slate-700">
              No hay movimientos pendientes por conciliar
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Cuando registres un depósito o retiro sin contrapartida en el
              sistema, aparecerá aquí.
            </p>
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            <section className="overflow-hidden rounded-xl border border-slate-200">
              <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-900">
                  Movimientos del banco
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  {reconciliation.bank_movements.length} pendiente
                  {reconciliation.bank_movements.length === 1 ? "" : "s"}
                </p>
              </div>
              <ul className="divide-y divide-slate-100">
                {reconciliation.bank_movements.map((movement) => {
                  const isSelected = movement.id === selectedMovementId;
                  return (
                    <li key={movement.id}>
                      <button
                        type="button"
                        onClick={() => handleSelectMovement(movement)}
                        aria-pressed={isSelected}
                        className={`w-full px-4 py-3 text-left transition-colors ${
                          isSelected
                            ? "bg-amber-50"
                            : "bg-white hover:bg-slate-50"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                              {movement.date} ·{" "}
                              {transactionTypeLabels[movement.transaction_type]}
                            </p>
                            <p className="mt-1 truncate text-sm font-medium text-slate-900">
                              {movement.description}
                            </p>
                            {movement.reference ? (
                              <p className="mt-0.5 truncate text-xs text-slate-500">
                                Ref. {movement.reference}
                              </p>
                            ) : null}
                          </div>
                          <div className="shrink-0 text-right">
                            <p className="text-sm font-semibold tabular-nums text-slate-900">
                              {formatCurrency(movement.amount, account.currency)}
                            </p>
                            <span
                              className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${
                                movement.candidates.length > 0
                                  ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                                  : "bg-slate-100 text-slate-600 ring-slate-200"
                              }`}
                            >
                              {movement.candidates.length} candidato
                              {movement.candidates.length === 1 ? "" : "s"}
                            </span>
                          </div>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>

            <section className="overflow-hidden rounded-xl border border-slate-200">
              <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-900">
                  Pagos y gastos del sistema
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  {selectedMovement
                    ? selectedMovement.candidates.length > 0
                      ? "Coincidencias por monto y fecha"
                      : "Sin coincidencias para el movimiento seleccionado"
                    : "Selecciona un movimiento para ver sus coincidencias"}
                </p>
              </div>

              {selectedMovement ? (
                selectedMovement.candidates.length === 0 ? (
                  <div className="px-4 py-8 text-center">
                    <p className="text-sm font-medium text-slate-700">
                      {selectedMovement.transaction_type === "TRANSFER"
                        ? "Las transferencias internas no se concilian con pagos o gastos."
                        : "No hay pagos o gastos compatibles."}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Revisa el monto o registra la contrapartida en el sistema.
                    </p>
                  </div>
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {selectedMovement.candidates.map((candidate) => {
                      const matchKey = `${selectedMovement.id}:${candidate.id}`;
                      const isBusy = busyMatchKey === matchKey;
                      return (
                        <li key={candidate.id} className="px-4 py-3">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <span
                                  className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${
                                    candidate.kind === "payment"
                                      ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                                      : "bg-rose-50 text-rose-700 ring-rose-200"
                                  }`}
                                >
                                  {candidate.kind === "payment"
                                    ? "Pago"
                                    : "Gasto"}
                                </span>
                                <span className="text-xs text-slate-500">
                                  {candidate.date}
                                </span>
                              </div>
                              <p className="mt-1 truncate text-sm font-medium text-slate-900">
                                {candidate.description}
                              </p>
                              <p className="mt-0.5 truncate text-xs text-slate-500">
                                {candidate.party_name}
                                {candidate.invoice_number
                                  ? ` · ${candidate.invoice_number}`
                                  : ""}
                              </p>
                              {candidate.reference ? (
                                <p className="mt-0.5 truncate text-xs text-slate-500">
                                  Ref. {candidate.reference}
                                </p>
                              ) : null}
                            </div>
                            <div className="flex shrink-0 flex-col items-end gap-2">
                              <p className="text-sm font-semibold tabular-nums text-slate-900">
                                {formatCurrency(
                                  candidate.amount,
                                  account.currency,
                                )}
                              </p>
                              <Button
                                type="button"
                                onClick={() =>
                                  handleMatch(selectedMovement, candidate)
                                }
                                disabled={isBusy}
                                className="px-3 py-1.5 text-xs"
                              >
                                {isBusy ? "Conciliando..." : "Conciliar"}
                              </Button>
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )
              ) : (
                <div className="px-4 py-8 text-center">
                  <p className="text-sm font-medium text-slate-700">
                    Selecciona un movimiento del banco
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Verás aquí los pagos y gastos que coinciden en monto y
                    fecha.
                  </p>
                </div>
              )}
            </section>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
