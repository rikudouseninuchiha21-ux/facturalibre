"use client";

import { useEffect, useMemo, useRef, useState } from "react";

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
  createInvoice,
  issueInvoice,
  type Contact,
  type PosItemSearchResult,
  searchPosItems,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

interface CartLine {
  itemId: string;
  name: string;
  quantity: string;
  unitPrice: string;
  taxRate: string;
}

interface PosClientProps {
  contacts: Contact[];
}

function parseMoney(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function roundMoney(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function money(value: number): string {
  return formatCurrency(String(value), "COP");
}

export function PosClient({ contacts }: PosClientProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<PosItemSearchResult[]>([]);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [cashReceived, setCashReceived] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const supplierContacts = useMemo(
    () =>
      contacts.filter(
        (contact) =>
          contact.type === "customer" ||
          contact.type === "both" ||
          contact.type === "supplier",
      ),
    [contacts],
  );

  const lineAmounts = useMemo(
    () =>
      cart.map((line) => {
        const quantity = parseMoney(line.quantity);
        const unitPrice = parseMoney(line.unitPrice);
        const taxRate = parseMoney(line.taxRate);
        const subtotal = roundMoney(quantity * unitPrice);
        const tax = roundMoney((subtotal * taxRate) / 100);
        return { subtotal, tax, total: roundMoney(subtotal + tax) };
      }),
    [cart],
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

  const cash = parseMoney(cashReceived);
  const change = roundMoney(Math.max(0, cash - totals.total));

  useEffect(() => {
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    if (searchQuery.trim().length >= 1) {
      searchDebounceRef.current = setTimeout(async () => {
        try {
          const results = await searchPosItems(searchQuery.trim());
          setSearchResults(results.slice(0, 10));
        } catch {
          setSearchResults([]);
        }
      }, 250);
    } else {
      // Use setTimeout to avoid synchronous setState within effect body
      setTimeout(() => {
        setSearchResults([]);
      }, 0);
    }
    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
    };
  }, [searchQuery]);

  function handleSearchChange(value: string): void {
    setSearchQuery(value);
  }

  function addToCart(item: PosItemSearchResult): void {
    setError(null);
    const existingIndex = cart.findIndex((line) => line.itemId === item.id);
    if (existingIndex >= 0) {
      const existing = cart[existingIndex];
      const newQuantity = roundMoney(
        parseMoney(existing.quantity) + 1,
      ).toFixed(4);
      setCart(
        cart.map((line, index) =>
          index === existingIndex
            ? { ...existing, quantity: newQuantity }
            : line,
        ),
      );
    } else {
      setCart([
        ...cart,
        {
          itemId: item.id,
          name: item.name,
          quantity: "1",
          unitPrice: item.unit_price,
          taxRate: item.tax_rate,
        },
      ]);
    }
    setSearchQuery("");
    setSearchResults([]);
  }

  function updateLineQuantity(
    index: number,
    value: string,
  ): void {
    setCart(
      cart.map((line, i) =>
        i === index ? { ...line, quantity: value } : line,
      ),
    );
  }

  function removeLine(index: number): void {
    setCart(cart.filter((_, i) => i !== index));
  }

  async function handleCheckout(): Promise<void> {
    if (cart.length === 0) {
      setError("El carrito está vacío. Agrega al menos un producto.");
      return;
    }

    setError(null);
    setSuccess(null);
    setIsProcessing(true);

    try {
      const idempotencyKey = crypto.randomUUID();

      const payload = {
        contact_id: customerId || "",
        issue_date: new Date().toISOString().slice(0, 10),
        due_date: new Date().toISOString().slice(0, 10),
        currency: "COP" as const,
        lines: cart.map((line) => ({
          item_id: line.itemId,
          quantity: line.quantity,
          unit_price: line.unitPrice,
          discount_percent: "0",
          tax_rate: line.taxRate,
        })),
      };

      const invoice = await createInvoice(payload, idempotencyKey);
      await issueInvoice(invoice.id);

      setSuccess(
        `Factura ${invoice.number} emitida correctamente.`,
      );
      setCart([]);
      setCashReceived("");
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? `No se pudo completar la venta: ${cause.message}`
          : "No se pudo completar la venta. Revisa tu conexión e inténtalo de nuevo.",
      );
    } finally {
      setIsProcessing(false);
    }
  }

  const customerOptions = useMemo(
    () => [
      { id: "", name: "Consumidor Final" },
      ...supplierContacts.map((contact) => ({
        id: contact.id,
        name: `${contact.name}${contact.tax_id ? ` (${contact.tax_id})` : ""}`,
      })),
    ],
    [supplierContacts],
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left: Search + Cart */}
        <div className="lg:col-span-7 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Buscar producto</CardTitle>
              <CardDescription>
                Escribe el nombre del producto para agregarlo al carrito.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Buscar producto..."
                  value={searchQuery}
                  onChange={(event) => handleSearchChange(event.target.value)}
                  className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
                />
                {searchResults.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 rounded-lg border border-slate-200 bg-white shadow-lg max-h-48 overflow-y-auto">
                    {searchResults.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => addToCart(item)}
                        className="w-full text-left px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                      >
                        <div className="text-slate-900 font-medium">
                          {item.name}
                        </div>
                        <div className="text-xs text-slate-500">
                          {money(parseMoney(item.unit_price))} • Stock:
                          {item.stock_current}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div
                role="alert"
                className={error ? "rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" : "hidden"}
              >
                {error}
              </div>
              {success ? (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  {success}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Carrito</CardTitle>
              <CardDescription>
                {cart.length} línea{cart.length !== 1 ? "s" : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {cart.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
                  <p className="font-medium text-slate-700">
                    Carrito vacío
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    Busca un producto para agregar la primera línea.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <caption className="sr-only">Líneas del carrito</caption>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Producto</TableHead>
                        <TableHead className="text-right">Cantidad</TableHead>
                        <TableHead className="text-right">P. Unitario</TableHead>
                        <TableHead className="text-right">Subtotal</TableHead>
                        <TableHead className="text-right">Impuesto</TableHead>
                        <TableHead className="text-right">Total</TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {cart.map((line, index) => {
                        const amounts = lineAmounts[index] ?? {
                          subtotal: 0,
                          tax: 0,
                          total: 0,
                        };
                        return (
                          <TableRow key={line.itemId}>
                            <TableCell className="text-slate-900">
                              {line.name}
                            </TableCell>
                            <TableCell className="text-right tabular-nums text-slate-900">
                              <input
                                type="number"
                                min="0.0001"
                                step="0.0001"
                                inputMode="decimal"
                                value={line.quantity}
                                onChange={(event) =>
                                  updateLineQuantity(index, event.target.value)
                                }
                                className="w-24 rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm text-slate-950 tabular-nums outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900"
                              />
                            </TableCell>
                            <TableCell className="text-right tabular-nums text-slate-900">
                              {money(parseMoney(line.unitPrice))}
                            </TableCell>
                            <TableCell className="text-right tabular-nums text-slate-900">
                              {money(amounts.subtotal)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums text-slate-900">
                              {money(amounts.tax)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums font-medium text-slate-950">
                              {money(amounts.total)}
                            </TableCell>
                            <TableCell className="text-right">
                              <button
                                type="button"
                                onClick={() => removeLine(index)}
                                className="rounded-md px-2 py-1 text-xs font-semibold text-red-600 transition-colors hover:bg-red-50 hover:text-red-700"
                              >
                                Eliminar
                              </button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Checkout Panel */}
        <div className="lg:col-span-5 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Cobro</CardTitle>
              <CardDescription>
                Resumen de la venta y método de pago.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="pos-customer"
                    className="block text-sm font-medium text-slate-700"
                  >
                    Cliente
                  </label>
                  <select
                    id="pos-customer"
                    value={customerId}
                    onChange={(event) => setCustomerId(event.target.value)}
                    className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
                  >
                    {customerOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label
                    htmlFor="pos-cash"
                    className="block text-sm font-medium text-slate-700"
                  >
                    Efectivo recibido
                  </label>
                  <input
                    id="pos-cash"
                    type="number"
                    min="0"
                    step="0.01"
                    inputMode="decimal"
                    value={cashReceived}
                    onChange={(event) => setCashReceived(event.target.value)}
                    className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 tabular-nums shadow-sm outline-none transition focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
                  />
                </div>

                <div className="grid gap-4">
                  <div className="flex items-center justify-between gap-4 text-sm text-slate-600">
                    <span>Subtotal</span>
                    <span className="tabular-nums">{money(totals.subtotal)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-sm text-slate-600">
                    <span>IVA</span>
                    <span className="tabular-nums">{money(totals.tax)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4 border-t border-slate-200 pt-2 text-base font-semibold text-slate-950">
                    <span>Total</span>
                    <span className="tabular-nums">{money(totals.total)}</span>
                  </div>
                </div>

                <div className="grid gap-4">
                  <div className="flex items-center justify-between gap-4 text-sm text-slate-600">
                    <span>Efectivo recibido</span>
                    <span className="tabular-nums">{money(cash)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-sm text-slate-600">
                    <span>Cambio</span>
                    <span className="tabular-nums font-bold text-emerald-600">
                      {money(change)}
                    </span>
                  </div>
                </div>
              </div>

              <Button
                onClick={handleCheckout}
                disabled={isProcessing || cart.length === 0 || cash < totals.total}
                className="w-full bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed py-3"
              >
                {isProcessing
                  ? "Procesando..."
                  : `Cobrar y Emitir Factura (${money(totals.total)})`}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
