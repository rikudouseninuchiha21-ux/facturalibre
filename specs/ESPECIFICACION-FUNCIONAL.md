# Especificación funcional — API pública de Alegra

> **Proyecto:** FacturaLibre (proyecto educativo)
> **Objeto analizado:** documentación pública de la API de Alegra en `https://developer.alegra.com`
> **Fecha del análisis:** 2026-10-21
> **Naturaleza:** análisis documental, no ingeniería inversa ni uso del servicio.

---

## 0. Alcance, método y leyenda

### 0.1 Qué se hizo

- Se consultaron **únicamente páginas públicas** de `developer.alegra.com` mediante peticiones HTTP `GET` de lectura. **[VISTO: proceso realizado]**
- No se inició sesión, no se generó ni utilizó token, no se enviaron credenciales y **no se llamó a ningún endpoint real** de `api.alegra.com`. **[VISTO: proceso realizado]**
- No se accedió a la aplicación web de Alegra ni a paneles privados. **[VISTO: proceso realizado]**
- Cada página de referencia publica, dentro de su HTML, el esquema OpenAPI del endpoint que documenta (script `#ssr-props`, ruta `document.api.schema`). Ese esquema se leyó como **parte de la documentación pública**, no como un acceso no autorizado. **[VISTO: HTML público de las páginas F2, F3, F9, etc.]**
- Las descripciones, ejemplos, tipos y campos obligatorios que aparecen abajo provienen de ese esquema y de los textos visibles de la documentación. **[VISTO: catálogo de fuentes]**

### 0.2 Qué NO se hizo

- No se probó el comportamiento real de la API (no hay observación de ejecución).
- No se verificaron límites, permisos, idempotencia, concurrencia ni tiempos de respuesta.
- No se analizaron SDKs, código fuente, binarios ni tráfico de red de Alegra.
- No se estudiaron todos los recursos: el foco son `invoices`, `contacts`, `items`, `payments` y `taxes`.
- No se validó la información con una cuenta de prueba.

### 0.3 Leyenda de evidencia

| Marca | Significado |
|---|---|
| **[VISTO]** | Aparece literalmente en la documentación pública citada (texto, esquema OpenAPI o ejemplo). |
| **[INFERIDO]** | Se deduce de la documentación, pero la documentación no lo afirma de forma explícita. |
| **[DESCONOCIDO]** | No se pudo confirmar con la documentación pública. No se inventa un valor. |

Cuando una tabla mezcla varios niveles de evidencia, la columna **Evidencia** lo indica fila por fila.

### 0.4 Catálogo de fuentes

Las referencias `F1`, `F2`, … apuntan a estas URLs públicas. Todas fueron consultadas el 2026-10-21.

| ID | URL | Contenido usado |
|---|---|---|
| F1 | https://developer.alegra.com/reference/get_invoices | Listar facturas, filtros, ejemplo de respuesta |
| F2 | https://developer.alegra.com/reference/post_invoices | Crear factura, cuerpo y esquemas |
| F3 | https://developer.alegra.com/reference/get_invoices-id | Consultar factura, ejemplos de respuesta |
| F4 | https://developer.alegra.com/reference/put_invoices-id | Editar factura |
| F5 | https://developer.alegra.com/reference/delete_invoices-id | Eliminar factura |
| F6 | https://developer.alegra.com/reference/post_invoices-id-void | Anular factura |
| F7 | https://developer.alegra.com/reference/post_invoices-id-open | Abrir / revertir anulación |
| F8 | https://developer.alegra.com/reference/listcontacts-1 | Listar contactos |
| F9 | https://developer.alegra.com/reference/post_contacts | Crear contacto |
| F10 | https://developer.alegra.com/reference/get_items | Listar ítems |
| F11 | https://developer.alegra.com/reference/post_items | Crear ítem |
| F12 | https://developer.alegra.com/reference/get_payments-1 | Listar pagos |
| F13 | https://developer.alegra.com/reference/post_payments-1 | Crear pago |
| F14 | https://developer.alegra.com/reference/post_payments-id-void-1 | Anular pago |
| F15 | https://developer.alegra.com/reference/post_payments-id-open-1 | Convertir pago a abierto |
| F16 | https://developer.alegra.com/reference/get_taxes | Listar impuestos |
| F17 | https://developer.alegra.com/reference/post_taxes | Crear impuesto |
| F18 | https://developer.alegra.com/reference/autenticación | Autenticación Basic |
| F19 | https://developer.alegra.com/reference/límite-de-request | Límite de peticiones |
| F20 | https://developer.alegra.com/reference/respuestas-del-api-y-manejo-de-errores | Códigos HTTP |
| F21 | https://developer.alegra.com/docs/términos-y-condiciones-api-alegra | Términos y condiciones del API |
| F22 | https://developer.alegra.com/docs/pagos-2 | Concepto de pagos |
| F23 | https://developer.alegra.com/docs/facturas-de-venta-1 | Concepto de factura |
| F24 | https://developer.alegra.com/docs/contactos | Concepto de contacto |
| F25 | https://developer.alegra.com/docs/productos-y-servicios | Concepto de ítem |
| F26 | https://developer.alegra.com/docs/numeración-de-documentos | Numeraciones |
| F27 | https://developer.alegra.com/reference/get_terms | Listar términos de pago |
| F28 | https://developer.alegra.com/reference/get_currencies | Listar monedas |
| F29 | https://developer.alegra.com/reference/get_retentions | Listar retenciones |
| F30 | https://developer.alegra.com/docs/información-general | Principios REST, métodos y formato JSON |

> Las páginas citadas por su slug (`post_invoices-id-email`, `contactsdetails-1`, `editcontact`, `get_items-id`, etc.) se localizan en `https://developer.alegra.com/reference/<slug>`.

> **Nota de trazabilidad:** las URLs no exponen números de línea estables. Por eso se cita `F#` y, cuando hace falta precisión, la sección o el nombre del campo del esquema (por ejemplo, «`post_invoices` → `components.schemas.PostGeneral.required`»).

---

## 1. Recursos principales de la API

La API se presenta como REST sobre JSON, con servidor `https://api.alegra.com/api/v1` y autenticación Basic. **[VISTO: F2, `servers`; F18]**

| Recurso | Ruta | Función documentada | Evidencia |
|---|---|---|---|
| Facturas de venta (`invoices`) | `/invoices` | Documentos de venta: creación, consulta, edición, anulación y envío por correo. | **[VISTO: F1, F2]** |
| Contactos (`contacts`) | `/contacts` | Clientes y proveedores; pueden ser ambos o ninguno. | **[VISTO: F8, F24]** |
| Ítems (`items`) | `/items` | Productos y servicios vendidos o comprados. | **[VISTO: F10, F25]** |
| Pagos (`payments`) | `/payments` | Recibos de caja (`type: in`) y comprobantes de egreso (`type: out`). | **[VISTO: F12, F22]** |
| Impuestos (`taxes`) | `/taxes` | Catálogo de impuestos reutilizable por ítems y facturas. | **[VISTO: F16, F17]** |
| Términos de pago (`terms`) | `/terms` | Plazos de vencimiento (contado, 8/15/30/60 días, manual). | **[VISTO: F27; F26]** |
| Monedas (`currencies`) | `/currencies` | Monedas y tasas de cambio. | **[VISTO: F28]** |
| Retenciones (`retentions`) | `/retentions` | Retenciones aplicables a facturas y pagos. | **[VISTO: F29]** |
| Numeraciones | `/number-templates` | Series/folios de facturación. El path exacto se menciona en la guía; no se abrió su página de referencia. | **[INFERIDO: F26 menciona «Endpoint /number-templates»; path no verificado en referencia]** |

**Idea clave del modelo:** una factura no «contiene» impuestos a nivel de cabecera; cada línea de la factura referencia uno o varios impuestos del catálogo. El total se construye línea por línea. **[VISTO: F2, `items[].tax`; F3, ejemplo de totales]**

### 1.1 Relaciones de alto nivel

```text
contacts 1 ──── N invoices
items    1 ──── N invoice.items
taxes    N ──── N invoice.items          (vía items[].tax[].id)
invoices 1 ──── N payments.invoices      (vía payments[].invoices[].id)
invoices 1 ──── N retentions             (vía retentions[].id)
invoices N ──── 1 number-templates
invoices N ──── 1 sellers
invoices N ──── 1 price-lists
invoices N ──── 1 warehouses
invoices N ──── 1 cost-centers
contacts N ──── 1 terms
contacts N ──── 1 sellers
items    N ──── N taxes                  (vía tax[].id)
items    N ──── 1 item-categories
taxes    N ──── 1 accounting-accounts    (cuenta a favor / por pagar)
payments N ──── 1 bank-accounts
```

**[VISTO]** para cada arista que se muestra con un `id` en los esquemas F2, F3, F9, F11, F13, F17. **[INFERIDO]** la cardinalidad (1:N / N:N), que no se declara formalmente pero se desprende de que los campos son arreglos o referencias por id.

---

## 2. Recursos: campos, tipos y relaciones

### 2.1 Facturas de venta (`invoices`)

#### 2.1.1 Cuerpo de creación (`POST /invoices`)

El esquema es un `oneOf` con una variante «simple» y variantes por país (México, Colombia, Argentina, Perú, Panamá, Chile, Costa Rica, República Dominicana, España). **[VISTO: F2, `requestBody.content['application/json'].schema.oneOf`]**

Campos de la variante general:

| Campo | Tipo | Obligatorio | Notas | Evidencia |
|---|---|---|---|---|
| `date` | string (`date`, `yyyy-MM-dd`) | **Sí** | Fecha de la factura. | **[VISTO: F2, `PostGeneral.required`]** |
| `dueDate` | string (`date`, `yyyy-MM-dd`) | **Sí** | Fecha de vencimiento. | **[VISTO: F2, `PostGeneral.required`]** |
| `client` | object `{ id: string }` | **Sí** | Contacto asociado. El texto dice que también se puede enviar el id directamente, aunque el esquema lo tipa como objeto. | **[VISTO: F2]** |
| `items` | array de objetos | **Sí** | Mínimo una línea. | **[VISTO: F2, `PostGeneral.required`; F23]** |
| `items[].id` | string | **Sí** (según descripción) | Id del producto/servicio. | **[VISTO: F2, descripción de `items`]** |
| `items[].price` | number | **Sí** (según descripción) | Precio unitario **sin impuestos ni descuentos**. | **[VISTO: F2, descripción de `items`]** |
| `items[].quantity` | number | **Sí** (según descripción) | Cantidad vendida. | **[VISTO: F2, descripción de `items`]** |
| `items[].discount` | number | No | Porcentaje de descuento, sin el símbolo `%`. En Costa Rica pasa a ser un objeto `{ nature, discount }`. | **[VISTO: F2]** |
| `items[].tax` | array `[{ id: string }]` | No | Impuestos aplicados a la línea. | **[VISTO: F2]** |
| `items[].description` | string | No | Descripción de la línea. | **[VISTO: F2]** |
| `items[].reference` | string | No | Referencia del producto/servicio. | **[VISTO: F2]** |
| `items[].name` | string | No | Nombre del producto. | **[VISTO: F2]** |
| `items[].observations` | string | No | Observaciones de la línea. | **[VISTO: F2]** |
| `status` | string | No | Solo documenta `open` o `draft`. Si se omite y no hay pagos, se crea `draft`; si hay pagos, `open`. | **[VISTO: F2]** |
| `numberTemplate` | object `{ id, prefix?, number? }` | No | Si se omite, se usa la numeración preferida de la empresa. En numeración manual se requiere `id` y `number`. | **[VISTO: F2, F26]** |
| `payments` | array de objetos | No | Permite registrar pagos al crear la factura. | **[VISTO: F2]** |
| `payments[].date` | string (`date`) | **Sí** (si se envía pago) | Fecha del pago. | **[VISTO: F2, descripción de `payments`]** |
| `payments[].account` | object `{ id }` | **Sí** (si se envía pago) | Cuenta bancaria que recibe el dinero. | **[VISTO: F2, descripción de `payments`]** |
| `payments[].amount` | number | **Sí** (si se envía pago) | Valor pagado. | **[VISTO: F2, descripción de `payments`]** |
| `payments[].paymentMethod` | string | No | Enum: `cash`, `check`, `transfer`, `deposit`, `credit-card`, `debit-card`. | **[VISTO: F2]** |
| `payments[].annotations` | string | No | Notas del pago (el texto usa `annotations`; el esquema usa `anotations` en otros lugares). | **[VISTO: F2]** |
| `payments[].observations` | string | No | Observaciones del pago. | **[VISTO: F2]** |
| `payments[].retentions` | array `[{ id, amount }]` | No | Retenciones aplicadas en el pago. | **[VISTO: F2]** |
| `payments[].currency` | object `{ code, exchangeRate }` | No | Moneda y tasa del pago. | **[VISTO: F2]** |
| `observations` | string (máx. 500) | No | No visible en el PDF. | **[VISTO: F2]** |
| `anotation` | string (máx. 500) | No | Visible en el PDF. | **[VISTO: F2]** |
| `termsConditions` | string (máx. 500) | No | Términos y condiciones. | **[VISTO: F2]** |
| `seller` | object/string | No | Vendedor asociado. | **[VISTO: F2]** |
| `priceList` | object/string | No | Lista de precios. | **[VISTO: F2]** |
| `currency` | object `{ code, exchangeRate }` | No | Solo si la empresa tiene multimoneda activa. | **[VISTO: F2]** |
| `retentions` | array `[{ id, amount }]` | No | Retenciones de la factura. | **[VISTO: F2]** |
| `warehouse` | object/string | No | Bodega; si se omite, va a la principal. | **[VISTO: F2]** |
| `remissions` | array de ids | No | Remisiones que se facturan. | **[VISTO: F2]** |
| `costCenter` | object/string | No | Centro de costo. | **[VISTO: F2]** |
| `comments` | array de strings | No | Comentarios editables aun si la factura no se puede editar. | **[VISTO: F2]** |
| `periodicity` | string | No | Enum: `BIWEEKLY`, `MONTHLY`, `BIMONTHLY`, `QUARTERLY`, `SEMIANNUALLY`, `MANUAL`. Obligatorio si la venta es a crédito y se emite. | **[VISTO: F2]** |
| `estimate` | string | No | Id de cotización que queda facturada. | **[VISTO: F2]** |

**Campos por país:** México, Colombia, Argentina, Perú, Panamá, Chile, Costa Rica, República Dominicana y España agregan campos fiscales propios (por ejemplo `paymentMethod`, `cfdiUse`, `stamp`, `regimeClient`, `ivaCondition`, etc.). **[VISTO: F2, `oneOf`]** El detalle completo de cada catálogo fiscal **no se analizó en este documento** y queda como **[DESCONOCIDO]**.

#### 2.1.2 Campos de respuesta

| Campo | Tipo | Notas | Evidencia |
|---|---|---|---|
| `id` | string | Identificador de la factura. | **[VISTO: F1, F2, F3]** |
| `date`, `dueDate` | string (`yyyy-MM-dd`) | Fechas del documento. | **[VISTO: F1]** |
| `datetime` | string (`yyyy-MM-dd HH:mm:ss`) | Fecha/hora de creación. | **[VISTO: F1]** |
| `status` | string | `open`, `closed`, `draft` o `void`. | **[VISTO: F1, parámetro `status`]** |
| `client` | object | Snapshot del contacto (id, nombre, identificación, email, teléfonos, dirección). | **[VISTO: F1]** |
| `numberTemplate` | object o array | En algunos ejemplos aparece como objeto y en otros como array. | **[VISTO: F1, F2]** |
| `items` | array | Líneas con `price`, `quantity`, `discount`, `tax`, y en algunos países `total` por línea. | **[VISTO: F1, F3]** |
| `payments` | array | Pagos asociados, con `id`, `number`, `date`, `amount`, `paymentMethod`, `status`. | **[VISTO: F1]** |
| `retentions` | array | `id`, `name`, `percentage`, `amount`. | **[VISTO: F1]** |
| `seller` | object | Vendedor. | **[VISTO: F1]** |
| `priceList` | object | Lista de precios. | **[VISTO: F1]** |
| `currency` | object `{ code, symbol, exchangeRate }` | Moneda de la factura. | **[VISTO: F1]** |
| `total` | number | Total de la factura. | **[VISTO: F1]** |
| `totalPaid` | number | Total pagado. | **[VISTO: F1]** |
| `balance` | number | Saldo pendiente. | **[VISTO: F1]** |
| `decimalPrecision` | number o string | En ejemplos: `2` y `"2"`. | **[VISTO: F1, F3]** |
| `subtotal` | number | **Solo aparece en el ejemplo de Costa Rica**; no está en el ejemplo genérico. | **[VISTO: F3, ejemplo `GetInvoiceCostaRica44Fields`]** |
| `discount` | number | **Solo en el ejemplo de Costa Rica.** | **[VISTO: F3]** |
| `tax` | number | **Solo en el ejemplo de Costa Rica.** | **[VISTO: F3]** |
| `totalsSummary` | object | Desglose por servicios/productos, bases y tarifas. **Solo en el ejemplo de Costa Rica.** | **[VISTO: F3]** |
| `totalsPendingByTaxes` | array | Bases, impuesto y total pendiente por tarifa. **Solo en el ejemplo de Costa Rica.** | **[VISTO: F3]** |
| `warehouse`, `costCenter`, `term`, `saleCondition`, `paymentMethod`, `type`, `economicActivity` | varios | Campos adicionales vistos en ejemplos de países. | **[VISTO: F3]** |

> **Hallazgo importante:** la forma de la respuesta **no es uniforme entre países/versiones**. `subtotal`, `discount` y `tax` no aparecen en el ejemplo genérico, y hay campos que solo existen en ciertos países. Un cliente de la API debe tratar esos campos como opcionales. **[VISTO: F1 vs. F3]**

#### 2.1.3 Relaciones

| Relación | Campo | Destino | Evidencia |
|---|---|---|---|
| Factura → Contacto | `client.id` | `/contacts/{id}` | **[VISTO: F2, F9]** |
| Factura → Ítem | `items[].id` | `/items/{id}` | **[VISTO: F2, F11]** |
| Factura → Impuesto | `items[].tax[].id` | `/taxes/{id}` | **[VISTO: F2, F17]** |
| Factura → Pago | `payments[].id` / `payments[].invoices[].id` | `/payments/{id}` | **[VISTO: F1, F13]** |
| Factura → Retención | `retentions[].id` | `/retentions/{id}` | **[VISTO: F2, F29]** |
| Factura → Numeración | `numberTemplate.id` | `/number-templates` | **[VISTO: F2, F26]** |
| Factura → Vendedor | `seller.id` | `/sellers/{id}` (según sidebar) | **[VISTO: F2; path de sellers no abierto → INFERIDO]** |
| Factura → Lista de precios | `priceList.id` | `/price-lists/{id}` | **[VISTO: F2; path no abierto → INFERIDO]** |
| Factura → Bodega | `warehouse.id` | `/warehouses/{id}` | **[VISTO: F2; path no abierto → INFERIDO]** |
| Factura → Centro de costo | `costCenter.id` | `/cost-centers/{id}` | **[VISTO: F2; path no abierto → INFERIDO]** |
| Factura → Cotización | `estimate` | `/estimates/{id}` | **[VISTO: F2; path no abierto → INFERIDO]** |
| Factura → Remisión | `remissions[]` | `/remissions/{id}` | **[VISTO: F2; path no abierto → INFERIDO]** |

---

### 2.2 Contactos (`contacts`)

#### 2.2.1 Campos (variante general)

| Campo | Tipo | Obligatorio | Notas | Evidencia |
|---|---|---|---|---|
| `name` | string | **Sí** | Nombre del contacto. | **[VISTO: F9, `required: ["name"]`]** |
| `identification` | string | No (en la variante general) | Identificación fiscal. En varios países con facturación electrónica pasa a ser obligatoria o a llamarse `identificationObject`. | **[VISTO: F9]** |
| `type` | string o array | No | `client`, `provider` o ambos. El ejemplo devuelve `["client","provider"]`. | **[VISTO: F8, F9]** |
| `status` | string | No | Enum `active` / `inactive`. | **[VISTO: F9]** |
| `email` | string | No | Correo. | **[VISTO: F9]** |
| `phonePrimary`, `phoneSecondary`, `mobile`, `fax` | string | No | Teléfonos. | **[VISTO: F9]** |
| `address` | object `{ city, address }` | No | Dirección. | **[VISTO: F9]** |
| `seller` | string (id) | No | Vendedor asociado. | **[VISTO: F9]** |
| `priceList` | string (id) | No | Lista de precios. | **[VISTO: F9]** |
| `term` | string (id) | No | Término de pago. | **[VISTO: F9, F27]** |
| `creditLimit` | number | No | Límite de crédito. | **[VISTO: F9]** |
| `accounting` | object `{ debtToPay, accountReceivable }` | No | Cuentas contables por pagar/cobrar. | **[VISTO: F9]** |
| `internalContacts` | array | No | Personas de contacto; cada una requiere `name`. | **[VISTO: F9]** |
| `ignoreRepeated` | boolean | No | Ignora duplicados por identificación. | **[VISTO: F9]** |
| `statementAttached` | string | No | Enum `yes` / `no`. | **[VISTO: F9]** |

#### 2.2.2 Obligatorios por país (facturación electrónica)

| País / variante | Campos obligatorios | Evidencia |
|---|---|---|
| Genérica | `name` | **[VISTO: F9]** |
| Chile con facturación electrónica | `name`, `identification`, `giro` | **[VISTO: F9]** |
| Colombia con facturación electrónica | `identificationObject`, `regime`, `kindOfPerson` | **[VISTO: F9]** |
| México con facturación electrónica | `name`, `thirdType`, `regime`, `regimeObject`, `address` | **[VISTO: F9]** |
| Argentina sin facturación electrónica | `name`, `ivaCondition` | **[VISTO: F9]** |
| Costa Rica con facturación electrónica | `name`, `identificationObject` | **[VISTO: F9]** |
| Panamá con facturación electrónica | `name`, `thirdsType`, `identificationObject` | **[VISTO: F9]** |

> La documentación tiene **18 variantes** de contacto según país y si hay facturación electrónica. **[VISTO: F9, `oneOf`]** No se validó cuál aplica a una empresa concreta; eso depende de la configuración de la cuenta. **[DESCONOCIDO]**

#### 2.2.3 Relaciones

| Relación | Campo | Destino | Evidencia |
|---|---|---|---|
| Contacto → Vendedor | `seller` | `/sellers/{id}` | **[VISTO: F9; path no abierto → INFERIDO]** |
| Contacto → Lista de precios | `priceList` | `/price-lists/{id}` | **[VISTO: F9; path no abierto → INFERIDO]** |
| Contacto → Término de pago | `term` | `/terms/{id}` | **[VISTO: F9, F27]** |
| Contacto → Cuentas contables | `accounting.*` | `/ledger/categories` (sidebar) | **[VISTO: F9; path de contabilidad no abierto → INFERIDO]** |
| Contacto ← Facturas | — | `invoices[].client.id` | **[VISTO: F2]** |

**Regla de negocio documentada:** un contacto puede ser cliente, proveedor, ambos o ninguno; la clasificación es informativa y **no impide** asociarle facturas de venta. **[VISTO: F24]**

---

### 2.3 Ítems (`items`)

| Campo | Tipo | Obligatorio | Notas | Evidencia |
|---|---|---|---|---|
| `name` | string (máx. 150) | **Sí** | Nombre del producto/servicio. | **[VISTO: F11, `required: ["name","price"]`]** |
| `price` | number o array | **Sí** | Puede ser un precio único o una lista `[{ idPriceList, price }]`. | **[VISTO: F11]** |
| `description` | string (máx. 500) | No | Descripción. | **[VISTO: F11]** |
| `reference` | string (máx. 45) u objeto | No | En Costa Rica es un objeto. | **[VISTO: F11]** |
| `type` | string | No | Enum: `product`, `service`, `variantParent`, `kit`. | **[VISTO: F11]** |
| `tax` | string o array `[{ id }]` | No | Impuestos asociados. | **[VISTO: F11]** |
| `category` | object `{ id }` | No | Si se omite, se asocia a «Ventas». | **[VISTO: F11]** |
| `itemCategory` | object `{ id }` | No | Categoría de ítem. | **[VISTO: F11]** |
| `inventory` | object | No | Solo para productos inventariables; se omite en servicios. | **[VISTO: F11, F25]** |
| `inventory.unit` | string | **Sí** (si hay inventario) | Unidad de medida; enum amplio (`unit`, `meter`, `piece`, etc.). | **[VISTO: F11, descripción]** |
| `inventory.unitCost` | number | **Sí** (si hay inventario) | Costo unitario. | **[VISTO: F11, descripción]** |
| `inventory.initialQuantity` | number | **Sí** (si hay inventario) | Cantidad inicial. | **[VISTO: F11, descripción]** |
| `inventory.warehouses` | array `[{ id, initialQuantity, minQuantity?, maxQuantity? }]` | No | Distribución por bodega. | **[VISTO: F11]** |
| `inventory.negativeSale` | boolean | No | Permite vender sin stock. | **[VISTO: F11]** |
| `accounting` | object `{ inventory, inventariablePurchase }` | No | Cuentas contables del ítem inventariable. | **[VISTO: F11]** |
| `customFields` | array | No | Campos adicionales. | **[VISTO: F11]** |
| `subitems` | array | Condicional | Obligatorio si `type = kit`. | **[VISTO: F11, descripción]** |
| `variantAttributes` | array | Condicional | Obligatorio si `type = variantParent`. | **[VISTO: F11, descripción]** |
| `status` | string | No | `active` / `inactive` (visto en respuestas). | **[VISTO: F10]** |

> **Inconsistencia detectada:** el esquema de `inventory` describe `unit`, `unitCost` e `initialQuantity` como obligatorios, pero el objeto no declara un arreglo `required` propio. Se toma como obligatoriedad **documentada en la descripción**, no validada por esquema. **[VISTO: F11; INFERIDO: obligatoriedad efectiva]**

#### 2.3.1 Relaciones

| Relación | Campo | Destino | Evidencia |
|---|---|---|---|
| Ítem → Impuesto | `tax[].id` | `/taxes/{id}` | **[VISTO: F11, F17]** |
| Ítem → Categoría contable | `category.id` | Plan de cuentas | **[VISTO: F11]** |
| Ítem → Categoría de ítem | `itemCategory.id` | `/item-categories/{id}` | **[VISTO: F11]** |
| Ítem → Lista de precios | `price[].idPriceList` | `/price-lists/{id}` | **[VISTO: F11]** |
| Ítem → Bodega | `inventory.warehouses[].id` | `/warehouses/{id}` | **[VISTO: F11]** |
| Ítem ← Líneas de factura | — | `invoices[].items[].id` | **[VISTO: F2]** |

---

### 2.4 Pagos (`payments`)

#### 2.4.1 Cuerpo de creación (`POST /payments`)

| Campo | Tipo | Obligatorio | Notas | Evidencia |
|---|---|---|---|---|
| `date` | string (`yyyy-MM-dd`) | **Sí** | Fecha del pago. | **[VISTO: F13, `schemas_PostGeneral.required`]** |
| `bankAccount` | object `{ id }` | **Sí** | Cuenta bancaria de origen/destino. | **[VISTO: F13]** |
| `type` | string | Condicional | `in` (ingreso) u `out` (egreso). **Obligatorio cuando el pago se hace a una categoría.** | **[VISTO: F13]** |
| `paymentMethod` | string | No | Enum: `cash`, `check`, `transfer`, `deposit`, `credit-card`, `debit-card`. | **[VISTO: F13]** |
| `client` | object `{ id }` | No | Cliente asociado. Si el pago aplica a facturas, todas deben ser del mismo cliente. | **[VISTO: F13, descripción]** |
| `invoices` | array | No | Facturas de venta que se pagan. | **[VISTO: F13]** |
| `invoices[].id` | string | **Sí** (si se envía `invoices`) | Id de la factura. | **[VISTO: F13, descripción]** |
| `invoices[].amount` | number | **Sí** (si se envía `invoices`) | Valor aplicado a esa factura. | **[VISTO: F13, descripción]** |
| `invoices[].retentions` | array `[{ id, amount }]` | No | Retenciones aplicadas en el pago. | **[VISTO: F13]** |
| `bills` | array | No | Facturas de compra que se pagan (misma forma que `invoices`). | **[VISTO: F13]** |
| `categories` | array | No | Categorías pagadas: `{ id, tax, quantity, price, observations }`. | **[VISTO: F13]** |
| `retentions` | array | No | Retenciones del pago. | **[VISTO: F13]** |
| `currency` | object `{ code, exchangeRate }` | No | Moneda del pago. | **[VISTO: F13]** |
| `costCenter` | object | No | Centro de costo. | **[VISTO: F13]** |
| `observations` | string (máx. 500) | No | No visible en el documento impreso. | **[VISTO: F13]** |
| `anotation` | string (máx. 500) | No | Visible en el documento impreso. | **[VISTO: F13]** |
| `comments` | array | No | Comentarios. | **[VISTO: F13]** |
| `numberTemplate` | object `{ id }` | No | Numeración del pago; si se omite, se usa la preferida. | **[VISTO: F13]** |

> **No hay un campo `amount` de nivel superior** en el esquema de pago: el valor se expresa por factura (`invoices[].amount`) o por categoría (`categories[].price` × `quantity`). **[VISTO: F13]** Si la API devuelve un total agregado, la documentación no lo muestra. **[DESCONOCIDO]**

#### 2.4.2 Respuesta y estados

| Campo | Tipo | Notas | Evidencia |
|---|---|---|---|
| `id` | string | Id del pago. | **[VISTO: F12, F13]** |
| `date` | string | Fecha. | **[VISTO: F12]** |
| `paymentMethod` | string | Medio de pago. | **[VISTO: F12]** |
| `client` | object o `null` | Puede ser nulo en pagos por categoría. | **[VISTO: F12]** |
| `invoices` | array | Facturas pagadas con `total`, `totalPaid`, `balance`. | **[VISTO: F12]** |
| `bankAccount` | object | Cuenta. | **[VISTO: F12]** |
| `currency` | object | Moneda. | **[VISTO: F12]** |
| `appliedAdvances` | array | Anticipos aplicados. | **[VISTO: F12]** |
| `type` | string | En el ejemplo de pago por categoría aparece `type: "in"`. | **[VISTO: F12]** |
| `status` | string | `open` es el estado natural; `void` es anulado. | **[VISTO: F14, F15]** |

**Regla documentada de anulación:** anular un pago «sirve para mantener registro del pago pero que este documento no tenga efecto en la contabilidad o reportes». Se reconoce por `status = "void"`. **[VISTO: F14]** Convertirlo a abierto lo devuelve a `status = "open"`. **[VISTO: F15]**

#### 2.4.3 Relaciones

| Relación | Campo | Destino | Evidencia |
|---|---|---|---|
| Pago → Factura de venta | `invoices[].id` | `/invoices/{id}` | **[VISTO: F12, F13]** |
| Pago → Factura de compra | `bills[].id` | `/bills/{id}` | **[VISTO: F13; path de bills no abierto → INFERIDO]** |
| Pago → Categoría | `categories[].id` | Categorías contables | **[VISTO: F13]** |
| Pago → Cuenta bancaria | `bankAccount.id` | `/bank-accounts/{id}` | **[VISTO: F13]** |
| Pago → Contacto | `client.id` | `/contacts/{id}` | **[VISTO: F13]** |
| Pago → Retención | `retentions[].id` | `/retentions/{id}` | **[VISTO: F13, F29]** |
| Pago → Centro de costo | `costCenter.id` | `/cost-centers/{id}` | **[VISTO: F13]** |

---

### 2.5 Impuestos (`taxes`)

| Campo | Tipo | Obligatorio | Notas | Evidencia |
|---|---|---|---|---|
| `name` | string | No declarado | Nombre del impuesto (ej. «IVA»). | **[VISTO: F17]** |
| `percentage` | number | No declarado | Tarifa del impuesto. El rango válido no se documenta. | **[VISTO: F17; rango DESCONOCIDO]** |
| `description` | string | No | Descripción. | **[VISTO: F17]** |
| `type` | string | No declarado | El esquema lo deja como string libre; no publica un enum. | **[VISTO: F17; catálogo de valores DESCONOCIDO]** |
| `status` | string | No | `active` / `inactive` (visible en respuestas y en la variante Colombia). | **[VISTO: F16, F17]** |
| `categoryFavorable` | object `{ id }` | No | Cuenta contable del impuesto a favor. | **[VISTO: F17]** |
| `categoryToBePaid` | object `{ id }` | No | Cuenta contable del impuesto por pagar. | **[VISTO: F17]** |
| `metadata.rate` | string | No | Solo en la variante Colombia. | **[VISTO: F17]** |
| `rate` | string o `null` | — | Aparece en la respuesta. | **[VISTO: F16]** |

> **Obligatoriedad no declarada:** el `requestBody` de `POST /taxes` no incluye un arreglo `required`. La documentación **no confirma** qué campos son obligatorios en la práctica. No se debe asumir que `name` y `percentage` lo sean sin probarlo. **[VISTO: F17, ausencia de `required`; DESCONOCIDO: obligatoriedad efectiva]**

#### 2.5.1 Uso y relaciones

- Un impuesto se asocia a un ítem mediante `items[].tax[].id` o a una línea de factura. **[VISTO: F11, F2]**
- Cada línea puede llevar **varios** impuestos (`tax` es un array). **[VISTO: F2]**
- `categoryFavorable` y `categoryToBePaid` apuntan a cuentas contables; su id se envía como string. **[VISTO: F17]**
- No se documenta si los impuestos son compuestos, si se suman en cascada ni si admiten tasas negativas. **[DESCONOCIDO]**

---

### 2.6 Recursos de apoyo

| Recurso | Campos relevantes | Evidencia |
|---|---|---|
| Términos de pago (`/terms`) | `id`, `name`, `days` (ej. «8 días», 8). Al registrarse se crean 6 términos por defecto: 8, 15, 30, 60 días, contado y vencimiento manual. | **[VISTO: F27, F26]** |
| Monedas (`/currencies`) | Código ISO de 3 letras y tasa de cambio; la factura usa `{ code, exchangeRate }`. | **[VISTO: F28, F2]** |
| Retenciones (`/retentions`) | `id`, `name`, `percentage`, `amount`; se aplican a facturas y pagos. | **[VISTO: F29, F1]** |
| Numeraciones (`/number-templates`) | `id`, `prefix`, `number`, `text`; el path exacto no se abrió. | **[VISTO: F26; path INFERIDO]** |

---

## 3. Estados posibles de una factura

### 3.1 Estados documentados

| Estado | ¿Aparece en la documentación? | Significado documentado | Evidencia |
|---|---|---|---|
| `draft` | Sí | Borrador. Es el estado por defecto si se crea sin pagos. La factura en `draft` **se puede eliminar**. | **[VISTO: F2, F5]** |
| `open` | Sí | Estado por defecto si se crea con pagos. La documentación **no define** su significado. | **[VISTO: F2; significado DESCONOCIDO]** |
| `closed` | Sí | Estado aceptado por el filtro `status` de la lista. La documentación **no explica** su significado. | **[VISTO: F1; significado DESCONOCIDO]** |
| `void` | Sí | Factura anulada; se llega por `POST /invoices/{id}/void`. | **[VISTO: F1, F6]** |
| `paid` | **No** | No aparece en el enum documentado. | **[VISTO: ausencia; DESCONOCIDO si existe internamente]** |

### 3.2 Interpretación propuesta (no confirmada)

| Afirmación | Evidencia |
|---|---|
| `draft` = borrador editable, sin efectos contables, eliminable. | **[INFERIDO]** a partir de que solo se puede eliminar en `draft` **[VISTO: F5]** y de que es el estado por defecto sin pagos **[VISTO: F2]**. |
| `open` = factura emitida con saldo pendiente. | **[INFERIDO]** a partir de que se crea con pagos parciales y conserva `balance` **[VISTO: F1, F2]**. |
| `closed` = factura totalmente pagada / cerrada. | **[INFERIDO]**; no hay texto que lo defina. |
| `void` = anulada, conserva el registro pero no afecta contabilidad ni reportes. | **[VISTO]** para pagos **[F14]**; **[INFERIDO]** para facturas, por analogía con la anulación. |
| Una factura pasa de `open` a `closed` automáticamente al pagar el total. | **[INFERIDO]**; no documentado. |
| «Pagada» en la interfaz corresponde a `closed`, no a un estado `paid`. | **[INFERIDO]**. |

### 3.3 Transiciones que la documentación sí permite afirmar

| Transición | Cómo | Evidencia |
|---|---|---|
| (nueva) → `draft` | `POST /invoices` sin `status` y sin `payments`. | **[VISTO: F2]** |
| (nueva) → `open` | `POST /invoices` con `payments`, o con `status: open`. | **[VISTO: F2]** |
| `draft` → eliminada | `DELETE /invoices/{id}` (solo en borrador). | **[VISTO: F5]** |
| `open`/`closed` → `void` | `POST /invoices/{id}/void` con `{ cause }` opcional. | **[VISTO: F6]** |
| `void` → abierta | `POST /invoices/{id}/open`; revierte la anulación. | **[VISTO: F7]** |
| `draft` → `open` por edición | No documentado. | **[DESCONOCIDO]** |
| `open` → `closed` | No documentado. | **[DESCONOCIDO]** |

> El endpoint de anulación acepta un objeto `{ cause: string }` para registrar la causa. **[VISTO: F6, `VoidInvoice`]**
> El endpoint de apertura puede recibir un objeto `stamp` para emitir electrónicamente al reabrir. **[VISTO: F7, `OpenColombia`]**

### 3.4 Estados de otros recursos

| Recurso | Estados vistos | Evidencia |
|---|---|---|
| Pagos | `open` (natural) y `void` (anulado). | **[VISTO: F14, F15]** |
| Contactos | `active`, `inactive`. | **[VISTO: F9]** |
| Ítems | `active`, `inactive`. | **[VISTO: F10]** |
| Impuestos | `active`, `inactive`. | **[VISTO: F16, F17]** |

---

## 4. Cálculo de totales e impuestos

### 4.1 Fórmula que se desprende de los ejemplos

```text
subtotal        = Σ (price_i × quantity_i)
descuento_i     = (price_i × quantity_i) × (discount_i / 100)
base_i          = price_i × quantity_i − descuento_i
impuesto_i      = base_i × (percentage_tax / 100)
tax             = Σ impuesto_i
total           = subtotal − descuentos + tax
totalPaid       = Σ pagos aplicados
balance         = total − totalPaid
```

| Afirmación | Evidencia |
|---|---|
| El `price` de la línea **no incluye impuestos ni descuentos**. | **[VISTO: F2, descripción de `items`]** |
| `discount` es un **porcentaje**, no un monto. | **[VISTO: F2]** |
| El impuesto se calcula por línea, según los impuestos de esa línea. | **[VISTO: F2; F3, ejemplo por línea]** |
| `subtotal` es la suma de las bases antes de impuestos. | **[VISTO: F3, ejemplo CR: 966 = 850 + 116]** |
| `tax` es la suma de los impuestos. | **[VISTO: F3, ejemplo CR: 112,82 = 110,50 + 2,32]** |
| `total = subtotal + tax` cuando no hay descuento. | **[VISTO: F3, ejemplo CR: 1.078,82 = 966 + 112,82]** |
| `total = subtotal − descuento + tax` en general. | **[INFERIDO]**: el ejemplo CR tiene `discount: 0`; no hay ejemplo con descuento distinto de cero. |
| `balance = total − totalPaid`. | **[VISTO: F1, ejemplos: 609 − 0 = 609; 632 − 500 = 132]** |
| La moneda y la tasa se expresan con `currency.code` y `currency.exchangeRate`. | **[VISTO: F2]** |
| `decimalPrecision` indica la precisión decimal usada. | **[VISTO: F1, F3]** |

### 4.2 Ejemplo verificable (Costa Rica)

Del ejemplo `GetInvoiceCostaRica44Fields` **[VISTO: F3]**:

| Línea | Cálculo | Total de línea |
|---|---|---|
| Activo virtual: `price 850`, `quantity 1`, IVA 13 % | 850 + 110,50 | 960,50 |
| Agua mineral: `price 58`, `quantity 2`, IVA 2 % | 116 + 2,32 | 118,32 |
| **Subtotal** | 850 + 116 | **966,00** |
| **Impuesto** | 110,50 + 2,32 | **112,82** |
| **Total** | 966 + 112,82 | **1.078,82** |
| **Pagado** | — | **0,00** |
| **Saldo** | 1.078,82 − 0 | **1.078,82** |

### 4.3 Ejemplo verificable (factura genérica)

Del ejemplo de `GET /invoices/{id}` **[VISTO: F3]**:

| Línea | Cálculo | Total |
|---|---|---|
| Billetera: `price 80`, `quantity 5`, IVA 16 % | 400 + 64 | 464 |
| Cartera: `price 125`, `quantity 1`, IVA 16 % | 125 + 20 | 145 |
| **Total** | 464 + 145 | **609** |

La respuesta solo muestra `total: 609`, `totalPaid: 0`, `balance: 609`; no incluye `subtotal` ni `tax` en este ejemplo. **[VISTO: F3]**

### 4.4 Advertencias sobre los totales

| Tema | Situación | Evidencia |
|---|---|---|
| Retenciones | La factura y el pago exponen `retentions[]` con `amount`, pero **no se documenta** si reducen el `total`, el `balance` o solo se informan. En el ejemplo genérico, `total` y `balance` no las descuentan. | **[VISTO: F2, F3; efecto DESCONOCIDO]** |
| Descuentos | No hay ejemplo con descuento > 0; el orden exacto (antes/después de impuesto) es una inferencia. | **[INFERIDO]** |
| Redondeo | `decimalPrecision` existe, pero no se documenta la regla de redondeo (half-up, truncamiento, etc.). Hay un ejemplo donde 545 × 1,16 = 632,2 y la respuesta muestra `total: 632`. | **[VISTO: F1; regla DESCONOCIDA]** |
| Cargos adicionales | `totalsSummary.additionalCharges` aparece en el ejemplo CR, pero no se documenta cómo se calcula ni cuándo aplica. | **[VISTO: F3; fórmula DESCONOCIDA]** |
| Impuestos múltiples | Una línea puede tener varios impuestos; no se documenta si se suman, si se componen o si hay orden de aplicación. | **[VISTO: F2; composición DESCONOCIDA]** |
| Moneda | No se aclara si `total` está en la moneda de la factura o en la moneda base de la empresa cuando hay multimoneda. | **[DESCONOCIDO]** |
| Precio con impuesto incluido | La documentación dice explícitamente que `price` **no** incluye impuestos; no se documenta una opción de precio con impuesto incluido. | **[VISTO: F2]** |
| Totales por país | Solo el ejemplo de Costa Rica muestra `subtotal`, `tax` y `totalsSummary`; no se puede generalizar a todos los países. | **[VISTO: F3]** |

---

## 5. Endpoints principales por recurso

### 5.1 Aspectos generales

| Aspecto | Valor | Evidencia |
|---|---|---|
| URL base | `https://api.alegra.com/api/v1` | **[VISTO: F2, `servers`]** |
| Formato | JSON | **[VISTO: F30; F2, `application/json`]** |
| Autenticación | HTTP Basic: `base64(correo:token)` en `Authorization` | **[VISTO: F18]** |
| Límite | 150 peticiones por minuto por usuario; al excederlo, HTTP 429 | **[VISTO: F19]** |
| Cabeceras de límite | `X-Rate-Limit-Limit`, `X-Rate-Limit-Remaining`, `X-Rate-Limit-Reset` | **[VISTO: F19]** |
| Códigos de éxito | 200 (OK), 201 (creado) | **[VISTO: F20]** |
| Códigos de error | 400, 401, 402, 403, 404, 405, 500, 503 | **[VISTO: F20]** |
| Versión | `v1` en la ruta; no se documenta política de versionado/deprecación | **[VISTO: F2; política DESCONOCIDA]** |
| PATCH | La guía general menciona GET/POST/PUT/PATCH, pero no se encontró un endpoint PATCH en la referencia | **[VISTO: F30; ausencia en referencia]** |

### 5.2 Facturas

| Método | Ruta | Acción | Evidencia |
|---|---|---|---|
| `GET` | `/invoices` | Listar facturas (30 por defecto; máximo 30 por página). | **[VISTO: F1]** |
| `POST` | `/invoices` | Crear factura. | **[VISTO: F2]** |
| `GET` | `/invoices/{id}` | Consultar una factura. | **[VISTO: F3]** |
| `PUT` | `/invoices/{id}` | Editar solo los campos enviados; `null` borra un valor. | **[VISTO: F4]** |
| `DELETE` | `/invoices/{id}` | Eliminar una factura en `draft`. | **[VISTO: F5]** |
| `POST` | `/invoices/{id}/void` | Anular factura. | **[VISTO: F6]** |
| `POST` | `/invoices/{id}/open` | Revertir la anulación. | **[VISTO: F7]** |
| `POST` | `/invoices/{id}/email` | Enviar la factura por correo. | **[VISTO: página `post_invoices-id-email`]** |
| `POST` | `/invoices/{id}/attachment` | Adjuntar archivos. | **[VISTO: barra lateral `post_invoices-id-attachment`; path no abierto → INFERIDO]** |
| `POST` | `/invoices/preview` | Vista previa. | **[VISTO: barra lateral; path no abierto → INFERIDO]** |
| `POST` | `/invoices/stamp` | Emisión masiva. | **[VISTO: barra lateral; path no abierto → INFERIDO]** |
| `PUT` | `/invoices/{id}/retentionsApplied` | Editar retenciones aplicadas. | **[VISTO: barra lateral; path no abierto → INFERIDO]** |

> La página `post_invoices-id-email` se consultó y su esquema confirma `POST /invoices/{id}/email`. **[VISTO: página `post_invoices-id-email`]** Las rutas marcadas como INFERIDO provienen del slug de la barra lateral y no se abrieron; no se usan como base para el modelo de datos.

### 5.3 Contactos

| Método | Ruta | Acción | Evidencia |
|---|---|---|---|
| `GET` | `/contacts` | Listar contactos. | **[VISTO: F8]** |
| `POST` | `/contacts` | Crear contacto. | **[VISTO: F9]** |
| `GET` | `/contacts/{id}` | Consultar contacto. | **[VISTO: página `contactsdetails-1`]** |
| `PUT` | `/contacts/{id}` | Editar contacto. | **[VISTO: página `editcontact`]** |
| `DELETE` | `/contacts/{id}` | Eliminar contacto. | **[VISTO: página `deletecontact`]** |
| `POST` | `/contacts/{id}/restore` | Restaurar contacto. | **[VISTO: barra lateral; path no abierto → INFERIDO]** |
| `POST` | `/contacts/{id}/attachment` | Adjuntar archivo. | **[VISTO: barra lateral; path no abierto → INFERIDO]** |

### 5.4 Ítems

| Método | Ruta | Acción | Evidencia |
|---|---|---|---|
| `GET` | `/items` | Listar ítems. | **[VISTO: F10]** |
| `POST` | `/items` | Crear ítem. | **[VISTO: F11]** |
| `GET` | `/items/{id}` | Consultar ítem. | **[VISTO: página `get_items-id`]** |
| `PUT` | `/items/{id}` | Editar ítem. | **[VISTO: página `put_items-id`]** |
| `DELETE` | `/items/{id}` | Eliminar ítem. | **[VISTO: barra lateral `delete_items-id`; path no abierto → INFERIDO]** |

### 5.5 Pagos

| Método | Ruta | Acción | Evidencia |
|---|---|---|---|
| `GET` | `/payments` | Listar pagos. | **[VISTO: F12]** |
| `POST` | `/payments` | Crear pago. | **[VISTO: F13]** |
| `GET` | `/payments/{id}` | Consultar pago. | **[VISTO: página `get_payments-id-1`]** |
| `PUT` | `/payments/{id}` | Editar pago. | **[VISTO: página `put_payments-id-1`]** |
| `POST` | `/payments/{id}/void` | Anular pago. | **[VISTO: F14]** |
| `POST` | `/payments/{id}/open` | Convertir pago a abierto. | **[VISTO: F15]** |

### 5.6 Impuestos

| Método | Ruta | Acción | Evidencia |
|---|---|---|---|
| `GET` | `/taxes` | Listar impuestos. | **[VISTO: F16]** |
| `POST` | `/taxes` | Crear impuesto. | **[VISTO: F17]** |
| `GET` | `/taxes/{id}` | Consultar impuesto. | **[VISTO: página `get_taxes-id`]** |
| `PUT` | `/taxes/{id}` | Editar impuesto. | **[VISTO: página `put_taxes-id`]** |
| `DELETE` | `/taxes/{id}` | Eliminar impuesto. | **[VISTO: página `delete_taxes-id`]** |

### 5.7 Apoyo

| Método | Ruta | Acción | Evidencia |
|---|---|---|---|
| `GET`, `POST` | `/terms` | Listar / crear términos de pago. | **[VISTO: F27]** |
| `GET`, `POST` | `/currencies` | Listar / crear monedas. | **[VISTO: F28]** |
| `GET`, `POST` | `/retentions` | Listar / crear retenciones. | **[VISTO: F29]** |
| `GET` | `/number-templates` | Listar numeraciones. | **[VISTO: F26; path INFERIDO]** |

---

## 6. Preguntas abiertas

Todo lo siguiente quedó **sin confirmar** con la documentación pública:

1. **Significado exacto de `closed`.** ¿Es «totalmente pagada», «cerrada manualmente» o ambas? **[DESCONOCIDO]**
2. **`paid`.** ¿Existe un estado `paid` interno o de API? No aparece en el enum documentado. **[DESCONOCIDO]**
3. **Transición `open` → `closed`.** ¿Es automática al llegar `balance = 0`, o requiere una acción? **[DESCONOCIDO]**
4. **Retenciones.** ¿Se restan del `total`, del `balance` o solo se informan? Los ejemplos no las descuentan. **[DESCONOCIDO]**
5. **Descuentos.** ¿El descuento se aplica antes o después del impuesto? ¿Existe descuento global además del descuento por línea? **[DESCONOCIDO]**
6. **Redondeo.** ¿Qué regla se aplica con `decimalPrecision`? ¿Por línea o sobre el total? **[DESCONOCIDO]**
7. **Impuestos múltiples.** ¿Se suman, se componen o se aplican en orden? ¿Se permiten tasas negativas? **[DESCONOCIDO]**
8. **Moneda.** ¿`total` está en la moneda de la factura o en la moneda base? ¿Cómo se interpreta `exchangeRate` (multiplicar o dividir)? **[DESCONOCIDO]**
9. **`payments[].account` vs. `bankAccount`.** Al crear una factura con pago se usa `account`; en `/payments` se usa `bankAccount`. ¿Son alias o estructuras distintas? **[DESCONOCIDO; VISTO: F2 vs. F13]**
10. **Monto total de un pago.** No hay `amount` de nivel superior en el esquema; ¿la respuesta lo agrega? **[DESCONOCIDO]**
11. **Sobrepagos y anticipos.** ¿Qué pasa si `invoices[].amount` supera el saldo? ¿Cómo se aplican `appliedAdvances`? **[DESCONOCIDO]**
12. **Obligatoriedad real de impuestos.** `POST /taxes` no declara `required`; no se sabe si `name` y `percentage` son exigidos. **[DESCONOCIDO]**
13. **Catálogo de `type` de impuesto.** El esquema lo deja como string; no publica enum. **[DESCONOCIDO]**
14. **Campos obligatorios por país.** Las variantes de México, Colombia, Chile, etc. agregan requisitos fiscales que no se analizaron en detalle. **[DESCONOCIDO]**
15. **Idempotencia.** ¿`POST /invoices` acepta una clave de idempotencia? **[DESCONOCIDO]**
16. **Concurrencia.** ¿Hay control optimista (`ETag`, `version`)? **[DESCONOCIDO]**
17. **Webhooks.** ¿Qué eventos existen para cambios de estado de factura o pago? La referencia tiene un módulo de suscripciones, pero no se analizó. **[DESCONOCIDO]**
18. **Notas de crédito.** ¿Cómo afectan el `balance` y el estado de la factura? No se analizaron. **[DESCONOCIDO]**
19. **Anulación y contabilidad.** La anulación de pagos dice no afectar contabilidad; ¿aplica igual a facturas? **[DESCONOCIDO]**
20. **Zona horaria de `date`/`datetime`.** No se documenta. **[DESCONOCIDO]**
21. **Versionado.** ¿Cómo se depreca `v1`? ¿Hay changelog con fechas de retiro? **[DESCONOCIDO]**
22. **Límite por usuario.** ¿El límite de 150/min es por usuario, por empresa o por token? La doc dice «por usuario». **[VISTO: F19; alcance exacto DESCONOCIDO]**

---

## 7. Notas de honestidad

### 7.1 Porcentaje de evidencia

Estimación **cualitativa** del peso de cada tipo de afirmación en este documento (no es una medición automática):

| Tipo | Porcentaje aproximado | Dónde se concentra |
|---|---|---|
| **[VISTO]** | **~75 %** | Rutas, métodos, campos, tipos, obligatoriedad declarada, ejemplos numéricos, autenticación, límites y códigos HTTP. |
| **[INFERIDO]** | **~18 %** | Significado de estados (`draft`/`open`/`closed`/`void`), cardinalidad de relaciones, fórmula con descuentos, efecto de retenciones, rutas marcadas desde la barra lateral. |
| **[DESCONOCIDO]** | **~7 %** | Reglas de redondeo, moneda, impuestos compuestos, idempotencia, concurrencia, webhooks, notas de crédito y obligatoriedad efectiva de impuestos. |

> El porcentaje es una **estimación editorial** para dar transparencia, no un cálculo exacto. La parte más frágil es todo lo que depende de **comportamiento en ejecución**, que aquí no se observó.

### 7.2 Qué es sólido y qué no

**Sólido (VISTO):**

- Rutas y métodos de los recursos principales.
- Existencia y tipo de los campos del esquema OpenAPI.
- Campos marcados como `required` en los esquemas.
- Ejemplos numéricos de totales (`subtotal + tax = total`, `total − totalPaid = balance`).
- Autenticación Basic, límite de 150/min y códigos HTTP.
- Que la forma de la respuesta varía por país.

**Frágil (INFERIDO):**

- El significado de `closed` y el paso automático a ese estado.
- La fórmula exacta cuando hay descuentos.
- El efecto de las retenciones.
- Las rutas que solo se dedujeron del slug de la barra lateral.

**No confirmado (DESCONOCIDO):**

- Reglas de redondeo y moneda.
- Comportamiento real de la API (nunca se ejecutó).
- Idempotencia, concurrencia y webhooks.
- Catálogos fiscales por país.

### 7.3 Riesgos legales

1. **Términos y condiciones del API.** Alegra concede una licencia «limitada, revocable, no exclusiva y no sublicenciable» y prohíbe, entre otras cosas, usar el API para «reemplazar o replicar la experiencia de uso o la funcionalidad de Alegra», desarrollar productos que Alegra considere competencia o extraer información del código base. **[VISTO: F21]** Este documento es un análisis educativo de documentación pública, pero **cualquier implementación que compita con Alegra o replique su producto debe revisarse legalmente antes de publicarse**.
2. **Propiedad intelectual de la documentación.** Los textos, ejemplos y esquemas son material de Alegra. Se citan y parafrasean con fines de análisis; **no se copia el corpus completo ni se redistribuye como si fuera propio**. **[VISTO: F21; criterio de redacción]**
3. **Marcas.** «Alegra» es una marca de Soluciones Alegra S.A.S. FacturaLibre no está afiliado ni patrocinado por Alegra. **[VISTO: F21, definiciones]** Este documento no debe presentarse como documentación oficial.
4. **Datos personales.** No se accedió a datos de ninguna cuenta; no hay datos personales en este análisis. **[VISTO: proceso realizado]**
5. **Uso del API en producción.** Los términos condicionan el acceso a los planes que ofrezcan integración y permiten a Alegra monitorear el uso y bloquear accesos. **[VISTO: F21]** Cualquier integración real debe hacerlo un usuario autorizado con su propio token.

### 7.4 Riesgos técnicos

1. **Deriva de la documentación.** Las páginas tienen fecha de actualización y pueden cambiar; este análisis es una foto del 2026-10-21. **[VISTO: metadatos de las páginas]**
2. **Ejemplos inconsistentes.** Hay diferencias de tipo (`id` como string o number), `numberTemplate` como objeto o array, `decimalPrecision` como número o string, y un total que no coincide exactamente con el cálculo (632 vs. 632,2). **[VISTO: F1, F3]**
3. **Variantes por país.** Los esquemas tienen `oneOf` por país; asumir la variante genérica puede fallar en México, Colombia, Chile, Costa Rica, etc. **[VISTO: F2, F9]**
4. **Campos no uniformes en respuestas.** `subtotal`, `discount`, `tax` y `totalsSummary` no aparecen en todos los ejemplos. El cliente debe tolerar su ausencia. **[VISTO: F1 vs. F3]**
5. **Obligatoriedad no declarada.** Algunos campos se describen como obligatorios en el texto pero no están en `required` (por ejemplo, `inventory.unit`), y `POST /taxes` no declara ninguno. **[VISTO: F11, F17]**
6. **Reglas contables no explicadas.** Retenciones, descuentos, redondeo y moneda pueden cambiar el total y no están formalizados. **[DESCONOCIDO]**
7. **Sin pruebas de ejecución.** No se observó el comportamiento real: no se sabe si la API valida, normaliza o rechaza los valores de los ejemplos. **[VISTO: proceso realizado]**
8. **Límite de peticiones.** 150/min puede ser insuficiente para sincronizaciones masivas; además, el alcance exacto del límite no está claro. **[VISTO: F19; alcance DESCONOCIDO]**

### 7.5 Recomendaciones antes de implementar

1. Tratar este documento como **mapa**, no como contrato: validar cada campo contra una cuenta de prueba autorizada. **[INFERIDO]**
2. Implementar el modelo con **campos opcionales y variantes por país**, no con una sola forma rígida. **[INFERIDO]**
3. Escribir pruebas de contrato con los ejemplos de la documentación y con casos de descuento, retención y redondeo. **[INFERIDO]**
4. No asumir que `closed` llega automáticamente: calcular el saldo con `total − totalPaid` y decidir la lógica de negocio en la aplicación. **[INFERIDO]**
5. Revisar los términos de Alegra con asesoría legal si FacturaLibre va a comercializarse o a competir con Alegra. **[VISTO: F21]**

---

### Cierre

Este análisis se hizo **solo con documentación pública**, sin credenciales, sin tokens y sin tocar la API real. Todo lo que no se pudo confirmar quedó marcado como **[DESCONOCIDO]** en lugar de rellenarse con suposiciones. La parte más fiable es la **estructura de recursos, rutas y campos**; la menos fiable es el **comportamiento dinámico** (estados, totales con retenciones, redondeo y moneda).
