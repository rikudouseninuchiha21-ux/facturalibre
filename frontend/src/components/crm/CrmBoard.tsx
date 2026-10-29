"use client";

import {
  DragDropContext,
  Draggable,
  Droppable,
  type DropResult,
} from "@hello-pangea/dnd";
import {
  CalendarDays,
  FileText,
  Mail,
  Phone,
  Plus,
  UserRound,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import {
  addCrmActivity,
  ApiError,
  convertCrmOpportunityToQuote,
  createCrmOpportunity,
  getCrmOpportunity,
  moveCrmOpportunity,
  type Contact,
  type CrmActivityType,
  type CrmOpportunity,
  type CrmOpportunityDetail,
  type CrmStage,
} from "@/lib/api";
import { formatCurrency, formatDate, formatRelativeTime } from "@/lib/format";

interface CrmBoardProps {
  initialStages: CrmStage[];
  initialOpportunities: CrmOpportunity[];
  contacts: Contact[];
}

const activityLabels: Record<CrmActivityType, string> = {
  CALL: "Llamada",
  EMAIL: "Correo",
  MEETING: "Reunión",
  NOTE: "Nota",
};

const activityIcons = {
  CALL: Phone,
  EMAIL: Mail,
  MEETING: Users,
  NOTE: FileText,
} as const;

const inputClassName =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-slate-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20";

function stageSummary(items: CrmOpportunity[]): string {
  const total = items.reduce((sum, item) => sum + Number(item.amount), 0);
  return formatCurrency(String(total), "COP");
}

export function CrmBoard({
  initialStages,
  initialOpportunities,
  contacts,
}: CrmBoardProps) {
  const [stages] = useState(initialStages);
  const [opportunities, setOpportunities] = useState(initialOpportunities);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CrmOpportunityDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [newTitle, setNewTitle] = useState("");
  const [newContactId, setNewContactId] = useState(contacts[0]?.id ?? "");
  const [newStageId, setNewStageId] = useState(stages[0]?.id ?? "");
  const [newAmount, setNewAmount] = useState("");
  const [newCloseDate, setNewCloseDate] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const [activityType, setActivityType] = useState<CrmActivityType>("CALL");
  const [activityDescription, setActivityDescription] = useState("");
  const [isAddingActivity, setIsAddingActivity] = useState(false);

  function replaceOpportunity(updated: CrmOpportunity): void {
    setOpportunities((current) =>
      current.map((item) => (item.id === updated.id ? updated : item)),
    );
    setDetail((current) =>
      current && current.id === updated.id ? { ...current, ...updated } : current,
    );
  }

  function handleDragEnd(result: DropResult): void {
    const { destination, source, draggableId } = result;
    if (!destination || destination.droppableId === source.droppableId) {
      return;
    }

    const targetStage = stages.find(
      (stage) => stage.id === destination.droppableId,
    );
    if (!targetStage) {
      return;
    }

    setError(null);
    const previous = opportunities;
    setOpportunities((current) =>
      current.map((item) =>
        item.id === draggableId
          ? {
              ...item,
              stage_id: targetStage.id,
              stage_name: targetStage.name,
              is_won: targetStage.is_won,
              is_lost: targetStage.is_lost,
            }
          : item,
      ),
    );

    void moveCrmOpportunity(draggableId, targetStage.id)
      .then((updated) => replaceOpportunity(updated))
      .catch((cause) => {
        setOpportunities(previous);
        setError(
          cause instanceof ApiError
            ? cause.message
            : "No se pudo mover la oportunidad.",
        );
      });
  }

  async function openDetail(opportunityId: string): Promise<void> {
    setSelectedId(opportunityId);
    setDetail(null);
    setError(null);
    setIsLoadingDetail(true);
    try {
      setDetail(await getCrmOpportunity(opportunityId));
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo cargar la oportunidad.",
      );
    } finally {
      setIsLoadingDetail(false);
    }
  }

  function closeDetail(): void {
    setSelectedId(null);
    setDetail(null);
    setActivityDescription("");
  }

  async function handleCreate(): Promise<void> {
    setError(null);
    if (!newTitle.trim() || !newContactId || !newStageId) {
      setError("Completa el título, el contacto y la etapa.");
      return;
    }
    if (newAmount && Number.isNaN(Number(newAmount))) {
      setError("El monto debe ser numérico.");
      return;
    }

    setIsCreating(true);
    try {
      const created = await createCrmOpportunity({
        contact_id: newContactId,
        stage_id: newStageId,
        title: newTitle.trim(),
        amount: newAmount.trim() || "0",
        ...(newCloseDate ? { expected_close_date: newCloseDate } : {}),
        ...(newNotes.trim() ? { notes: newNotes.trim() } : {}),
      });
      setOpportunities((current) => [created, ...current]);
      setIsCreateOpen(false);
      setNewTitle("");
      setNewAmount("");
      setNewCloseDate("");
      setNewNotes("");
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo crear la oportunidad.",
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleAddActivity(): Promise<void> {
    if (!detail || !activityDescription.trim()) {
      return;
    }
    setError(null);
    setIsAddingActivity(true);
    try {
      const activity = await addCrmActivity(detail.id, {
        type: activityType,
        description: activityDescription.trim(),
      });
      setDetail((current) =>
        current
          ? { ...current, activities: [activity, ...current.activities] }
          : current,
      );
      setActivityDescription("");
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo registrar la actividad.",
      );
    } finally {
      setIsAddingActivity(false);
    }
  }

  async function handleConvert(): Promise<void> {
    if (!detail) {
      return;
    }
    setError(null);
    setIsConverting(true);
    try {
      const converted = await convertCrmOpportunityToQuote(detail.id);
      replaceOpportunity(converted);
      setDetail((current) =>
        current ? { ...current, quote_id: converted.quote_id } : current,
      );
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "No se pudo convertir la oportunidad.",
      );
    } finally {
      setIsConverting(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <span className="font-semibold text-slate-900">
            {opportunities.length}
          </span>
          oportunidad{opportunities.length === 1 ? "" : "es"} en el embudo
        </div>
        <Button
          onClick={() => setIsCreateOpen(true)}
          disabled={contacts.length === 0 || stages.length === 0}
        >
          <Plus className="mr-2 size-4" aria-hidden="true" />
          Nueva Oportunidad
        </Button>
      </div>

      {contacts.length === 0 ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Necesitas al menos un contacto para crear oportunidades. Ve a{" "}
          <Link href="/contacts" className="font-semibold underline">
            Contactos
          </Link>
          .
        </div>
      ) : null}

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      <DragDropContext onDragEnd={handleDragEnd}>
        <div className="flex gap-4 overflow-x-auto pb-4">
          {stages.map((stage) => {
            const items = opportunities.filter(
              (opportunity) => opportunity.stage_id === stage.id,
            );
            return (
              <section
                key={stage.id}
                className="flex w-72 shrink-0 flex-col rounded-2xl border border-slate-200 bg-slate-50/70"
              >
                <header className="border-b border-slate-200 px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <span
                        className="size-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: stage.color }}
                      />
                      <h2 className="truncate text-sm font-bold text-slate-900">
                        {stage.name}
                      </h2>
                    </div>
                    <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-600 ring-1 ring-slate-200">
                      {items.length}
                    </span>
                  </div>
                  <p className="mt-1 text-xs font-medium text-slate-500">
                    {stageSummary(items)}
                  </p>
                </header>

                <Droppable droppableId={stage.id}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      className={`flex min-h-28 flex-1 flex-col gap-3 overflow-y-auto p-3 transition-colors ${
                        snapshot.isDraggingOver ? "bg-violet-50/80" : ""
                      }`}
                    >
                      {items.map((opportunity, index) => (
                        <Draggable
                          key={opportunity.id}
                          draggableId={opportunity.id}
                          index={index}
                        >
                          {(dragProvided, dragSnapshot) => (
                            <article
                              ref={dragProvided.innerRef}
                              {...dragProvided.draggableProps}
                              {...dragProvided.dragHandleProps}
                              onClick={() => void openDetail(opportunity.id)}
                              className={`cursor-pointer rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-shadow hover:shadow-md ${
                                dragSnapshot.isDragging ? "shadow-xl ring-2 ring-violet-300" : ""
                              }`}
                            >
                              <div className="flex items-start justify-between gap-2">
                                <h3 className="text-sm font-semibold leading-5 text-slate-950">
                                  {opportunity.title}
                                </h3>
                                {opportunity.is_won ? (
                                  <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                                    GANADA
                                  </span>
                                ) : opportunity.is_lost ? (
                                  <span className="shrink-0 rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-bold text-red-700">
                                    PERDIDA
                                  </span>
                                ) : null}
                              </div>
                              <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-600">
                                <UserRound className="size-3.5" aria-hidden="true" />
                                <span className="truncate">{opportunity.contact_name}</span>
                              </p>
                              <p className="mt-3 text-base font-bold tabular-nums text-violet-700">
                                {formatCurrency(opportunity.amount, "COP")}
                              </p>
                              <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-slate-500">
                                <span className="truncate">
                                  {opportunity.owner_name}
                                </span>
                                {opportunity.expected_close_date ? (
                                  <span className="flex shrink-0 items-center gap-1">
                                    <CalendarDays className="size-3" aria-hidden="true" />
                                    {formatDate(opportunity.expected_close_date)}
                                  </span>
                                ) : null}
                              </div>
                            </article>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                      {items.length === 0 ? (
                        <p className="rounded-lg border border-dashed border-slate-300 px-3 py-6 text-center text-xs text-slate-400">
                          Arrastra una oportunidad aquí
                        </p>
                      ) : null}
                    </div>
                  )}
                </Droppable>
              </section>
            );
          })}
        </div>
      </DragDropContext>

      {isCreateOpen ? (
        <Modal
          title="Nueva oportunidad"
          description="Crea una tarjeta para el embudo comercial."
          onClose={() => setIsCreateOpen(false)}
          maxWidthClassName="max-w-2xl"
        >
          <div className="space-y-4">
            <label className="block space-y-1">
              <span className="text-sm font-medium text-slate-700">Título *</span>
              <input
                className={inputClassName}
                value={newTitle}
                onChange={(event) => setNewTitle(event.target.value)}
                placeholder="Renovación de licencias"
                autoFocus
              />
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block space-y-1">
                <span className="text-sm font-medium text-slate-700">Contacto *</span>
                <select
                  className={inputClassName}
                  value={newContactId}
                  onChange={(event) => setNewContactId(event.target.value)}
                >
                  {contacts.map((contact) => (
                    <option key={contact.id} value={contact.id}>
                      {contact.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block space-y-1">
                <span className="text-sm font-medium text-slate-700">Etapa *</span>
                <select
                  className={inputClassName}
                  value={newStageId}
                  onChange={(event) => setNewStageId(event.target.value)}
                >
                  {stages.map((stage) => (
                    <option key={stage.id} value={stage.id}>
                      {stage.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block space-y-1">
                <span className="text-sm font-medium text-slate-700">Monto (COP)</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  className={inputClassName}
                  value={newAmount}
                  onChange={(event) => setNewAmount(event.target.value)}
                  placeholder="1500000.00"
                />
              </label>
              <label className="block space-y-1">
                <span className="text-sm font-medium text-slate-700">
                  Cierre esperado
                </span>
                <input
                  type="date"
                  className={inputClassName}
                  value={newCloseDate}
                  onChange={(event) => setNewCloseDate(event.target.value)}
                />
              </label>
            </div>
            <label className="block space-y-1">
              <span className="text-sm font-medium text-slate-700">Notas</span>
              <textarea
                className={`${inputClassName} min-h-24`}
                value={newNotes}
                onChange={(event) => setNewNotes(event.target.value)}
                placeholder="Contexto de la oportunidad..."
              />
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                onClick={() => setIsCreateOpen(false)}
                disabled={isCreating}
              >
                Cancelar
              </Button>
              <Button onClick={() => void handleCreate()} disabled={isCreating}>
                {isCreating ? "Creando..." : "Crear oportunidad"}
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}

      {selectedId ? (
        <Modal
          title={detail?.title ?? "Oportunidad"}
          description={
            detail
              ? `${detail.contact_name} · ${detail.stage_name}`
              : "Cargando oportunidad..."
          }
          onClose={closeDetail}
          maxWidthClassName="max-w-3xl"
        >
          {isLoadingDetail ? (
            <p className="text-sm text-slate-500">Cargando...</p>
          ) : detail ? (
            <div className="space-y-6">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl bg-violet-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-violet-600">
                    Monto
                  </p>
                  <p className="mt-1 text-lg font-bold tabular-nums text-violet-900">
                    {formatCurrency(detail.amount, "COP")}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Dueño
                  </p>
                  <p className="mt-1 truncate text-sm font-semibold text-slate-900">
                    {detail.owner_name}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Cierre esperado
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-900">
                    {detail.expected_close_date
                      ? formatDate(detail.expected_close_date)
                      : "Sin fecha"}
                  </p>
                </div>
              </div>

              {detail.notes ? (
                <p className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                  {detail.notes}
                </p>
              ) : null}

              <div className="flex flex-wrap items-center gap-3">
                {detail.quote_id ? (
                  <Link
                    href={`/quotes/${detail.quote_id}`}
                    className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-500"
                  >
                    <FileText className="size-4" aria-hidden="true" />
                    Ver cotización generada
                  </Link>
                ) : (
                  <Button onClick={() => void handleConvert()} disabled={isConverting}>
                    {isConverting ? "Convirtiendo..." : "Convertir a Cotización"}
                  </Button>
                )}
                {detail.is_won ? (
                  <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">
                    Ganada
                  </span>
                ) : detail.is_lost ? (
                  <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-700">
                    Perdida
                  </span>
                ) : null}
              </div>

              <div className="space-y-3">
                <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                  Historial de actividades
                </h3>
                {detail.activities.length === 0 ? (
                  <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-500">
                    Todavía no hay actividades registradas.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {detail.activities.map((activity) => {
                      const Icon = activityIcons[activity.type] ?? FileText;
                      return (
                        <li
                          key={activity.id}
                          className="flex gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3"
                        >
                          <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-violet-100 text-violet-700">
                            <Icon className="size-4" aria-hidden="true" />
                          </span>
                          <div className="min-w-0">
                            <p className="text-xs font-semibold uppercase tracking-wide text-violet-600">
                              {activityLabels[activity.type] ?? activity.type}
                            </p>
                            <p className="mt-1 text-sm text-slate-800">
                              {activity.description}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              {activity.created_by_name} ·{" "}
                              {formatRelativeTime(activity.activity_date)}
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}

                <div className="rounded-xl border border-violet-100 bg-violet-50/40 p-4">
                  <p className="text-sm font-semibold text-slate-800">
                    Registrar actividad
                  </p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-[160px_1fr]">
                    <select
                      className={inputClassName}
                      value={activityType}
                      onChange={(event) =>
                        setActivityType(event.target.value as CrmActivityType)
                      }
                    >
                      <option value="CALL">Llamada</option>
                      <option value="EMAIL">Correo</option>
                      <option value="MEETING">Reunión</option>
                      <option value="NOTE">Nota</option>
                    </select>
                    <input
                      className={inputClassName}
                      value={activityDescription}
                      onChange={(event) => setActivityDescription(event.target.value)}
                      placeholder="Describe la interacción..."
                    />
                  </div>
                  <div className="mt-3 flex justify-end">
                    <Button
                      onClick={() => void handleAddActivity()}
                      disabled={isAddingActivity || !activityDescription.trim()}
                    >
                      {isAddingActivity ? "Registrando..." : "Agregar actividad"}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-red-600">{error ?? "No se pudo cargar."}</p>
          )}
        </Modal>
      ) : null}
    </div>
  );
}
