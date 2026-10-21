# Decisiones de diseño — FacturaLibre

> **Documento:** resolución de las 22 preguntas abiertas de `specs/ESPECIFICACION-FUNCIONAL.md`
> **Enfoque:** decisiones propias de FacturaLibre, no una copia del comportamiento de Alegra.
> **Fecha:** 2026-10-21
> **Ámbito:** Colombia, MVP; arquitectura preparada para crecer.

---

## 1. Introducción

`ESPECIFICACION-FUNCIONAL.md` describe **qué hace** la API pública de Alegra y deja 22 preguntas sin responder. Este documento responde **qué haremos nosotros** y por qué.

Alegra nos sirvió como mapa del problema: qué recursos existen, qué campos se usan y dónde la documentación se queda corta. **No es nuestro contrato.** FacturaLibre define su propio modelo, sus propias reglas y su propia API. Cuando la práctica de Alegra no nos convence, nos apartamos de ella y lo justificamos.

Tres principios guían todas las decisiones:

1. **El documento fiscal es inmutable.** Se corrige con otro documento (nota crédito, anulación), nunca editando el original.
2. **El dinero no se calcula con `float`.** Se usa aritmética decimal y reglas de redondeo explícitas.
3. **Toda decisión técnica debe poder auditarse.** Si no se puede reconstruir cómo se llegó a un saldo, el diseño está mal.

Cada decisión cita una autoridad: **DIAN**, **NIIF**, **práctica contable**, **RFC/ISO** o **criterio de ingeniería**. Cuando la norma exacta no se puede afirmar con certeza, se marca **REQUIERE VALIDACIÓN** con contador, abogado o experto DIAN. No inventamos normativa.

---

## 2. Tabla resumen

| # | Pregunta | Decisión | Estado | Prioridad |
|---|---|---|---|---|
| 1 | ¿Qué significa `closed`? | Separar ciclo de vida (`draft/issued/void`) de estado de pago (`unpaid/partially_paid/paid/overpaid`). `closed` desaparece como estado propio. | **DECIDIDO** | MVP |
| 2 | ¿Existe `paid`? | Sí, pero solo como **estado de pago derivado**, nunca como estado de ciclo de vida editable. | **DECIDIDO** | MVP |
| 3 | ¿Cómo se pasa de `open` a `closed`? | Se recalcula automáticamente al aplicar pagos, notas crédito o anulaciones. Sin cierre manual. | **DECIDIDO** | MVP |
| 4 | ¿Cómo afectan las retenciones? | Se modelan aparte; **no modifican** el total ni el IVA de la factura, reducen el valor a cobrar. | **DECIDIDO** | Fase2 |
| 5 | ¿Cómo funcionan los descuentos? | Por línea, antes de impuestos; el descuento global se prorratea por base. Nunca después de impuesto. | **DECIDIDO** | MVP |
| 6 | ¿Cómo se redondea? | `Decimal`, precisión interna alta, redondeo `ROUND_HALF_UP` por línea a 2 decimales monetarios. | **DECIDIDO** | MVP |
| 7 | ¿Cómo se combinan varios impuestos? | Se suman sobre la misma base (aditivos). Impuestos compuestos quedan fuera. | **DECIDIDO** | MVP |
| 8 | ¿En qué moneda está el total? | Moneda de la transacción + moneda funcional (COP), con tasa y fecha. MVP solo COP. | **POSPUESTO** | Fase2 |
| 9 | ¿`account` o `bankAccount`? | Un solo nombre canónico: `bank_account_id`. Los alias se traducen en el adaptador. | **DECIDIDO** | MVP |
| 10 | ¿Hay un monto total del pago? | Sí, `amount` obligatorio; debe cuadrar con las aplicaciones a facturas. | **DECIDIDO** | MVP |
| 11 | ¿Sobrepagos y anticipos? | MVP rechaza sobrepagos. Fase2 crea anticipo del cliente y aplica FIFO. | **POSPUESTO** | Fase2 |
| 12 | ¿Qué campos de impuesto son obligatorios? | `name`, `rate`, `type`, `dian_code` (si es electrónico) y `status`. No heredamos la omisión de Alegra. | **DECIDIDO** | MVP |
| 13 | ¿Catálogo de `type` de impuesto? | Enum cerrado: `VAT`, `INC`, `ICA`, `WITHHOLDING`, `OTHER`; el código DIAN va aparte. | **DECIDIDO** | MVP |
| 14 | ¿Campos obligatorios por país? | MVP solo Colombia. Otros países quedan fuera de este diseño. | **DESCARTADO** | Descartado |
| 15 | ¿Idempotencia? | `Idempotency-Key` UUID v4, alcance por tenant y endpoint, TTL 24 h. | **DECIDIDO** | MVP |
| 16 | ¿Concurrencia? | Bloqueo optimista con `version` y `If-Match`; 412 si el recurso cambió. | **DECIDIDO** | MVP |
| 17 | ¿Webhooks? | Outbox transaccional, HMAC-SHA256, reintentos y entrega al menos una vez. | **POSPUESTO** | Fase2 |
| 18 | ¿Notas crédito? | Documento separado que referencia la factura y reduce el saldo; nunca edita la factura. | **DECIDIDO** | MVP |
| 19 | ¿Anulación y contabilidad? | Documento emitido no se borra: se anula y se reversa contablemente. Solo el borrador se elimina. | **DECIDIDO** | MVP |
| 20 | ¿Zona horaria? | Fechas de negocio sin hora en `America/Bogota`; marcas de tiempo en UTC/RFC 3339. | **DECIDIDO** | MVP |
| 21 | ¿Versionado de la API? | Ruta `/v1`, cambios aditivos, ruptura en `/v2`, aviso de retiro de 6 meses. | **DECIDIDO** | MVP |
| 22 | ¿Límite por usuario? | Cuota propia por tenant/token con token bucket; no copiamos los 150/min de Alegra. | **DECIDIDO** | MVP |

**Conteo:** 18 DECIDIDAS · 3 POSPUESTAS · 1 DESCARTADA.

---

## 3. Detalle por pregunta

### Pregunta 1 — ¿Qué significa `closed`?

**Estado:** DECIDIDO · **Prioridad:** MVP

`closed` mezcla dos dimensiones distintas: si el documento está emitido y si está pagado. Las separamos:

- `lifecycle_status`: `draft` → `issued` → `void`.
- `payment_status`: `unpaid`, `partially_paid`, `paid`, `overpaid` (derivado).

Para compatibilidad con integraciones, `closed` se traduce a `paid`. **No** existirá un estado `closed` persistido.

**Por qué:** un documento puede estar emitido y no pagado, o pagado y luego anulado. Un solo campo no puede representar ambas cosas sin ambigüedad.

**Autoridad:** NIIF 15 (ingreso) y NIIF 9 (cuentas por cobrar); práctica contable; criterio de ingeniería.

---

### Pregunta 2 — ¿Existe `paid`?

**Estado:** DECIDIDO · **Prioridad:** MVP

Sí, pero como **estado de pago derivado**, no como estado del documento. Se calcula:

```text
balance = total - pagos_aplicados - notas_credito_aplicadas
paid    = balance == 0
```

El cliente no puede escribir `paid`; solo puede registrar pagos o notas crédito que lo produzcan.

**Por qué:** evita que un usuario marque una factura como pagada sin respaldo contable. El estado debe ser consecuencia de hechos, no una etiqueta.

**Autoridad:** NIIF 9; práctica contable; criterio de ingeniería.

---

### Pregunta 3 — ¿Cómo se pasa de `open` a `closed`?

**Estado:** DECIDIDO · **Prioridad:** MVP

No hay transición manual. El `payment_status` se recalcula en la misma transacción que:

1. aplica un pago,
2. anula un pago,
3. aplica una nota crédito,
4. anula la factura.

Se emite el evento `invoice.payment_status_changed` solo si el valor cambia. Si dos pagos llegan a la vez, el bloqueo de la factura serializa el cálculo.

**Por qué:** el saldo debe ser siempre la suma de sus aplicaciones; un cierre manual lo desincroniza.

**Autoridad:** práctica contable; criterio de ingeniería; NIIF 9.

---

### Pregunta 4 — ¿Cómo afectan las retenciones?

**Estado:** DECIDIDO · **Prioridad:** Fase2

Se modelan como entidades separadas (`withholdings`) asociadas a la factura o al pago, con:

- `type`: ReteFuente, ReteIVA, ReteICA u otra.
- `base`, `rate`, `amount`.
- `rule_id` y vigencia de la regla.

No modifican el `total` ni el `tax` de la factura. Reducen el **valor a cobrar** y, en los libros del vendedor, se registran como activo por impuesto (saldo a favor). Se guardan siempre el bruto, la retención y el neto.

**Por qué:** una retención no es un descuento comercial ni un impuesto de la factura; es un pago anticipado de impuestos que hace el comprador.

**Autoridad:** práctica contable colombiana (agente retenedor); normativa DIAN de retenciones; acuerdos municipales para ReteICA.

**REQUIERE VALIDACIÓN:** tarifas, bases mínimas, códigos y excepciones exactas antes de implementar el cálculo.

---

### Pregunta 5 — ¿Cómo funcionan los descuentos?

**Estado:** DECIDIDO · **Prioridad:** MVP

- Descuento por línea: porcentaje o monto fijo.
- Se aplica sobre la base de la línea **antes** de impuestos.
- Descuento global: se reparte entre las líneas de forma proporcional a su base.
- Nunca se aplica después del impuesto.
- No se permiten precios negativos; un descuento mayor a la base es error de validación.

Se almacenan `gross_base`, `discount_amount`, `tax_base` y `total_line`.

**Por qué:** la base gravable debe quedar explícita y reproducible; aplicar descuentos después del IVA distorsiona el impuesto.

**Autoridad:** NIIF 15 (contraprestación variable); práctica contable; DIAN (base gravable).

**REQUIERE VALIDACIÓN:** cómo reportar el descuento en el documento electrónico y su efecto exacto en la base.

---

### Pregunta 6 — ¿Cómo se redondea?

**Estado:** DECIDIDO · **Prioridad:** MVP

- Nada de `float` ni `double` para dinero.
- `Decimal(19,6)` para precios unitarios, tasas y cálculos intermedios.
- `Decimal(19,2)` para montos monetarios en COP.
- Redondeo `ROUND_HALF_UP` por línea, y luego suma de líneas redondeadas.
- En otras monedas se usan los decimales que indique ISO 4217 (0, 2 o 3).
- Los montos se serializan como **string** en JSON para no perder precisión.

**Por qué:** `0.1 + 0.2` en binario no es `0.3`; en facturación ese error se acumula y rompe cuadres.

**Autoridad:** ISO 4217; IEEE 754 (qué evitar); práctica contable; criterio de ingeniería.

**REQUIERE VALIDACIÓN:** la DIAN puede exigir una regla de redondeo distinta por tipo de documento o por línea/total. Confirmar antes de emitir electrónicamente.

---

### Pregunta 7 — ¿Cómo se combinan varios impuestos?

**Estado:** DECIDIDO · **Prioridad:** MVP

Los impuestos son **aditivos e independientes**: cada uno se calcula sobre la misma base de la línea y se suma (`tax_total = Σ base × rate_i`). No hay impuesto sobre impuesto. Se distingue `exempt` (0 %), `excluded` (no causa) y `not_subject` (no sujeto).

Los impuestos compuestos quedan **DESCARTADOS**: no los implementamos hasta que un experto confirme que un caso colombiano real los requiere.

**Por qué:** sumar es predecible y auditable; la cascada es una fuente clásica de diferencias de un centavo.

**Autoridad:** estructura de IVA/INC de la DIAN; práctica contable; criterio de ingeniería.

---

### Pregunta 8 — ¿En qué moneda está el total?

**Estado:** POSPUESTO · **Prioridad:** Fase2

El MVP opera **solo en COP**. El modelo se prepara desde ahora con:

- `Money { amount, currency }`.
- `exchange_rate` = unidades de COP por unidad de moneda extranjera.
- `rate_date`.
- `amount_functional` y `amount_transaction`.

No se convierte «de ida y vuelta»: se guarda el importe original y el funcional por separado. La multimoneda real se implementa en Fase2.

**Por qué:** un MVP multimoneda sin políticas contables claras produce diferencias por tipo de cambio imposibles de auditar.

**Autoridad:** NIC 21 (efectos de variaciones en tasas de cambio); ISO 4217.

**REQUIERE VALIDACIÓN:** política de revaluación, fecha de tasa y tratamiento de diferencias cambiarias con el contador.

---

### Pregunta 9 — ¿`account` o `bankAccount`?

**Estado:** DECIDIDO · **Prioridad:** MVP

Un solo nombre canónico en nuestro modelo: **`bank_account_id`**. Los alias (`account`, `bankAccount`, `cuenta`) se traducen en la capa de adaptación de entrada/salida.

No habrá dos campos que representen lo mismo ni lógica condicional por nombre.

**Por qué:** dos nombres para el mismo concepto generan bugs silenciosos y deuda técnica. Un solo nombre, una sola verdad.

**Autoridad:** criterio de ingeniería (fuente única de verdad); diseño de APIs.

---

### Pregunta 10 — ¿Hay un monto total del pago?

**Estado:** DECIDIDO · **Prioridad:** MVP

Sí: `payment.amount` es obligatorio, mayor que cero y debe cumplir:

```text
amount = Σ allocations.amount + unapplied_amount
```

Las aplicaciones a facturas se guardan en una tabla aparte (`payment_allocations`), no como un arreglo embebido. Un pago puede aplicar a varias facturas y una factura puede recibir varios pagos.

**Por qué:** el pago es un hecho contable propio; embeberlo dentro de la factura impide reversarlo y auditar su origen.

**Autoridad:** práctica contable; NIIF 9; criterio de ingeniería.

---

### Pregunta 11 — ¿Sobrepagos y anticipos?

**Estado:** POSPUESTO · **Prioridad:** Fase2

En el MVP, si `amount` supera el saldo de las facturas, se rechaza con `422` y un mensaje claro. No se crea saldo a favor automáticamente.

En Fase2:

- el excedente se registra como `customer_advance` (pasivo),
- se aplica a facturas futuras de forma manual o FIFO,
- se devuelve con un pago de salida o una nota crédito,
- nunca se permite un `balance` negativo en la factura.

**Por qué:** un anticipo es dinero de terceros; mezclarlo con el saldo de una factura oculta el pasivo.

**Autoridad:** NIIF 9; práctica contable; criterio de ingeniería.

---

### Pregunta 12 — ¿Qué campos de impuesto son obligatorios?

**Estado:** DECIDIDO · **Prioridad:** MVP

Nuestro contrato exige cinco campos: `name` (1–100 caracteres), `rate` (`Decimal` entre 0 y 100, máximo 4 decimales), `type` (enum cerrado), `dian_code` (obligatorio si el impuesto se usa en documento electrónico) y `status` (`active` por defecto; `inactive` no se puede usar en documentos nuevos).

No heredamos la ausencia de `required` de Alegra: nuestro esquema sí valida.

**Por qué:** un impuesto sin código o sin tarifa no se puede reportar ni auditar.

**Autoridad:** catálogos DIAN; práctica contable; criterio de ingeniería.

**REQUIERE VALIDACIÓN:** la tabla exacta de códigos y vigencias.

---

### Pregunta 13 — ¿Catálogo de `type` de impuesto?

**Estado:** DECIDIDO · **Prioridad:** MVP

Enum cerrado y propio: `VAT` (IVA), `INC` (impuesto nacional al consumo), `ICA` (industria y comercio, municipal), `WITHHOLDING` (retención) y `OTHER` (otros, con código DIAN obligatorio).

El `dian_code` se guarda como campo separado y versionado. **No** usamos un string libre como Alegra.

**Por qué:** un enum permite validar, reportar y filtrar; un string libre convierte cualquier error tipográfico en un impuesto nuevo.

**Autoridad:** catálogos DIAN; práctica contable; criterio de ingeniería.

**REQUIERE VALIDACIÓN:** códigos, nombres y vigencias del catálogo oficial.

---

### Pregunta 14 — ¿Campos obligatorios por país?

**Estado:** DESCARTADO · **Prioridad:** Descartado

FacturaLibre **no soporta otros países** en este diseño. El MVP es Colombia y punto.

No implementamos variantes de México, Chile, Argentina, Perú, Panamá, Costa Rica, España ni República Dominicana. El modelo deja un punto de extensión (`tax_profile`) para no cerrar la puerta, pero no se codifica nada específico.

**Por qué:** cada país es un producto fiscal distinto; intentar cubrirlos todos con un `oneOf` gigante es la forma más rápida de no cumplir bien en ninguno.

**Autoridad:** alcance de producto; criterio de ingeniería.

---

### Pregunta 15 — ¿Idempotencia?

**Estado:** DECIDIDO · **Prioridad:** MVP

Cabecera `Idempotency-Key` con UUID v4, obligatoria en `POST` y `PUT`.

- Alcance: `tenant_id + método + ruta + key`.
- TTL: 24 horas.
- Se guarda hash del cuerpo y la respuesta completa.
- Repetición con el mismo cuerpo: devuelve la misma respuesta (200/201).
- Repetición con cuerpo distinto: `409 Conflict`.

**Por qué:** un reintento de red no puede crear dos facturas ni cobrar dos veces.

**Autoridad:** IETF `Idempotency-Key` (borrador); criterio de ingeniería.

---

### Pregunta 16 — ¿Concurrencia?

**Estado:** DECIDIDO · **Prioridad:** MVP

Bloqueo optimista:

- columna `version` en cada agregado,
- `ETag` en la respuesta,
- `If-Match` obligatorio en actualizaciones,
- `412 Precondition Failed` si la versión no coincide.

Para numeraciones y aplicación de pagos se usa además bloqueo pesimista (`SELECT … FOR UPDATE`) dentro de la transacción.

**Por qué:** dos usuarios editando la misma factura no pueden pisarse; dos pagos simultáneos no pueden sobre-aplicar el mismo saldo.

**Autoridad:** RFC 7232 (`ETag`/`If-Match`); criterio de ingeniería.

---

### Pregunta 17 — ¿Webhooks?

**Estado:** POSPUESTO · **Prioridad:** Fase2

El MVP usa consulta por polling. En Fase2 implementamos **outbox** transaccional, firma `HMAC-SHA256` con secreto por suscripción, `timestamp` contra replay, reintentos con backoff exponencial, entrega **al menos una vez**, cola de mensajes muertos y consumidor idempotente por `event_id`.

Eventos mínimos: `invoice.issued`, `invoice.voided`, `payment.applied`, `payment.voided`, `credit_note.applied`.

**Por qué:** un webhook dentro de la transacción de facturación puede perder eventos o bloquear la emisión; el outbox los desacopla.

**Autoridad:** criterio de ingeniería (outbox, at-least-once, idempotencia).

---

### Pregunta 18 — ¿Notas crédito?

**Estado:** DECIDIDO · **Prioridad:** MVP

La nota crédito es un **documento separado** que referencia obligatoriamente una factura emitida, tiene líneas, impuestos y motivo, aplica su valor contra el saldo de la factura y no puede superar el saldo ni el total. **No edita ni borra** la factura original.

Se anula con otra nota o con un proceso de anulación; nunca se elimina. La nota crédito electrónica DIAN se implementa en Fase2.

**Por qué:** la factura es inmutable; la corrección se documenta, no se reescribe.

**Autoridad:** práctica contable; NIIF 15; normativa DIAN de notas crédito.

**REQUIERE VALIDACIÓN:** requisitos, referencia al CUFE y efectos de la nota crédito electrónica.

---

### Pregunta 19 — ¿Anulación y contabilidad?

**Estado:** DECIDIDO · **Prioridad:** MVP

- Un documento **emitido** nunca se borra: se anula (`void`) y se conserva.
- La anulación genera un asiento de reversión y deja rastro de auditoría.
- Un **borrador** sí se puede eliminar físicamente.
- Los pagos se anulan, no se borran.
- El log de auditoría es *append-only*.

**Por qué:** borrar un documento emitido rompe la trazabilidad fiscal y contable. La anulación deja historia; el borrado la destruye.

**Autoridad:** práctica contable; NIIF; normativa DIAN de conservación de documentos.

**REQUIERE VALIDACIÓN:** plazos legales de conservación y requisitos de archivo.

---

### Pregunta 20 — ¿Zona horaria?

**Estado:** DECIDIDO · **Prioridad:** MVP

- Fechas de negocio (`date`, `due_date`): tipo `DATE`, sin hora, interpretadas en `America/Bogota`.
- Marcas de tiempo (`created_at`, `issued_at`, `voided_at`): `TIMESTAMP WITH TIME ZONE`, almacenadas en UTC.
- Serialización: ISO 8601 / RFC 3339 con offset (`2026-10-21T15:04:05-05:00`).
- Reportes y cierres: se agrupan por fecha de Bogotá.
- Nunca se usa la zona horaria del servidor.

**Por qué:** una factura emitida a las 23:30 en Bogotá no puede caer en el día siguiente por un servidor en UTC.

**Autoridad:** ISO 8601; RFC 3339; práctica contable.

---

### Pregunta 21 — ¿Versionado de la API?

**Estado:** DECIDIDO · **Prioridad:** MVP

- Versión en la ruta: `/v1`.
- Cambios **aditivos** no rompen: campos nuevos opcionales, endpoints nuevos.
- Cambios **rupturistas** van a `/v2`; nunca se cambia el significado de un campo en la misma versión.
- Deprecación anunciada con 6 meses de antelación.
- Cabeceras `Deprecation` y `Sunset`.
- Contrato OpenAPI versionado en el repositorio y probado en CI.

**Por qué:** los clientes de facturación no pueden actualizar de un día para otro; necesitan una ventana predecible.

**Autoridad:** RFC 8594 (`Sunset`); criterio de ingeniería.

> **DESCARTADO:** versionar por cabecera (`Accept: application/vnd.facturalibre.v2+json`) o por query param. Añade complejidad sin beneficio para nuestro caso.

---

### Pregunta 22 — ¿Límite por usuario?

**Estado:** DECIDIDO · **Prioridad:** MVP

No copiamos el límite de Alegra. Definimos cuota propia:

- **token bucket** por `tenant_id` y por token,
- límite sostenido y ráfaga configurables,
- `429 Too Many Requests` con `Retry-After`,
- cabeceras `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`,
- trabajos internos usan cola y no compiten con usuarios.

**Por qué:** el límite debe proteger el sistema y ser justo con cada tenant, no replicar un número arbitrario de otro producto.

**Autoridad:** RFC 6585 (`429`); criterio de ingeniería.

> **DESCARTADO:** heredar los 150 req/min de Alegra como constante del producto.

---

## 4. Lo que NO podemos decidir solos

Estas materias **no** se resuelven con criterio de ingeniería. Todas requieren **REQUIERE VALIDACIÓN** con un experto humano antes de implementar.

| Tema | Por qué no lo decidimos solos | A quién consultar |
|---|---|---|
| Reglas exactas de redondeo DIAN | Pueden variar por tipo de documento y versión del anexo técnico. Un centavo mal redondeado invalida el documento. | Contador + experto DIAN |
| Tarifas y bases de retenciones | ReteFuente, ReteIVA y ReteICA dependen de concepto, cuantía, municipio y régimen. | Contador |
| Catálogos DIAN | Tipos de documento, formas de pago, medios de pago, unidades, responsabilidades y códigos de impuesto cambian por resolución. | Experto DIAN |
| Numeración y resoluciones | Prefijo, rango, vigencia, contingencia y autorización son propios de cada empresa. | Contador + experto DIAN |
| Firma y transmisión electrónica | CUFE, certificado, habilitación, software propio y estado del documento. | Proveedor tecnológico autorizado + DIAN |
| Tratamiento de descuentos y retenciones en el XML | La representación fiscal exacta no se deduce de la práctica comercial. | Experto DIAN |
| Aceptación de notas crédito | Efectos y plazos dependen de la normativa y del adquirente. | Contador + abogado |
| Reconocimiento de ingreso y cartera (NIIF) | NIIF 15/9 admiten políticas que deben documentarse y aprobarse. | Contador público |
| Conservación de documentos | Plazos y soportes exigidos por ley. | Abogado + contador |
| Protección de datos | Ley 1581 de 2012 y política de tratamiento de datos personales. | Abogado |
| Términos y condiciones del producto | Licencias, responsabilidad y propiedad intelectual. | Abogado |
| Facturación electrónica de contingencia | Protocolos y habilitación ante caídas. | Experto DIAN |

**Regla interna:** ninguna historia de usuario que toque estos temas se considera «terminada» sin la firma de un responsable humano.

---

## 5. Decisiones de ingeniería propias

Estas son decisiones que Alegra no documenta (o documenta de forma ambigua) y que FacturaLibre toma por su cuenta.

### 5.1 Dinero y precisión

- `Money` es un *value object* inmutable: `amount: Decimal`, `currency: ISO 4217`.
- Prohibido `float`/`double` en dominio, base de datos y serialización.
- JSON serializa montos como string (`"1234.50"`), no como número.
- Redondeo centralizado en una sola función de dominio, nunca disperso.

### 5.2 Identificadores

- Entidades: UUID v7 (ordenable por tiempo, útil para índices).
- Idempotencia: UUID v4 (aleatorio, sin filtración de tiempo).
- Nunca ids autoincrementales expuestos al cliente.

### 5.3 Estado como máquina explícita

- `lifecycle_status` y `payment_status` separados (preguntas 1–3).
- Transiciones válidas declaradas en el dominio; una transición inválida lanza error, no se ignora.
- `payment_status` es derivado y no se puede escribir por API.

### 5.4 Libro de aplicaciones inmutable

- `payment_allocations` es un libro *append-only*.
- Corregir una aplicación = registrar una reversa, no un `UPDATE`.
- El saldo se reconstruye sumando aplicaciones y reversas.

### 5.5 Borrado

- Borrador: *hard delete* permitido.
- Documento emitido: *void* + asiento de reversión; nunca `DELETE`.
- Contactos, ítems e impuestos: *soft delete* con `deleted_at`, y no se pueden borrar si están referenciados.
- Auditoría: *append-only*, sin `UPDATE` ni `DELETE`.

### 5.6 Transacciones y eventos

- Patrón **outbox** para todos los eventos de dominio.
- Publicación *at-least-once*; consumidores idempotentes por `event_id`.
- No se emiten eventos antes del `COMMIT`.

### 5.7 Concurrencia

- `version` + `If-Match`/`ETag` (pregunta 16).
- Bloqueo pesimista solo donde hay contadores: numeración y aplicación de pagos.
- Timeout de transacción corto; sin llamadas externas dentro de la transacción.

### 5.8 API

- OpenAPI 3.1 como contrato fuente; se genera el servidor o se valida contra él.
- Errores con RFC 7807 (`application/problem+json`), con `type`, `title`, `detail`, `instance` y `code` propio.
- Paginación por cursor (`created_at`, `id`), no por offset, para listados grandes.
- `PATCH` con JSON Merge Patch (RFC 7386) para actualizaciones parciales; `PUT` para reemplazo completo de campos mutables.
- Filtros y ordenamientos explícitos y *whitelist*.

### 5.9 Multi-tenencia

- `tenant_id` en todas las tablas de negocio.
- Row Level Security o filtro obligatorio en el repositorio.
- Pruebas automáticas que fallan si una consulta no filtra por tenant.

### 5.10 Adaptación e interoperabilidad

- Capa *anti-corruption* para importar/exportar datos de otros sistemas (incluido Alegra si algún usuario lo pide).
- Los alias (`account`/`bankAccount`, `anotation`/`annotation`) se resuelven en el borde, no en el dominio.
- Ningún nombre de campo de un proveedor externo entra al modelo interno.

### 5.11 Observabilidad

- Cada documento emitido tiene *trace id* y log de eventos.
- Métricas: facturas emitidas, pagos aplicados, errores de validación, latencia de emisión.
- Alertas si el saldo reconstruido no coincide con el calculado.

### 5.12 Pruebas

- Pruebas de propiedad para totales: `sum(lines) == total`, `total - paid == balance`.
- Casos dorados con documentos reales anonimizados.
- Pruebas de contrato contra el OpenAPI.
- Pruebas de concurrencia con dos pagos simultáneos.

---

## 6. Cierre

FacturaLibre no necesita imitar a Alegra: necesita ser **correcto, auditable y explicable**. Las 22 preguntas quedaron resueltas con una decisión explícita o con un aplazamiento consciente; ninguna quedó en «depende».

La regla para el futuro es simple: si una decisión afecta dinero, impuestos o trazabilidad, se documenta aquí, se cita su autoridad y, cuando corresponde, se firma con un experto humano.
