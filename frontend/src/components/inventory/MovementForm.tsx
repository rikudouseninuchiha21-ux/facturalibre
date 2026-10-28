"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  ApiError,
  getItems,
  getWarehouses,
  registerMovement,
  type Item,
  type StockMovementType,
  type Warehouse,
} from "@/lib/api";

const selectClassName =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

const inputClassName = selectClassName;

const movementLabels: Record<StockMovementType, string> = {
  IN: "Entrada (IN)",
  OUT: "Salida (OUT)",
};

export function MovementForm() {
  const router = useRouter();
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [warehouseId, setWarehouseId] = useState("");
  const [itemId, setItemId] = useState("");
  const [movementType, setMovementType] = useState<StockMovementType>("IN");
  const [quantity, setQuantity] = useState("1");
  const [isLoadingOptions, setIsLoadingOptions] = useState(true);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadOptions(): Promise<void> {
      try {
        const [warehouseData, itemData] = await Promise.all([
          getWarehouses(),
          getItems(),
        ]);

        if (cancelled) {
          return;
        }

        const activeWarehouses = warehouseData.filter(
          (warehouse) => warehouse.is_active,
        );
        setWarehouses(activeWarehouses);
        setItems(itemData);
        setWarehouseId(activeWarehouses[0]?.id ?? "");
        setItemId(itemData[0]?.id ?? "");
      } catch (cause) {
        if (cancelled) {
          return;
        }

        setOptionsError(
          cause instanceof Error
            ? cause.message
            : "No se pudieron cargar las bodegas y los ítems.",
        );
      } finally {
        if (!cancelled) {
          setIsLoadingOptions(false);
        }
      }
    }

    void loadOptions();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!warehouseId) {
      setError("Selecciona una bodega activa.");
      return;
    }

    if (!itemId) {
      setError("Selecciona un ítem.");
      return;
    }

    const normalizedQuantity = quantity.trim();
    const numericQuantity = Number(normalizedQuantity);

    if (
      !/^\d+(\.\d{1,4})?$/.test(normalizedQuantity) ||
      !Number.isFinite(numericQuantity) ||
      numericQuantity <= 0
    ) {
      setError("La cantidad debe ser un número mayor que cero, con hasta 4 decimales.");
      return;
    }

    setIsSubmitting(true);

    try {
      await registerMovement({
        item_id: itemId,
        warehouse_id: warehouseId,
        movement_type: movementType,
        quantity: normalizedQuantity,
      });
      setQuantity("1");
      setSuccess(
        `${movementLabels[movementType]} registrada correctamente. El saldo se actualizó.`,
      );
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo registrar el movimiento: ${cause.message}`
          : "No se pudo registrar el movimiento. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const hasOptions = warehouses.length > 0 && items.length > 0;
  const isDisabled = isLoadingOptions || isSubmitting || !hasOptions;

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {optionsError ? (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {optionsError}
        </p>
      ) : null}

      {!isLoadingOptions && !optionsError && !hasOptions ? (
        <div className="rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-sm text-violet-800">
          {warehouses.length === 0 ? (
            <p>
              No hay bodegas activas. Crea una en{" "}
              <Link
                href="/warehouses"
                className="font-semibold text-violet-900 underline decoration-violet-400 underline-offset-2"
              >
                Bodegas
              </Link>
              .
            </p>
          ) : null}
          {items.length === 0 ? (
            <p>No hay ítems disponibles para mover stock.</p>
          ) : null}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="movement-warehouse"
            className="block text-sm font-medium text-slate-700"
          >
            Bodega{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <select
            id="movement-warehouse"
            name="warehouse_id"
            required
            value={warehouseId}
            onChange={(event) => setWarehouseId(event.target.value)}
            disabled={isDisabled}
            className={selectClassName}
          >
            {isLoadingOptions ? (
              <option value="">Cargando bodegas...</option>
            ) : null}
            {!isLoadingOptions && warehouses.length === 0 ? (
              <option value="">Sin bodegas activas</option>
            ) : null}
            {warehouses.map((warehouse) => (
              <option key={warehouse.id} value={warehouse.id}>
                {warehouse.name} ({warehouse.code})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="movement-item"
            className="block text-sm font-medium text-slate-700"
          >
            Ítem{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <select
            id="movement-item"
            name="item_id"
            required
            value={itemId}
            onChange={(event) => setItemId(event.target.value)}
            disabled={isDisabled}
            className={selectClassName}
          >
            {isLoadingOptions ? (
              <option value="">Cargando ítems...</option>
            ) : null}
            {!isLoadingOptions && items.length === 0 ? (
              <option value="">Sin ítems disponibles</option>
            ) : null}
            {items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="movement-type"
            className="block text-sm font-medium text-slate-700"
          >
            Tipo{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <select
            id="movement-type"
            name="movement_type"
            required
            value={movementType}
            onChange={(event) =>
              setMovementType(event.target.value as StockMovementType)
            }
            disabled={isDisabled}
            className={selectClassName}
          >
            <option value="IN">{movementLabels.IN}</option>
            <option value="OUT">{movementLabels.OUT}</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="movement-quantity"
            className="block text-sm font-medium text-slate-700"
          >
            Cantidad{" "}
            <span className="text-red-600" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="movement-quantity"
            name="quantity"
            type="number"
            required
            min="0.0001"
            step="0.0001"
            inputMode="decimal"
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
            disabled={isDisabled}
            className={inputClassName}
          />
        </div>
      </div>

      {error ? (
        <p
          id="movement-form-error"
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
        <Button type="submit" disabled={isDisabled} className="w-full sm:w-auto">
          {isSubmitting ? "Registrando..." : "Registrar Movimiento"}
        </Button>
      </div>
    </form>
  );
}
