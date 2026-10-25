# Auditoría de brechas — Nexus ERP frente a Alegra y Siigo

> **Proyecto:** Nexus ERP (repositorio FacturaLibre)
> **Objeto:** módulos actuales de Nexus, páginas públicas y documentación de API de Alegra y Siigo
> **Fecha de observación:** 2026-10-24
> **Mercado de referencia:** Colombia, COP, pyme y mediana empresa
> **Naturaleza:** análisis documental y de código. No se accedió a cuentas privadas, no se ejecutaron transacciones reales y no se validaron reglas fiscales con la DIAN.
> **Regla de evidencia:** una capacidad no se declara “inexistente” en un competidor si solo no se encontró. En ese caso se marca **[DESCONOCIDO]**.

### Contenido

1. [Resumen ejecutivo](#0-resumen-ejecutivo)
2. [Alcance, método y evidencia](#1-alcance-método-y-evidencia)
3. [Estado actual de Nexus ERP](#2-estado-actual-de-nexus-erp)
4. [Benchmark: Alegra y Siigo](#3-benchmark-alegra-y-siigo)
5. [Inventario de brechas](#4-inventario-de-brechas)
6. [Matriz de priorización](#5-matriz-de-priorización)
7. [Mapeo REA](#6-mapeo-rea)
8. [Roadmap propuesto](#7-roadmap-propuesto)
9. [Decisiones de diseño y no negociables](#8-decisiones-de-diseño-y-no-negociables)
10. [Riesgos y supuestos](#9-riesgos-y-supuestos)
11. [Anexos](#10-anexos)
12. [Cierre](#11-cierre)

---

## 0. Resumen ejecutivo

Nexus ERP ya tiene una base transaccional creíble: ventas, compras, gastos, tesorería, inventario, nómina básica, contabilidad automática, reportes financieros, usuarios y RBAC. No es un prototipo vacío. Sin embargo, **no está listo para operar como ERP de producción en Colombia**, y la brecha más grande no es de “features” frente a Alegra o Siigo: es de **cumplimiento fiscal y verdad financiera**.

Los cinco hallazgos que cambian la conclusión del análisis son:

1. **Nexus no emite facturación electrónica DIAN.** Existe factura interna con numeración `FV`, pero no hay XML, CUFE/CUDE, firma, transmisión, resolución, documento soporte ni buzón DIAN. La propia arquitectura lo ubica fuera del MVP. **[VISTO: N8, N9, N11]**
2. **La venta no genera costo de ventas ni descarga contable del inventario.** El asiento de facturación debita cuentas por cobrar y acredita ingresos e IVA; no debita costo de ventas ni acredita inventario. El inventario se mueve en unidades, pero no se valoriza al vender. **[VISTO: N9]**
3. **El POS cobra en pantalla, pero no registra el pago ni el movimiento de caja.** Crea y emite la factura, mas no llama a `createPayment`, no crea una sesión de caja y no hace arqueo. La factura queda con saldo pendiente aunque el cliente haya pagado. **[VISTO: N7]**
4. **La conciliación bancaria es manual y está desconectada de pagos y facturas.** Solo marca o desmarca como “revisado” un movimiento bancario creado a mano. No importa extractos, no hace matching, no maneja diferencias y no vincula el pago con el banco. **[VISTO: N5]**
5. **Faltan los controles que un negocio colombiano usa todos los días:** edades de cartera, flujo de caja, presupuestos, activos fijos/depreciación, órdenes de compra, cierres de caja POS, centros de costo, retenciones y cierre de periodos. **[VISTO: N3, N4, N5, N6, N7, N9, N10]**

La lectura competitiva es consistente con lo anterior:

- **Alegra** es más fuerte en automatización, ecosistema fiscal, conciliación bancaria automática, POS con turnos, órdenes de compra, activos fijos vía API/MCP y amplitud de API. **[VISTO: A1–A7]**
- **Siigo** es más fuerte en contabilidad, nómina electrónica/PILA, cartera por edades, cobranza, centros de costo, inventario valorizado y documentos soporte. **[VISTO: S1–S10]**
- **Nexus** tiene una arquitectura más limpia y transparente que muchos competidores, pero una cobertura funcional mucho más estrecha. Su ventaja no es “tener más módulos”: es poder construir un núcleo correcto, open source y auditable. **[INFERIDO]**

La secuencia recomendada no es copiar el menú de Alegra o Siigo. Es:

1. **Verdad financiera y base fiscal:** COGS, valorización de inventario, catálogo de impuestos con códigos DIAN, datos maestros fiscales, cierre de periodos y libros.
2. **Cumplimiento DIAN:** factura electrónica, nota crédito, documento soporte, buzón, retenciones y exógena.
3. **Liquidez y caja:** POS con pago y sesión de caja, conciliación bancaria automática, flujo de caja y edades de cartera.
4. **Control corporativo:** órdenes de compra, presupuestos, centros de costo, activos fijos, conteo físico y transferencias.
5. **Plataforma:** API pública, webhooks, multiempresa, offline, IA/MCP y multimoneda.

> **Conclusión ejecutiva:** Nexus puede competir, pero primero debe dejar de ser un “facturador con contabilidad” y convertirse en un ERP con eventos económicos completos, cumplimiento fiscal y control de caja. La paridad de menú con Alegra o Siigo es un objetivo posterior.

---

## 1. Alcance, método y evidencia

### 1.1 Qué se revisó

- El código local de Nexus: routers, modelos, servicios, migraciones, pantallas y pruebas. **[VISTO: N1–N12]**
- Las páginas públicas de Alegra Colombia y su centro de ayuda, además de su documentación de API y MCP. **[VISTO: A1–A7]**
- Las páginas públicas de Siigo Nube y su documentación de API. **[VISTO: S1–S10]**
- La documentación de arquitectura y decisiones del propio proyecto. **[VISTO: N11]**

### 1.2 Qué no se hizo

- No se inició sesión en Alegra ni en Siigo.
- No se probaron flujos reales, permisos, límites de plan, concurrencia, latencia ni precios.
- No se revisó el frontend privado, la base de datos ni el tráfico de red de los competidores.
- No se validaron reglas fiscales colombianas con contador, abogado o experto DIAN.
- No se estudiaron todos los módulos de Alegra y Siigo; se priorizaron los relacionados con el objeto de este informe.
- No se afirma que una capacidad no exista en un competidor si solo no aparece en las fuentes revisadas. **[DESCONOCIDO]** no es lo mismo que “no tiene”.

### 1.3 Leyenda de evidencia

| Marca | Significado |
|---|---|
| **[VISTO]** | Aparece en el código local, en una página pública, en una captura o en la documentación de API consultada. |
| **[INFERIDO]** | Se deduce de la evidencia, pero la fuente no lo afirma de forma literal. |
| **[DESCONOCIDO]** | No se pudo confirmar con las fuentes revisadas. No se inventa la regla ni el comportamiento. |

Cuando una tabla mezcla niveles, la columna **Evidencia** lo indica fila por fila.

### 1.4 Fuentes principales

#### Nexus ERP

| ID | Fuente | Uso |
|---|---|---|
| N1 | `README.md` | Estado declarado del proyecto y advertencia de software educativo |
| N2 | `frontend/src/components/layout/Sidebar.tsx` | Navegación real de la aplicación |
| N3 | `backend/app/main.py` | Routers registrados y alcance del backend |
| N4 | `backend/app/api/v1/reports.py`, `backend/app/domain/dashboard_repository.py` | Reportes, CSV y métricas del dashboard |
| N5 | `backend/app/api/v1/treasury.py`, `backend/app/domain/models/bank.py` | Cuentas, movimientos y conciliación manual |
| N6 | `backend/app/api/v1/purchases.py`, `backend/app/domain/models/purchase.py` | Facturas de compra y pagos a proveedores |
| N7 | `backend/app/api/v1/pos.py`, `frontend/src/components/pos/PosClient.tsx` | Alcance real del POS |
| N8 | `backend/app/domain/models/invoice.py`, `payment.py`, `credit_note.py`, `tax.py`, `company_setting.py` | Documentos, impuestos y datos maestros |
| N9 | `backend/app/application/accounting/service.py`, `mapping.py` | Asientos automáticos y alcance contable |
| N10 | `backend/app/application/payroll/service.py`, `backend/app/domain/models/payroll.py` | Nómina básica |
| N11 | `specs/ARQUITECTURA.md`, `specs/DECISIONES.md`, `specs/ESPECIFICACION-FUNCIONAL.md` | Decisiones y límites del MVP |
| N12 | `backend/app/application/inventory/service.py`, `backend/app/domain/models/stock.py`, `item.py` | Inventario, movimientos y datos maestros |

#### Alegra

| ID | Fuente | Uso |
|---|---|---|
| A1 | https://www.alegra.com/colombia/contabilidad/ | Conciliación bancaria automática, flujo de efectivo, cartera, reportes |
| A2 | https://www.alegra.com/colombia/punto-de-venta/ | POS, turnos, apertura/cierre de caja y reportes |
| A3 | https://www.alegra.com/colombia/facturacion/ | Facturación electrónica, documentos y ecosistema fiscal |
| A4 | https://www.alegra.com/colombia/inventarios/ | Inventario permanente, bodegas, ajustes y valorización |
| A5 | https://www.alegra.com/colombia/nomina/ | Nómina electrónica y prestaciones |
| A6 | https://developer.alegra.com/llms.txt | Índice de API/MCP: órdenes de compra, conciliaciones, centros de costo, activos fijos, flujo de caja, cartera y reportes |
| A7 | https://developer.alegra.com/reference/accounting_getfixedasset.md | Evidencia específica de activos fijos vía MCP |

#### Siigo

| ID | Fuente | Uso |
|---|---|---|
| S1 | https://www.siigo.com/nube/ | Siigo Nube, cartera por edades, POS, nómina, contabilidad, inventario |
| S2 | https://www.siigo.com/software-contable/ | Contabilidad, conciliación bancaria, reportes y documentos |
| S3 | https://www.siigo.com/software-de-cobranza/ | Cartera, cobranza, recordatorios y Siigo Pay |
| S4 | https://www.siigo.com/software-de-compras/ | Compras, cuentas por pagar y saldos vencidos |
| S5 | https://www.siigo.com/punto-de-venta/ | POS, apertura/cierre de caja, turnos y cuadres |
| S6 | https://www.siigo.com/software-de-costos/ | Centros de costo y presupuesto por sucursal |
| S7 | https://www.siigo.com/software-de-inventario/ | Kardex, valorización, costo promedio, conteo y transferencias |
| S8 | https://www.siigo.com/software-de-nomina/ | Nómina electrónica, PILA, prestaciones y archivos bancarios |
| S9 | https://siigoapi.docs.apiary.io/ | API: autenticación, documentos, reportes, catálogos y webhooks |
| S10 | https://www.siigo.com/ia/ | Casos de uso de IA, incluido cierre contable y fiscal |

> Las URLs y el contenido observado corresponden al 2026-10-24. Los competidores pueden cambiar nombres, planes o alcance sin previo aviso.

---

## 2. Estado actual de Nexus ERP

### 2.1 Arquitectura y principios

Nexus es un **monolito modular API-first** con FastAPI, PostgreSQL y Next.js. La separación por routers, servicios, repositorios y modelos es clara, y las operaciones críticas usan transacciones, bloqueo optimista e idempotencia. **[VISTO: N3, N11]**

| Principio | Implementación observada | Evidencia |
|---|---|---|
| Dinero exacto | `Decimal` en Python y `NUMERIC` en PostgreSQL | **[VISTO: N8, N11]** |
| Operaciones atómicas | `operation_transaction` en emisión, pagos, compras y tesorería | **[VISTO: N3, N5, N6, N9]** |
| Idempotencia | `Idempotency-Key` en comandos críticos | **[VISTO: N3, N11]** |
| Concurrencia | Bloqueo optimista con `version` | **[VISTO: N8, N11]** |
| Contabilidad automática | Asientos de factura, pago, compra, gasto, nómina y tesorería | **[VISTO: N9]** |
| RBAC | Roles `ADMIN`, `ACCOUNTANT`, `CASHIER` | **[VISTO: N3, N8]** |
| Movimientos inmutables | Stock y banco se corrigen con movimientos compensatorios | **[VISTO: N5, N12]** |
| Frontera fiscal | Reglas DIAN, retenciones y firma requieren validación humana | **[VISTO: N11]** |

La arquitectura es una buena base. El problema no es la calidad estructural del código, sino **la cobertura del dominio y la profundidad de los eventos económicos**.

### 2.2 Mapa de módulos actuales

| Módulo | Qué existe hoy | Evidencia | Madurez |
|---|---|---|---|
| Autenticación y usuarios | Registro bootstrap, login, sesiones revocables, cookie `HttpOnly`, roles | **[VISTO: N3, N8]** | Operativa |
| Contactos y CRM básico | Clientes, proveedores o ambos; estados `LEAD`, `PROSPECT`, `CUSTOMER`; `tax_id` simple | **[VISTO: N8]** | Básica |
| Ítems e impuestos | Nombre, descripción, precio, impuesto, precio con impuesto incluido; impuesto solo nombre y tarifa | **[VISTO: N8, N12]** | Básica |
| Bodegas e inventario | Multi-bodega, libro de movimientos, saldos por ítem/bodega, tipos `IN`, `OUT`, `TRANSFER_IN`, `TRANSFER_OUT`, `ADJUSTMENT` | **[VISTO: N12]** | Parcial |
| Ventas | Facturas `draft`/`issued`/`void`, líneas, descuentos, vencimiento, pagos, notas crédito, conversión de cotización, salida de stock y asiento | **[VISTO: N8, N9]** | Operativa |
| Cotizaciones | Cotizaciones con estados y conversión a factura | **[VISTO: N8]** | Básica |
| Compras | Facturas de proveedor `draft`/`issued`/`void`, líneas, pagos a proveedores, entrada de stock y asiento | **[VISTO: N6, N9]** | Operativa, sin órdenes de compra |
| Gastos | Gastos operativos con asiento contable | **[VISTO: N3, N9]** | Básica |
| Tesorería | Cuentas bancarias COP, depósitos, retiros, transferencias, conciliación manual, resumen y asientos | **[VISTO: N5, N9]** | Manual |
| POS | Búsqueda de ítems, carrito, creación y emisión de factura | **[VISTO: N7]** | Incompleto |
| Nómina | Empleados, periodo mensual, salud 4 %, pensión 4 %, neto y asiento | **[VISTO: N10]** | Muy básica |
| Contabilidad | PUC, asientos automáticos, consulta de cuentas y asientos | **[VISTO: N9]** | Parcial, solo lectura de asientos |
| Reportes | Estado de resultados, balance general, `invoices.csv`, `payments.csv` | **[VISTO: N4]** | Mínimo |
| Dashboard | Facturación, pagos, cartera pendiente, estados y ventas de seis meses | **[VISTO: N4]** | Básico |
| Configuración | Nombre, NIT, dirección, teléfono, email y logo | **[VISTO: N8]** | Insuficiente para DIAN |
| Administración | Usuarios, roles, bodegas, impuestos y configuración | **[VISTO: N2, N3]** | Básica |

> **Nota de evidencia:** el `README.md` está desactualizado: declara “Fase 10” y “sin notas crédito”, pero el código actual incluye notas crédito, compras, gastos, tesorería y nómina. Para este informe se usó el código y las migraciones como fuente de verdad, no el estado declarado en el README. **[VISTO: N1 vs. N3, N6, N9, N10]**

### 2.3 Lo que ya es sólido

- **Integridad transaccional:** la emisión de factura, el pago, la compra y el movimiento de inventario se ejecutan dentro de una transacción; si falla la contabilidad, se revierte la operación. **[VISTO: N9, N11]**
- **Trazabilidad de movimientos:** stock y banco son libros de movimientos inmutables, no saldos editables a mano. **[VISTO: N5, N12]**
- **Contabilidad de partida doble:** los documentos principales generan asientos automáticos. **[VISTO: N9]**
- **Separación de estados:** ciclo de vida (`draft`/`issued`/`void`) y estado de pago (`unpaid`/`partially_paid`/`paid`/`overpaid`) están separados. **[VISTO: N8]**
- **Base modular:** los routers y servicios permiten agregar dominios sin reescribir el núcleo. **[INFERIDO: N3, N11]**
- **Enfoque educativo y open source:** facilita auditar decisiones y construir sobre el proyecto. **[VISTO: N1]**

### 2.4 Hallazgos de integridad que condicionan todo lo demás

Estos hallazgos no son “funciones faltantes” menores. Si no se corrigen, cualquier reporte o módulo nuevo hereda datos incorrectos.

#### 2.4.1 La venta no reconoce costo de ventas

El asiento de emisión de factura debita cuentas por cobrar y acredita ingresos e IVA. La compra debita inventario, pero la venta **no** debita costo de ventas ni acredita inventario. **[VISTO: N9]**

Consecuencias:

- El estado de resultados muestra un margen bruto inflado.
- El balance general mantiene inventario que ya se vendió.
- El inventario en unidades y el inventario contable se separan.
- El flujo de caja y la utilidad no son confiables para tomar decisiones.

Esto es **Alta** prioridad, incluso antes de agregar reportes nuevos.

#### 2.4.2 El POS no registra el pago ni la caja

`PosClient` crea y emite la factura, pero no llama a `createPayment`, no crea un movimiento de tesorería y no abre una sesión de caja. El efectivo recibido y el cambio se calculan solo en la interfaz. **[VISTO: N7]**

Consecuencias:

- La factura queda `unpaid` o `partially_paid` aunque el cliente pagó.
- No hay arqueo, no hay diferencia de caja y no hay responsable del turno.
- El asiento contable no debita caja: debita cuentas por cobrar.
- El dashboard y la cartera muestran una deuda que no existe.

Esto es **Alta** prioridad para cualquier negocio con POS.

#### 2.4.3 La conciliación bancaria no concilia nada automáticamente

`BankTransaction` tiene un booleano `is_reconciled` y una fecha `reconciled_at`. La operación de conciliar solo cambia ese booleano; no compara con un extracto, no cruza con pagos, no sugiere coincidencias y no registra diferencias. **[VISTO: N5]**

Consecuencias:

- El usuario debe crear el movimiento bancario a mano y luego marcarlo como revisado.
- No se puede saber si el banco ya registró un pago que el sistema aún no tiene.
- No hay conciliación por periodo ni reporte de partidas conciliatorias.
- La “conciliación” es un checklist, no un control.

Esto es **Alta** prioridad.

#### 2.4.4 El catálogo fiscal es insuficiente

`Tax` solo guarda `name` y `rate`. No distingue IVA, INC, ICA, retención en la fuente, reteIVA o reteICA; no tiene código DIAN ni tipo de impuesto. **[VISTO: N8]**

Consecuencias:

- No se puede construir una factura electrónica válida.
- No se pueden calcular retenciones ni reportes fiscales.
- No se puede separar IVA generado, IVA descontable y retenciones.
- El asiento contable usa una sola cuenta de IVA por total, sin detalle fiscal.

Esto es **Alta** prioridad y bloquea la facturación electrónica.

#### 2.4.5 Los datos maestros fiscales son mínimos

`CompanySetting` solo tiene nombre, NIT, dirección, teléfono, email y logo. `Contact` solo tiene nombre, email, tipo, estado y `tax_id`. **[VISTO: N8]**

Faltan, entre otros:

- Tipo de identificación y dígito de verificación.
- Régimen y responsabilidades fiscales.
- Tipo de persona y actividad económica.
- Municipio, departamento y país.
- Resolución de facturación, prefijo, rango y vigencia.
- Datos de la DIAN, correo de notificación y responsabilidades.

Sin esto no se puede emitir una factura electrónica colombiana.

#### 2.4.6 No hay facturación electrónica DIAN

No se observó XML, CUFE/CUDE, firma electrónica, transmisión, resolución, documento soporte, buzón DIAN ni eventos RADIAN. La documentación del proyecto ubica la facturación electrónica y la nota crédito electrónica en fases posteriores, no en el MVP. **[VISTO: N11]**

Esto no es una brecha de “paridad competitiva”. Es una **brecha de cumplimiento legal** para una empresa colombiana que facture.

#### 2.4.7 El dashboard llama “ingresos” a la suma de pagos

`DashboardRepository` calcula `total_revenue` como `SUM(Payment.amount)`, sin filtro de fecha. No es ingreso devengado ni flujo de caja; es el total histórico de pagos registrados. **[VISTO: N4]**

Consecuencias:

- El KPI puede crecer por un pago antiguo registrado hoy.
- No coincide con el estado de resultados.
- No sirve para medir flujo de caja del periodo.

#### 2.4.8 El POS usa números de JavaScript para dinero

`PosClient` usa `Number`, `Math.round` y aritmética de punto flotante para totales y cambio, mientras el backend usa `Decimal`. **[VISTO: N7]**

No es el riesgo más grave, pero en un POS con arqueo y diferencias de caja puede producir centavos inconsistentes. La regla de dinero exacto debe aplicarse también a la capa de presentación que calcula totales y cambio.

---

## 3. Benchmark: Alegra y Siigo

### 3.1 Alegra

Alegra se posiciona como una plataforma de contabilidad, facturación, inventario, POS, nómina y automatización para pymes. Su mayor diferenciador observado es la **automatización del ciclo financiero** y la amplitud de su ecosistema de API/MCP. **[VISTO: A1–A7]**

| Dominio | Capacidad observada | Evidencia |
|---|---|---|
| Facturación | Facturación electrónica, notas crédito/débito, remisiones, facturas recurrentes, numeración y documentos | **[VISTO: A3, A6]** |
| Buzón DIAN | Recepción y causación de facturas electrónicas de proveedores | **[VISTO: A1, A6]** |
| Documento soporte | Gestión de documentos soporte y retenciones | **[VISTO: A6]** |
| Cartera | Cuentas por cobrar, facturas vencidas, recordatorios y análisis de flujo de efectivo | **[VISTO: A1, A6]** |
| Tesorería | Conciliación bancaria automática con IA, importación de extracto, ajuste de diferencias y tasa de cambio | **[VISTO: A1]** |
| Flujo de caja | Reporte de flujo de efectivo y análisis de flujo de caja | **[VISTO: A1, A6]** |
| POS | Apertura/cierre de turnos, cierres de caja, terminales y reportes | **[VISTO: A2]** |
| Compras | Órdenes de compra, facturas de compra, pagos y notas débito | **[VISTO: A6]** |
| Contabilidad | Centros de costo, asientos, cierres, activos fijos y depreciaciones | **[VISTO: A6, A7]** |
| Inventario | Inventario permanente, bodegas, ajustes, transferencias, listas de precios y variantes | **[VISTO: A4, A6]** |
| Nómina | Nómina electrónica y prestaciones | **[VISTO: A5]** |
| API/MCP | Endpoints de lectura/escritura, herramientas MCP y webhooks | **[VISTO: A6]** |

Lo que **no** se pudo confirmar en las fuentes revisadas:

- Un módulo de presupuestos independiente. **[DESCONOCIDO]**
- La interfaz de usuario completa de activos fijos; solo se vio la API/MCP. **[VISTO: A6, A7; DESCONOCIDO: UI]**
- La existencia de edades de cartera con rangos configurables; la página pública habla de facturas vencidas y cuentas por cobrar. **[VISTO: A1; DESCONOCIDO: buckets exactos]**

### 3.2 Siigo

Siigo se posiciona como un sistema contable y administrativo con fuerte énfasis en cumplimiento, nómina, cartera, inventario y centros de costo. Su mayor diferenciador observado es la **profundidad contable y fiscal**. **[VISTO: S1–S10]**

| Dominio | Capacidad observada | Evidencia |
|---|---|---|
| Facturación | Facturación electrónica, notas crédito/débito, recibos de caja y comprobantes de pago | **[VISTO: S2, S9]** |
| Documento soporte | Documentos soporte y compras | **[VISTO: S4, S9]** |
| Cartera | Cartera pendiente por edades o rangos de fechas, responsable, recordatorios y Siigo Pay | **[VISTO: S1, S3]** |
| Tesorería | Conciliación de cuentas bancarias; detalle de automatización no verificado | **[VISTO: S2; DESCONOCIDO: matching/importación]** |
| Flujo de caja | Se menciona mejorar el flujo de caja desde cobranza; no se vio un reporte autónomo | **[VISTO: S3; DESCONOCIDO: reporte]** |
| POS | Apertura/cierre de caja, turnos, movimientos y cuadres de caja | **[VISTO: S5]** |
| Compras | Compras, cuentas por pagar, saldos vencidos y días de mora | **[VISTO: S4]** |
| Centros de costo | Clasificación por centros de costo y presupuesto por sucursal | **[VISTO: S6]** |
| Inventario | Kardex, valorización, costo promedio, conteo físico y transferencias | **[VISTO: S7]** |
| Nómina | Nómina electrónica, PILA, prestaciones, retención y archivos bancarios | **[VISTO: S8]** |
| Contabilidad | Documentos contables, estados financieros y reportes; cierre contable/fiscal mencionado como caso de uso de IA, no verificado como flujo | **[VISTO: S2, S10; DESCONOCIDO: flujo de cierre]** |
| API | Autenticación, productos, clientes, facturas, cotizaciones, notas, compras, documentos soporte, recibos, comprobantes, reportes, catálogos, webhooks y SDK | **[VISTO: S9]** |

Lo que **no** se pudo confirmar en las fuentes revisadas:

- Un módulo de órdenes de compra. **[DESCONOCIDO]**
- Un módulo de activos fijos y depreciación. **[DESCONOCIDO]**
- Un módulo de presupuestos independiente; solo se vio “presupuesto por sucursal” dentro de centros de costo. **[VISTO: S6; DESCONOCIDO: módulo]**
- Conciliación bancaria automática vía API. **[DESCONOCIDO]**
- Un reporte de flujo de caja autónomo. **[DESCONOCIDO]**
- Edades de cartera vía API. **[DESCONOCIDO]**

### 3.3 Comparación directa

Leyenda de la columna de competidores: **Sí** = capacidad observada explícitamente; **Parcial** = capacidad limitada o adyacente; **No visto** = no se encontró en las fuentes revisadas, no prueba de ausencia; **No** = Nexus no lo tiene según código o documentación.

| Capacidad | Nexus | Alegra | Siigo | Lectura para Nexus |
|---|---|---|---|---|
| Factura electrónica DIAN | **No** | Sí | Sí | Brecha legal crítica |
| Nota crédito | Interna, no DIAN | Sí | Sí | Falta versión electrónica |
| Nota débito | **No** | Sí | Sí | Brecha media |
| Documento soporte | **No** | Sí | Sí | Brecha crítica |
| Buzón DIAN | **No** | Sí | Sí | Brecha crítica |
| Retenciones / exógena | **No** | Sí / Parcial | Parcial | Brecha crítica |
| Nómina electrónica / PILA | **No** | Sí | Sí | Brecha crítica si hay nómina |
| Conciliación bancaria automática | **No** (manual) | Sí | Parcial / No visto | Brecha alta |
| Flujo de caja | **No** | Sí | No visto | Brecha alta |
| Edades de cartera | **No** | Parcial | Sí | Brecha alta |
| Cobranza y recordatorios | **No** | Sí | Sí | Brecha alta |
| POS con pago y sesión de caja | **No** | Sí | Sí | Brecha alta |
| Cierres y arqueo de caja | **No** | Sí | Sí | Brecha alta |
| Órdenes de compra | **No** | Sí | No visto | Brecha media |
| Presupuestos | **No** | No visto | Parcial | Brecha media |
| Activos fijos / depreciación | **No** | Sí (API/MCP) | No visto | Brecha alta/condicionada |
| Centros de costo | **No** | Sí | Sí | Brecha media |
| Inventario valorizado / COGS | **No** | Sí | Sí | Brecha crítica |
| Conteo físico / transferencias | Parcial | Sí | Sí | Brecha media |
| Multimoneda | **No** (COP) | Sí | No visto | Brecha baja/media |
| Multiempresa | **No** | Probable **[INFERIDO]** | Probable **[INFERIDO]** | Brecha baja/media |
| API pública / webhooks | **No** (API interna) | Sí | Sí | Brecha media |
| IA / MCP | **No** | Sí | Sí | Brecha baja |
| Offline POS | **No** | Sí | No visto | Brecha baja |

### 3.4 Lectura competitiva

- **Alegra** compite por automatización y experiencia: conciliación con IA, buzón DIAN, flujo de caja, POS con turnos y una API/MCP amplia. Es el competidor más cercano a la “operación sin fricción”. **[VISTO: A1–A7]**
- **Siigo** compite por profundidad contable y fiscal: nómina electrónica, PILA, cartera por edades, centros de costo, inventario valorizado y documentos soporte. Es el competidor más cercano al “back office robusto”. **[VISTO: S1–S10]**
- **Nexus** no debe intentar ganar por cantidad de módulos en el corto plazo. Su oportunidad es un núcleo correcto, transparente, open source y auditable, con una experiencia más simple que la de los incumbentes. **[INFERIDO]**
- La paridad de menú es engañosa: tener una pantalla de “Presupuestos” no sirve si el asiento, el costo y la cartera no son confiables. Primero se corrige el núcleo; después se amplía la superficie. **[INFERIDO]**

---

## 4. Inventario de brechas

El orden de esta sección es por impacto económico y de cumplimiento, no por orden alfabético ni por menú de competidor. Cada brecha incluye estado actual, referencia de mercado, prioridad y un entregable mínimo.

### 4.1 Flujo de caja

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | No existe estado de flujo de caja. Hay estado de resultados, balance general, resumen de tesorería y un KPI de cartera. `total_revenue` suma pagos, no flujo de caja del periodo. **[VISTO: N4, N5]** |
| **Alegra** | Reporte de flujo de efectivo y análisis de flujo de caja; la landing lo presenta como “de la venta a tu flujo de efectivo”. **[VISTO: A1]** |
| **Siigo** | La cobranza se vende como mejora del flujo de caja; no se observó un reporte autónomo de flujo de caja. **[VISTO: S3; DESCONOCIDO: reporte]** |
| **Brecha** | Falta un estado de flujo de caja directo e indirecto, con apertura, entradas, salidas, cierre y categorías; falta proyección de caja basada en cartera y cuentas por pagar. |
| **Prioridad** | **Alta** |
| **Entregable mínimo** | Reporte por periodo con saldo inicial, entradas, salidas, saldo final y conciliación contra cuentas bancarias; exportación CSV. Después, proyección a 13 semanas con vencimientos de CxC y CxP. |

**Por qué es Alta:** sin flujo de caja, el dueño no sabe si puede pagar nómina, IVA o proveedores. Es la pregunta financiera más frecuente de una pyme colombiana.

### 4.2 Conciliación bancaria

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | Cuentas bancarias COP, movimientos manuales de depósito/retiro/transferencia y un booleano de conciliación. No hay extracto, importación, matching, reglas, diferencias ni vínculo con pagos o facturas. **[VISTO: N5]** |
| **Alegra** | Conciliación bancaria automática con IA, importación de extracto, cruce con contabilidad, ajuste de diferencias y tasa de cambio. **[VISTO: A1]** |
| **Siigo** | Menciona conciliación de cuentas bancarias; no se verificó el detalle de importación o matching. **[VISTO: S2; DESCONOCIDO: detalle]** |
| **Brecha** | Falta modelo de línea de extracto, importación CSV/OFX, motor de coincidencias, sugerencias, reglas, sesión de conciliación, partidas conciliatorias, diferencia en cambio y vínculo con `Payment`/`PurchasePayment`. |
| **Prioridad** | **Alta** |
| **Entregable mínimo** | Importar CSV, crear líneas de extracto, sugerir coincidencias por monto/fecha/referencia, confirmar manualmente, registrar diferencia y emitir reporte de conciliación. Sin IA en la primera versión. |

**Por qué es Alta:** la conciliación manual no escala y no detecta fraudes, duplicados ni pagos no registrados. Es un control de liquidez y de integridad.

### 4.3 Presupuestos

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | No existe modelo, pantalla ni reporte de presupuesto. **[VISTO: N3, N4]** |
| **Alegra** | No se encontró un módulo de presupuestos independiente en las fuentes revisadas. **[DESCONOCIDO]** |
| **Siigo** | Menciona “controla el presupuesto de cada sucursal” dentro de centros de costo. **[VISTO: S6]** |
| **Brecha** | Falta presupuesto por cuenta, centro de costo, mes y versión; comparación presupuesto vs. real; compromisos; aprobación; variaciones. |
| **Prioridad** | **Media** (Alta si se implementan centros de costo y la empresa es mediana) |
| **Entregable mínimo** | Presupuesto anual/mensual por cuenta y centro de costo, reporte de ejecución y variación, exportación CSV. Sin workflow de aprobación en la primera versión. |

**Por qué es Media:** es un control corporativo valioso, pero no bloquea la operación ni el cumplimiento. Depende de que existan centros de costo y contabilidad confiable.

### 4.4 Activos fijos y depreciación

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | No hay maestro de activos, depreciación, baja ni reporte. Tampoco hay diario manual para registrar una depreciación por fuera del sistema. **[VISTO: N3, N9]** |
| **Alegra** | La API/MCP expone activos fijos, consulta de activo y depreciaciones por estado. La interfaz pública no se verificó. **[VISTO: A6, A7; DESCONOCIDO: UI]** |
| **Siigo** | No se encontró evidencia pública explícita de un módulo de activos fijos. **[DESCONOCIDO]** |
| **Brecha** | Falta maestro de activo, adquisición, vida útil, método de depreciación, depreciación mensual, baja, venta, diferencias contables/fiscales y reporte. |
| **Prioridad** | **Alta** si la empresa tiene activos materiales o reporta bajo NIIF; **Media** para microempresa sin activos relevantes |
| **Entregable mínimo** | Activo con costo, fecha, vida útil y método; depreciación lineal mensual; asiento automático; baja con resultado; reporte por activo y por cuenta. |

**Por qué es Alta/condicionada:** la depreciación afecta el estado de resultados, el balance y la declaración de renta. Si el negocio tiene maquinaria, vehículos, equipo de cómputo o locales, no puede operar sin ella.

### 4.5 Edades de cartera

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | Las facturas tienen `due_date`, `balance` y `payment_status`, y el dashboard muestra cartera pendiente. No hay reporte por edades, por cliente ni por fecha de corte. **[VISTO: N4, N8]** |
| **Alegra** | Cuentas por cliente, facturas vencidas y análisis de cartera; no se confirmaron rangos configurables. **[VISTO: A1; DESCONOCIDO: buckets]** |
| **Siigo** | Cartera pendiente “por edades o rangos de fechas”, con responsable y recordatorios. **[VISTO: S1, S3]** |
| **Brecha** | Falta reporte de edades 0–30/31–60/61–90/90+, por cliente y fecha de corte, incluyendo notas crédito, facturas anuladas y moneda; faltan tareas de cobranza, promesas de pago y recordatorios. |
| **Prioridad** | **Alta** |
| **Entregable mínimo** | Reporte de edades por cliente y bucket, con saldo, vencimiento y días de mora; exportación CSV y tarjeta en el dashboard. Después, tareas y recordatorios. |

**Por qué es Alta:** la cartera es el activo más importante de muchas pymes. Sin edades no se prioriza la cobranza y se deteriora el flujo de caja.

### 4.6 Órdenes de compra

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | Solo existen facturas de compra y pagos a proveedores. No hay orden de compra, aprobación, recepción parcial, comparación precio/cantidad ni conversión a factura. **[VISTO: N6]** |
| **Alegra** | La API/MCP incluye órdenes de compra con CRUD y consulta. **[VISTO: A6]** |
| **Siigo** | La página de compras habla de cuentas por pagar y saldos vencidos; no se observó orden de compra. **[VISTO: S4; DESCONOCIDO: PO]** |
| **Brecha** | Falta ciclo `draft`/`sent`/`approved`/`partially_received`/`closed`, aprobaciones por monto, recepción parcial, conversión a factura, tolerancias y compromiso de compra. |
| **Prioridad** | **Media** (Alta para retail, manufactura o empresas con compras recurrentes y aprobaciones) |
| **Entregable mínimo** | Orden de compra con líneas, proveedor, precio y fecha; aprobación simple; recepción total/parcial; conversión a factura de compra; reporte de compromisos. |

**Por qué es Media:** no es obligatoria para vender, pero sin ella no hay control de compras, autorizaciones ni compromisos. Es la antesala natural de un control corporativo.

### 4.7 Cierres de caja POS

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | El POS busca ítems, arma carrito y emite factura. No registra pago, no abre/cierra caja, no maneja turnos, no hace arqueo, no registra movimientos de efectivo y no tiene terminal. **[VISTO: N7]** |
| **Alegra** | Cierres de caja, apertura/cierre de turnos, terminales y reportes de cierre. **[VISTO: A2]** |
| **Siigo** | Apertura/cierre de caja, turnos, movimientos y cuadres de caja. **[VISTO: S5]** |
| **Brecha** | Falta caja/terminal, sesión con base inicial, ventas en efectivo, entradas/salidas de caja, esperado vs. contado, diferencia, cierre inmutable, asiento y reporte por cajero/turno. |
| **Prioridad** | **Alta** para retail/POS; **Media** si el POS no es el canal principal |
| **Entregable mínimo** | Abrir sesión con base, registrar pagos en efectivo, cerrar con conteo, calcular diferencia y generar reporte; integrar con factura y asiento. |

**Por qué es Alta:** el POS es el punto donde se pierde dinero con más frecuencia. Sin sesión y arqueo no hay responsable, no hay control y no hay conciliación de efectivo.

### 4.8 Fiscalidad DIAN y documentos

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | Factura interna, nota crédito interna, numeración `FV` secuencial, impuesto solo nombre/tarifa y datos fiscales mínimos. No hay XML, CUFE/CUDE, firma, transmisión, resolución, documento soporte, buzón DIAN, retenciones ni exógena. **[VISTO: N8, N9, N11]** |
| **Alegra** | Facturación electrónica, notas, remisiones, recurrentes, buzón DIAN, documento soporte, retenciones y exógena. **[VISTO: A1, A3, A6]** |
| **Siigo** | Facturación electrónica, notas, documentos soporte, recibos, comprobantes y nómina electrónica. **[VISTO: S2, S8, S9]** |
| **Brecha** | Es un programa completo: datos maestros fiscales, catálogo de impuestos, resolución y numeración, XML, firma, transmisión, estados, contingencia, nota crédito, documento soporte, buzón, retenciones, exógena y RADIAN. |
| **Prioridad** | **Alta (bloqueante)** |
| **Entregable mínimo** | Fase 1: datos maestros + catálogo DIAN + numeración/resolución + XML + validación. Fase 2: firma, transmisión, estados, nota crédito y documento soporte. Fase 3: buzón, retenciones y exógena. |

**Por qué es Alta:** sin factura electrónica, una empresa colombiana no puede operar formalmente con Nexus como sistema principal. Esta brecha está por encima de cualquier comparación de features.

### 4.9 Contabilidad y cierre

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | PUC, asientos automáticos, estado de resultados y balance general. Los asientos son de solo lectura; no hay diario manual, cierre de periodos, balance de prueba, libro mayor, saldos iniciales, centros de costo ni reportes fiscales. **[VISTO: N4, N9]** |
| **Alegra** | Centros de costo, asientos, cierres, activos fijos, balance de prueba, libro mayor y reportes. **[VISTO: A6]** |
| **Siigo** | Contabilidad, documentos, estados financieros, centros de costo, reportes y cierre. **[VISTO: S2, S6, S10]** |
| **Brecha** | Falta COGS, diario manual, cierre/bloqueo de periodos, balance de prueba, libro mayor, saldos iniciales, dimensiones de centro de costo, reportes de impuestos y consolidación. |
| **Prioridad** | **Alta** para COGS/cierre; **Media** para centros de costo y consolidación |
| **Entregable mínimo** | Asiento de COGS, diario manual, balance de prueba, libro mayor y bloqueo de periodo. Después, centros de costo y reportes fiscales. |

**Por qué es Alta:** sin cierre y libros, la contabilidad es un registro, no un sistema de control. Y sin COGS, el estado de resultados no es confiable.

### 4.10 Inventario y costos

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | Movimientos y saldos por ítem/bodega, multi-bodega y tipos de movimiento. No hay valorización, costo promedio, COGS, conteo físico, documento de transferencia, lotes/series, stock mínimo ni listas de precios. **[VISTO: N12]** |
| **Alegra** | Inventario permanente, ajustes, transferencias, listas de precios, variantes y valorización. **[VISTO: A4, A6]** |
| **Siigo** | Kardex, valorización, costo promedio, conteo físico y transferencias. **[VISTO: S7]** |
| **Brecha** | Falta método de costeo, costo promedio, asiento de COGS, reporte de valorización, conteo físico, transferencia atómica, stock mínimo, lotes/series y listas de precios. |
| **Prioridad** | **Alta** para valorización/COGS; **Media** para lotes/series y listas de precios |
| **Entregable mínimo** | Costo promedio ponderado, asiento de COGS, reporte de valorización, conteo físico y transferencia con documento. |

**Por qué es Alta:** el inventario es uno de los activos más grandes de un negocio comercial. Sin valorización, el balance y el margen son incorrectos.

### 4.11 Nómina

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | Empleados, periodo mensual, salud 4 %, pensión 4 %, neto y asiento. No hay PILA, nómina electrónica, prestaciones, horas extras, cesantías, prima, vacaciones, aportes del empleador, retención en la fuente ni archivos bancarios. **[VISTO: N10]** |
| **Alegra** | Nómina electrónica y prestaciones. **[VISTO: A5]** |
| **Siigo** | Nómina electrónica, PILA, prestaciones, retención y archivos bancarios. **[VISTO: S8]** |
| **Brecha** | Falta liquidación colombiana completa, PILA, nómina electrónica, provisiones, liquidación de contrato, retención y archivos bancarios. |
| **Prioridad** | **Alta** si la nómina está en el alcance; **Media** si Nexus solo se usa para facturación y contabilidad |
| **Entregable mínimo** | Deducciones y aportes completos, provisiones, PILA y archivo de nómina electrónica. |

**Por qué es Alta/condicionada:** una nómina mal liquidada genera sanciones, demandas y diferencias con la DIAN y las cajas. Es un dominio especializado que requiere validación experta.

### 4.12 Plataforma, integraciones y capacidades adyacentes

| Dimensión | Hallazgo |
|---|---|
| **Nexus hoy** | API interna, sesiones, RBAC y documentación de arquitectura. No se observaron API tokens, webhooks, outbox, adjuntos, envío de correo, auditoría de acciones, aprobaciones, multiempresa, offline, campos personalizados, portal de clientes ni pagos en línea. **[VISTO: N3, N11]** |
| **Alegra** | API/MCP amplia, webhooks y ecosistema de integraciones. **[VISTO: A6]** |
| **Siigo** | API, webhooks y SDK. **[VISTO: S9]** |
| **Brecha** | Falta API pública con tokens y scopes, webhooks/outbox, adjuntos, email/PDF, auditoría, aprobaciones, multiempresa, offline, campos personalizados, portal y pagos en línea. |
| **Prioridad** | **Media** para API/webhooks/adjuntos/auditoría; **Baja** para IA/MCP, offline, portal y multimoneda |
| **Entregable mínimo** | Webhooks/outbox, adjuntos, auditoría y envío de documentos. La API pública puede esperar a que el núcleo sea estable. |

Capacidades adyacentes que tampoco se observaron en Nexus:

- Facturas recurrentes. **[VISTO: A6; no visto en Nexus]**
- Remisiones. **[VISTO: A6; no visto en Nexus]**
- Notas débito. **[VISTO: A6; no visto en Nexus]**
- Documento soporte. **[VISTO: A6, S9; no visto en Nexus]**
- Facturas electrónicas de proveedor en buzón. **[VISTO: A1; no visto en Nexus]**
- Multimoneda. **[VISTO: A6; Nexus solo COP]**
- Multiempresa/sucursales. **[VISTO: S6; no visto en Nexus]**
- Producción/BOM/órdenes de trabajo. **[VISTO: A6; no visto en Nexus]**

---

## 5. Matriz de priorización

### 5.1 Criterio

La prioridad no se asigna por “lo que tiene el competidor”. Se asigna por el costo de no tenerlo:

1. **Cumplimiento legal:** sin esto no se puede operar formalmente.
2. **Liquidez:** sin esto el negocio puede quebrar aunque venda.
3. **Integridad contable:** sin esto los reportes mienten.
4. **Control operativo:** sin esto se pierde dinero en caja, compras e inventario.
5. **Diferenciación:** solo después de lo anterior.

### 5.2 Matriz

| Prioridad | Brecha | Tipo | Por qué ahora | Depende de | Horizonte |
|---|---|---|---|---|---|
| **Alta** | Facturación electrónica DIAN, nota crédito, documento soporte, buzón, retenciones | Legal | Sin esto no hay operación formal | Datos maestros fiscales, catálogo DIAN, numeración | 1–3 meses |
| **Alta** | COGS y valorización de inventario | Integridad | El margen y el balance son incorrectos | Costeo, movimientos, asiento | 0–4 semanas |
| **Alta** | POS con pago, sesión y cierre de caja | Liquidez/control | El POS actual deja facturas impagas y no controla efectivo | Pago, caja, asiento | 1–2 meses |
| **Alta** | Conciliación bancaria con importación y matching | Liquidez/control | La conciliación manual no detecta diferencias | Modelo de extracto, pagos, reglas | 1–3 meses |
| **Alta** | Edades de cartera y cobranza | Liquidez | Sin cartera priorizada no hay flujo de caja | Facturas, notas crédito, clientes | 2–4 semanas |
| **Alta** | Flujo de caja y proyección | Liquidez | Es la pregunta central del dueño | Tesorería, CxC, CxP | 3–6 semanas |
| **Alta** | Activos fijos y depreciación | Integridad/legal | Afecta resultados, balance y renta | Asiento manual, periodos | 1–2 meses |
| **Alta** | Cierre de periodos, diario manual, balance de prueba y libro mayor | Integridad | Sin cierre no hay contabilidad controlada | Asientos, periodos | 1–2 meses |
| **Alta** | Nómina colombiana completa (si está en alcance) | Legal | PILA y nómina electrónica son obligatorias | Dominio de nómina, DIAN | 2–4 meses |
| **Media** | Órdenes de compra y aprobaciones | Control | Controla compromisos y compras | Proveedores, recepción, factura | 2–3 meses |
| **Media** | Presupuestos por cuenta y centro de costo | Control | Controla ejecución y desviaciones | Centros de costo, contabilidad | 2–3 meses |
| **Media** | Centros de costo | Control | Habilita presupuestos y rentabilidad por área | Asientos, dimensiones | 1–2 meses |
| **Media** | Conteo físico, transferencias y stock mínimo | Control | Evita faltantes y sobrestock | Inventario, costeo | 1–2 meses |
| **Media** | Facturas recurrentes, remisiones, notas débito y adjuntos | Operación | Reduce trabajo manual y errores | Documentos, PDF/email | 2–4 meses |
| **Media** | API pública, webhooks y auditoría | Plataforma | Habilita integraciones y confianza | Tokens, outbox, eventos | 3–6 meses |
| **Media** | Multiempresa/sucursales | Plataforma | Necesario para grupos y franquicias | Tenant, permisos, reportes | 4–6 meses |
| **Baja** | IA/MCP | Diferenciación | Útil, pero no corrige el núcleo | API, datos limpios | 6–12 meses |
| **Baja** | POS offline | Diferenciación | Útil para retail con conectividad frágil | POS, sincronización | 6–12 meses |
| **Baja** | Multimoneda | Diferenciación | La mayoría del mercado objetivo opera en COP | Contabilidad, tasas | 6–12 meses |
| **Baja** | Producción/BOM | Segmento | Solo si el target es manufactura | Inventario, costos | 6–12 meses |
| **Baja** | Portal de clientes, pagos en línea, CRM avanzado | Diferenciación | No bloquea la operación | API, seguridad | 6–12 meses |

### 5.3 Lo que no se debe hacer todavía

- **No** construir un asistente de IA que “conteste sobre los reportes” antes de que los reportes sean correctos.
- **No** copiar el menú completo de Alegra o Siigo para “parecer ERP”.
- **No** agregar multimoneda antes de dominar COP, IVA y retenciones.
- **No** agregar multiempresa antes de tener cierre y auditoría por empresa.
- **No** prometer “DIAN ready” mientras no exista transmisión y aceptación real.
- **No** usar el dashboard como fuente de verdad financiera mientras `total_revenue` sume pagos sin criterio contable.

---

## 6. Mapeo REA

### 6.1 Lectura REA de Nexus

En este informe, **REA** se usa como lente de análisis: **Resources–Events–Agents**. La recolección de evidencia de Alegra y Siigo se apoyó en las técnicas de la skill **leanrea**; el modelo REA se usa después para leer la cobertura del dominio de Nexus.

REA permite describir el negocio por **recursos económicos**, **eventos que los transforman o intercambian** y **agentes que participan**. Nexus está construido principalmente como un sistema de **documentos** (factura, compra, pago), no como un sistema de **eventos económicos completos**.

Eso no es necesariamente malo: los documentos son artefactos legales y operativos. El problema es que faltan eventos que expliquen la realidad física y financiera detrás del documento.

### 6.2 Tabla de mapeo

| Componente REA | Qué existe en Nexus | Qué falta | Impacto |
|---|---|---|---|
| **Recurso: efectivo y bancos** | `BankAccount`, `BankTransaction` | Caja/terminal, sesión de caja, línea de extracto, saldo proyectado | No se controla el efectivo ni se concilia automáticamente |
| **Recurso: inventario** | `Item`, `StockMovement`, `StockBalance` | Costo, valorización, lotes/series, stock mínimo, conteo | No se conoce el valor real del inventario |
| **Recurso: activos fijos** | No existe | Maestro, depreciación, baja, ubicación, responsable | No se reconoce depreciación ni se controla el activo |
| **Recurso: cuentas por cobrar** | `Invoice.balance`, `Payment` | Edades, cobranza, promesas, castigo, provisión | No se prioriza la cobranza ni se mide el riesgo |
| **Recurso: cuentas por pagar** | `PurchaseInvoice.balance`, `PurchasePayment` | Edades, programación de pagos, orden de compra | No se planifica el pago a proveedores |
| **Recurso: nómina** | `Employee`, `PayrollPeriod` | PILA, prestaciones, provisiones, nómina electrónica | No se cumple el ciclo laboral colombiano |
| **Evento: venta** | `Invoice`, salida de stock, asiento | Pago en POS, COGS, DIAN, remisión, recurrencia | La venta no cierra el ciclo económico |
| **Evento: compra** | `PurchaseInvoice`, entrada de stock, asiento | Orden de compra, recepción, 3-way match, documento soporte | No hay control de compromiso ni de recepción |
| **Evento: pago** | `Payment`, `PurchasePayment`, asiento | Vínculo con banco, retenciones, conciliación | El pago no se cruza con el extracto |
| **Evento: conciliación** | Booleano en `BankTransaction` | Extracto, matching, diferencias, periodo | No es un evento económico, es un checklist |
| **Evento: sesión de caja** | No existe | Apertura, movimientos, arqueo, cierre, diferencia | No hay custodia del efectivo |
| **Evento: depreciación** | No existe | Cálculo mensual, asiento, baja | No se reconoce el consumo del activo |
| **Evento: presupuesto** | No existe | Asignación, compromiso, ejecución, variación | No se controla la desviación |
| **Evento: cierre** | No existe | Cierre de periodo, bloqueo, ajustes | No hay corte contable confiable |
| **Agente: cliente** | `Contact` tipo `customer`/`both` | Datos fiscales, cupo, comportamiento, cobrador | No se evalúa riesgo ni se asigna cobranza |
| **Agente: proveedor** | `Contact` tipo `supplier`/`both` | Datos fiscales, condiciones, evaluación | No se controla el abastecimiento |
| **Agente: empleado** | `Employee` | Datos laborales completos, centro de costo, banco | Nómina incompleta |
| **Agente: cajero** | `User` con rol `CASHIER` | Turno, caja asignada, arqueo, responsable | No hay custodia ni segregación |
| **Agente: contador** | `User` con rol `ACCOUNTANT` | Aprobaciones, cierre, auditoría | No hay workflow contable |
| **Agente: centro de costo** | No existe | Dimensión, responsable, presupuesto | No se mide rentabilidad por área |
| **Dualidad: venta** | Entrega de inventario ↔ CxC/ingreso | Efectivo/CxC real, COGS, impuesto | Dualidad incompleta |
| **Dualidad: compra** | Inventario/gasto ↔ CxP | Recepción, orden, retención | Dualidad incompleta |
| **Dualidad: pago** | Caja/banco ↔ CxC/CxP | Extracto, conciliación, retención | Dualidad no verificada contra banco |
| **Compromiso: cotización** | `Quote` y conversión | Seguimiento, expiración, recordatorio | Parcial |
| **Compromiso: orden de compra** | No existe | Aprobación, recepción, factura | Ausente |
| **Compromiso: presupuesto** | No existe | Asignación, ejecución, variación | Ausente |
| **Conversión: cotización → factura** | Existe | Impuestos, DIAN, remisión | Funciona a nivel interno |
| **Conversión: orden → factura** | No existe | Recepción, 3-way match | Ausente |
| **Conversión: remisión → factura** | No existe | Documento de despacho | Ausente |
| **Custodia: stock** | Movimientos inmutables | Conteo, responsable, ubicación | Parcial |
| **Custodia: banco** | Movimientos inmutables | Extracto, matching, diferencias | Parcial |
| **Custodia: caja** | No existe | Sesión, arqueo, responsable | Ausente |

### 6.3 Conclusiones REA

- Nexus captura **documentos** y **asientos**, pero no todos los **eventos económicos**. Los eventos faltantes son, precisamente, los puntos de control: caja, banco, inventario valorizado, activos, compromisos y cierre.
- La dualidad de una venta no se completa con emitir la factura: falta el pago, el costo de venta y el documento fiscal.
- La dualidad de una compra no se completa con registrar la factura: falta la orden, la recepción y el documento soporte.
- La custodia del efectivo no se resuelve con un campo `method` en el pago: requiere caja, turno, arqueo y responsable.
- El diseño recomendado es un **híbrido documento + evento**: el documento conserva el valor legal; el evento conserva la realidad operativa y permite reportería, auditoría y conciliación.
- No hace falta event sourcing completo. Sí hace falta que cada evento tenga: fecha, agente, recurso, cantidad/valor, documento origen, asiento contable y trazabilidad.

---

## 7. Roadmap propuesto

El roadmap está ordenado por dependencias, no por deseo comercial. Cada fase debe cerrar con criterios de aceptación verificables.

### 7.1 Fase 0 — Verdad financiera (0–4 semanas)

**Objetivo:** que los números de Nexus sean confiables antes de agregar módulos.

- Implementar costeo y asiento de COGS al vender.
- Agregar valorización de inventario y reporte de costo.
- Ampliar `Tax` con tipo, código DIAN y uso (IVA, INC, ICA, retención).
- Ampliar datos fiscales de empresa y contactos.
- Agregar diario manual, balance de prueba, libro mayor y bloqueo de periodo.
- Corregir el KPI `total_revenue` o renombrarlo para que no se confunda con ingreso devengado.
- Pruebas doradas de redondeo, impuestos y COGS.

**Criterio de salida:** una venta y una compra producen asientos completos; el balance y el estado de resultados cuadran; el inventario contable coincide con el inventario físico valorizado.

### 7.2 Fase 1 — Cumplimiento DIAN (1–3 meses)

**Objetivo:** emitir documentos válidos y recibir documentos de proveedores.

- Resolución, prefijo, rango y numeración autorizada.
- XML de factura electrónica, nota crédito y documento soporte.
- Firma electrónica y transmisión.
- Estados: pendiente, aceptada, rechazada, contingencia.
- Buzón DIAN y recepción de facturas de proveedores.
- Retenciones y reportes de exógena.
- Nómina electrónica si está en alcance.

**Criterio de salida:** una factura real es aceptada por la DIAN; una nota crédito la referencia; un documento soporte se genera; un rechazo se puede corregir sin romper la contabilidad.

### 7.3 Fase 2 — Liquidez y caja (2–4 meses)

**Objetivo:** controlar el efectivo y anticipar el flujo.

- POS: registrar pago, medio de pago, caja y cambio.
- Sesión de caja: apertura, movimientos, arqueo, cierre y diferencia.
- Importación de extractos CSV/OFX.
- Matching bancario, reglas, sugerencias y diferencias.
- Reporte de flujo de caja y proyección a 13 semanas.
- Edades de cartera y tareas de cobranza.

**Criterio de salida:** un cierre de caja cuadra o explica su diferencia; un extracto bancario se concilia; el flujo de caja proyectado usa vencimientos reales de CxC y CxP.

### 7.4 Fase 3 — Control corporativo (3–6 meses)

**Objetivo:** controlar compras, presupuesto, activos e inventario.

- Órdenes de compra, aprobaciones y recepción parcial.
- Conversión orden → factura y 3-way match.
- Presupuestos por cuenta y centro de costo.
- Centros de costo en asientos y documentos.
- Activos fijos y depreciación.
- Conteo físico, transferencias y stock mínimo.
- Facturas recurrentes, remisiones y notas débito.

**Criterio de salida:** una compra se autoriza, recibe y factura con trazabilidad; un presupuesto se compara con lo real; un activo se deprecia y se da de baja correctamente.

### 7.5 Fase 4 — Plataforma (6–12 meses)

**Objetivo:** abrir el sistema sin sacrificar el núcleo.

- API pública con tokens, scopes y documentación.
- Webhooks y outbox.
- Adjuntos, PDF, email y auditoría.
- Multiempresa/sucursales.
- Offline POS.
- Multimoneda.
- IA/MCP sobre datos confiables.

**Criterio de salida:** un tercero puede integrarse sin acceso a la base de datos; un evento se publica después del commit; una empresa puede operar varias sucursales sin mezclar datos.

### 7.6 Dependencias críticas

```text
Datos fiscales + catálogo DIAN
        │
        ├── Factura electrónica
        │       └── Nota crédito / documento soporte / buzón
        │
        └── Retenciones / exógena

COGS + valorización
        │
        ├── Estado de resultados confiable
        ├── Flujo de caja confiable
        └── Cierre contable

Pago en POS
        │
        └── Sesión de caja → arqueo → cierre

Extracto bancario
        │
        └── Matching → conciliación → flujo de caja

Centros de costo
        │
        └── Presupuestos → variaciones

Órdenes de compra
        │
        └── Recepción → factura → 3-way match
```

---

## 8. Decisiones de diseño y no negociables

### 8.1 Dinero y transacciones

- Todo monto monetario se representa con `Decimal` en Python y `NUMERIC` en PostgreSQL. Nunca `float`. **[VISTO: N8, N11]**
- Las operaciones de negocio que afectan documentos, inventario, contabilidad o caja deben ejecutarse dentro de `operation_transaction`. **[VISTO: N3, N9]**
- Los comandos críticos deben ser idempotentes y usar bloqueo optimista. **[VISTO: N8, N11]**
- Los movimientos de stock y banco son inmutables; las correcciones se hacen con movimientos compensatorios. **[VISTO: N5, N12]**
- No se eliminan documentos emitidos; se anulan con contra-asiento y trazabilidad. **[VISTO: N9]**

### 8.2 Fiscalidad

- Las reglas DIAN, retenciones, firma y numeración requieren validación de contador y experto DIAN. No se inventan. **[VISTO: N11]**
- El catálogo de impuestos debe distinguir tipo, código DIAN, tarifa, base y uso. **[VISTO: N8; INFERIDO: requisito para XML]**
- La numeración debe estar ligada a resolución, prefijo, rango y vigencia. **[INFERIDO: requisito DIAN]**
- La factura electrónica no se debe implementar como “un PDF con logo”: requiere XML, firma, transmisión y estado. **[INFERIDO]**
- La contingencia y el rechazo deben ser estados de primera clase, no errores genéricos. **[INFERIDO]**

### 8.3 Contabilidad

- El asiento debe reflejar el hecho económico completo: venta, costo, impuesto, retención, pago y banco. **[INFERIDO: N9]**
- No se debe usar el asiento contable como sustituto del evento operativo; ambos son necesarios. **[INFERIDO]**
- El cierre de periodo debe bloquear ediciones y permitir ajustes auditados. **[INFERIDO]**
- Los reportes deben poder explicar su origen: documento → evento → asiento → cuenta. **[INFERIDO]**

### 8.4 Seguridad y control

- RBAC no es suficiente: se requiere segregación de funciones y aprobaciones por monto. **[INFERIDO: N3]**
- El cajero no debería poder abrir, cobrar, cerrar y conciliar su propia caja sin revisión. **[INFERIDO]**
- El contador no debería poder emitir facturas sin control. **[INFERIDO]**
- Toda acción sensible debe tener auditoría: quién, cuándo, qué cambió y por qué. **[INFERIDO]**
- Los adjuntos y documentos fiscales deben almacenarse con integridad y control de acceso. **[INFERIDO]**

### 8.5 Frontend

- No se pasan manejadores de eventos desde Server Components a Client Components. La interacción vive en componentes `"use client"`. **[VISTO: N2, N7]**
- Solo el Root Layout contiene `<html>` y `<body>`. **[VISTO: N2]**
- Los cálculos de dinero en el cliente deben usar una estrategia exacta o delegar el cálculo final al backend; no `Number`/`Math.round` para totales fiscales. **[VISTO: N7; INFERIDO: riesgo]**
- Los estados ambiguos deben nombrarse con precisión: “conciliado”, “pagado”, “emitido”, “aceptado por DIAN” no son sinónimos. **[INFERIDO]**

---

## 9. Riesgos y supuestos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Comercializar Nexus como “DIAN ready” sin implementación | Riesgo legal y reputacional | Comunicar el estado real; no prometer cumplimiento hasta tener aceptación DIAN |
| Reportes incorrectos por falta de COGS | Decisiones de precio, margen y rentabilidad equivocadas | Fase 0 antes de nuevos reportes |
| POS sin pago ni caja | Pérdida de efectivo y cartera falsa | Fase 2 con pago, sesión y arqueo |
| Conciliación manual | Fraudes, duplicados y diferencias no detectadas | Importación y matching |
| Nómina básica | Sanciones laborales y fiscales | Validación experta y nómina completa |
| Competidores con más módulos | Pérdida de oportunidades comerciales | Competir por núcleo correcto y transparencia, no por menú |
| Evidencia pública incompleta de competidores | Conclusiones sesgadas | Etiquetar `[DESCONOCIDO]`; no afirmar ausencia |
| Scope creep | Retraso del núcleo | Roadmap por fases y criterios de salida |
| Migración de datos | Pérdida de historial | Importadores, validación y conciliación de saldos iniciales |
| Adopción del usuario | Procesos mal usados | UX simple, valores por defecto y capacitación |

**Supuestos:**

- El mercado objetivo principal es Colombia y opera en COP.
- La empresa necesita facturación electrónica DIAN para operar formalmente.
- El POS es relevante para al menos una parte del mercado objetivo.
- La nómina puede quedar fuera del alcance inicial si Nexus se posiciona como facturación + contabilidad + tesorería.
- No se evaluaron precios ni disposición a pagar.

---

## 10. Anexos

### A. Rutas actuales de Nexus

| Módulo | Backend | Frontend |
|---|---|---|
| Autenticación | `/api/v1/auth/*` | `/login`, `/register` |
| Dashboard | `/api/v1/dashboard/summary` | `/dashboard` |
| Contactos | `/api/v1/contacts` | `/contacts` |
| Ítems | `/api/v1/items` | `/items` |
| Impuestos | `/api/v1/taxes` | `/taxes` |
| Facturas | `/api/v1/invoices` | `/invoices`, `/invoices/new`, `/invoices/[id]` |
| Pagos | `/api/v1/payments` | Integrado en detalle de factura |
| Cotizaciones | `/api/v1/quotes` | `/quotes`, `/quotes/new`, `/quotes/[id]` |
| Compras | `/api/v1/purchases` | `/purchases`, `/purchases/new`, `/purchases/[id]` |
| Gastos | `/api/v1/expenses` | `/expenses`, `/expenses/new` |
| Tesorería | `/api/v1/treasury` | `/treasury`, `/treasury/accounts/new`, `/treasury/accounts/[id]` |
| Inventario | `/api/v1/inventory` | `/inventory` |
| Bodegas | `/api/v1/warehouses` | `/warehouses` |
| POS | `/api/v1/pos/search` | `/pos` |
| Nómina | `/api/v1/payroll` | `/payroll` |
| Empleados | `/api/v1/employees` | `/employees` |
| Contabilidad | `/api/v1/accounting` | `/reports/financials` |
| Reportes | `/api/v1/reports/*` | `/reports/financials` |
| Configuración | `/api/v1/settings/company` | `/settings` |
| Usuarios | `/api/v1/users` | `/users` |

### B. Modelos actuales y brecha principal

| Modelo | Propósito | Brecha principal |
|---|---|---|
| `Invoice` | Factura de venta | Sin DIAN, sin COGS, sin retenciones |
| `InvoiceLine` | Línea de factura | Sin centro de costo, sin código DIAN |
| `Payment` | Pago recibido | Sin cuenta bancaria, sin vínculo con extracto |
| `CreditNote` | Nota crédito | Sin versión electrónica DIAN |
| `Quote` | Cotización | Sin seguimiento comercial avanzado |
| `PurchaseInvoice` | Factura de compra | Sin orden de compra, sin recepción, sin documento soporte |
| `PurchasePayment` | Pago a proveedor | Sin cuenta bancaria, sin programación de pagos |
| `Expense` | Gasto operativo | Sin centro de costo, sin retención |
| `BankAccount` | Cuenta bancaria | Solo COP, sin integración bancaria |
| `BankTransaction` | Movimiento bancario | Sin extracto, sin matching, sin diferencias |
| `Item` | Producto/servicio | Sin costo, sin SKU, sin stock mínimo, sin categoría |
| `StockMovement` | Movimiento de inventario | Sin valorización, sin documento de transferencia |
| `StockBalance` | Saldo por bodega | Sin costo promedio |
| `Tax` | Impuesto | Sin tipo, sin código DIAN, sin retención |
| `CompanySetting` | Datos de empresa | Sin datos fiscales completos |
| `Contact` | Cliente/proveedor | Sin datos fiscales completos, sin cupo |
| `Employee` | Empleado | Sin datos laborales completos |
| `PayrollPeriod` | Periodo de nómina | Sin PILA, prestaciones, e-nómina |
| `AccountingAccount` | Cuenta PUC | Sin dimensión de centro de costo |
| `AccountingEntry` | Asiento | Sin diario manual, sin cierre, sin aprobación |
| `AccountingEntryLine` | Línea de asiento | Sin centro de costo, sin documento soporte |

### C. Checklist de módulos obligatorios

| Módulo | Estado Nexus | Prioridad |
|---|---|---|
| Facturación electrónica DIAN | No | Alta |
| Nota crédito electrónica | No | Alta |
| Documento soporte | No | Alta |
| Buzón DIAN | No | Alta |
| Retenciones / exógena | No | Alta |
| Nómina electrónica / PILA | No | Alta si aplica |
| Flujo de caja | No | Alta |
| Conciliación bancaria automática | No | Alta |
| Edades de cartera | No | Alta |
| Cierres de caja POS | No | Alta |
| COGS / valorización | No | Alta |
| Activos fijos / depreciación | No | Alta/Media |
| Órdenes de compra | No | Media |
| Presupuestos | No | Media |
| Centros de costo | No | Media |
| Cierre de periodos | No | Alta |
| Diario manual / balance de prueba / libro mayor | No | Alta |
| Facturas recurrentes | No | Media |
| Remisiones | No | Media |
| Notas débito | No | Media |
| Multimoneda | No | Baja/Media |
| Multiempresa | No | Baja/Media |
| API pública / webhooks | No | Media |
| IA / MCP | No | Baja |
| Offline POS | No | Baja |

### D. Preguntas abiertas

1. ¿Nexus se posicionará como facturador + contabilidad + tesorería, o como ERP completo con nómina y manufactura?
2. ¿La facturación electrónica se implementará propia o mediante un proveedor tecnológico autorizado?
3. ¿El POS es parte del producto principal o un módulo opcional?
4. ¿La nómina está en el alcance del primer año?
5. ¿Se necesitan activos fijos desde el inicio o solo para empresas medianas?
6. ¿Se requiere multiempresa/sucursales en el corto plazo?
7. ¿Se necesita offline para retail?
8. ¿Se integrará con bancos colombianos o solo importación de extractos?
9. ¿Se ofrecerá API pública a terceros?
10. ¿Qué segmento es el “beachhead”: servicios, retail, distribución o manufactura?

### E. Glosario

| Término | Significado |
|---|---|
| **REA** | Resources–Events–Agents: modelo para describir recursos, eventos económicos y agentes. |
| **COGS** | Cost of Goods Sold; costo de los bienes vendidos. |
| **Aging / edades de cartera** | Clasificación de saldos por antigüedad de vencimiento. |
| **Arqueo** | Conteo físico del efectivo en caja y comparación con lo esperado. |
| **3-way match** | Comparación entre orden de compra, recepción y factura del proveedor. |
| **DIAN** | Dirección de Impuestos y Aduanas Nacionales de Colombia. |
| **CUFE/CUDE** | Códigos únicos de factura electrónica / documento electrónico. |
| **PUC** | Plan Único de Cuentas colombiano. |
| **Exógena** | Reporte de información tributaria a la DIAN. |
| **PILA** | Planilla Integrada de Liquidación de Aportes. |
| **RADIAN** | Registro de facturas electrónicas y eventos asociados. |
| **NIIF** | Normas Internacionales de Información Financiera. |
| **Outbox** | Patrón de publicación de eventos después del commit. |
| **Idempotencia** | Propiedad por la cual repetir una operación no duplica su efecto. |

### F. Fuentes consultadas

#### Nexus

- `README.md`
- `specs/ARQUITECTURA.md`
- `specs/DECISIONES.md`
- `specs/ESPECIFICACION-FUNCIONAL.md`
- `backend/app/main.py`
- `backend/app/api/v1/reports.py`
- `backend/app/api/v1/treasury.py`
- `backend/app/api/v1/purchases.py`
- `backend/app/api/v1/pos.py`
- `backend/app/domain/models/bank.py`
- `backend/app/domain/models/purchase.py`
- `backend/app/domain/models/invoice.py`
- `backend/app/domain/models/payment.py`
- `backend/app/domain/models/tax.py`
- `backend/app/domain/models/company_setting.py`
- `backend/app/domain/models/stock.py`
- `backend/app/application/accounting/service.py`
- `backend/app/application/payroll/service.py`
- `backend/app/application/inventory/service.py`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/pos/PosClient.tsx`

#### Alegra

- https://www.alegra.com/colombia/contabilidad/
- https://www.alegra.com/colombia/punto-de-venta/
- https://www.alegra.com/colombia/facturacion/
- https://www.alegra.com/colombia/inventarios/
- https://www.alegra.com/colombia/nomina/
- https://developer.alegra.com/llms.txt
- https://developer.alegra.com/reference/accounting_getfixedasset.md

#### Siigo

- https://www.siigo.com/nube/
- https://www.siigo.com/software-contable/
- https://www.siigo.com/software-de-cobranza/
- https://www.siigo.com/software-de-compras/
- https://www.siigo.com/punto-de-venta/
- https://www.siigo.com/software-de-costos/
- https://www.siigo.com/software-de-inventario/
- https://www.siigo.com/software-de-nomina/
- https://siigoapi.docs.apiary.io/
- https://www.siigo.com/ia/

---

## 11. Cierre

Nexus no está “atrasado” frente a Alegra y Siigo por una lista de pantallas. Está atrasado en la **profundidad de los eventos económicos** y en el **cumplimiento fiscal**. La buena noticia es que la base técnica es sólida y el orden correcto está claro:

1. Corregir COGS, impuestos y datos fiscales.
2. Implementar DIAN.
3. Controlar caja y banco.
4. Agregar control corporativo.
5. Abrir la plataforma.

Si se invierte el orden —por ejemplo, IA, MCP o multimoneda antes de COGS y DIAN— el producto se vuelve más vistoso pero menos confiable. Para un ERP colombiano, la confiabilidad es la característica principal.
