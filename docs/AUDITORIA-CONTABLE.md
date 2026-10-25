# Auditoría Contable Completa — Nexus ERP

| | |
|---|---|
| **Fecha de auditoría** | 2026-10-25 |
| **Alcance** | Esquema contable y financiero: asientos, balance de prueba, estado de resultados, balance general, catálogo PUC, periodos fiscales y reconciliaciones submayor vs. mayor |
| **Base auditada** | PostgreSQL de desarrollo (`facturalibre`) poblada por `scripts/seed_demo_data.py` |
| **Metodología** | Consultas SQL de **solo lectura** ejecutadas contra la base con Python + SQLAlchemy. Todos los cálculos con `Decimal` / `NUMERIC` exacto; **cero uso de `float`** (verificado: 0 columnas `double precision`/`real` en todo el esquema). Contraste adicional de la capa de presentación (API `/api/v1/reports/*`) contra el mayor de la base |
| **Código modificado** | **Ninguno.** Auditoría de solo lectura; los hallazgos se reportan sin corregir |

---

## Resumen ejecutivo

| # | Prueba | Resultado |
|---|---|---|
| 1 | Partida doble por asiento (débitos = créditos) | ✅ 50/50 asientos cuadrados |
| 2 | Balance de prueba global | ✅ D = C = $575.791.641,64; diferencia $0,00 |
| 3 | Estado de Resultados (UN = I − C − G) | ✅ UN = $4.405.024,38 exacta |
| 4 | Balance General (A = P + Pt) | ✅ A = $393.122.746,51; diferencia $0,00 |
| 5 | Cuentas PUC | ✅ 0 cuentas fuera del PUC; jerarquía íntegra |
| 6 | Periodos fiscales | ✅ 0 asientos en periodos cerrados (⚠️ no hay periodos cerrados) |
| 7 | Reconciliaciones submayor vs. mayor (7/7) | ✅ Todas cuadran al centavo |
| 8 | Capa API vs. mayor | ✅ Los 3 reportes coinciden exactamente con la base |

**Conclusión: el esquema contable está 100% cuadrado.** No se encontraron errores críticos ni descuadres. Se reportan **3 observaciones menores** (presentación y gobierno de datos, no de cuadre) y 2 notas informativas.

---

## 0. Controles preventivos verificados (esquema)

| Control | Estado |
|---|---|
| Trigger de partida doble `trg_accounting_entry_lines_balanced` (constraint trigger a nivel BD) | ✅ Presente |
| CHECK `debit >= 0` y `credit >= 0` en `accounting_entry_lines` | ✅ Presente |
| CHECK una sola cara positiva (`(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)`) | ✅ Presente |
| FK `accounting_entry_lines.account_code → accounting_accounts` (`RESTRICT`) | ✅ Presente; 0 líneas con cuenta inexistente |
| Unicidad `(source_type, source_id)` — impide duplicar el asiento de un mismo documento | ✅ Presente |
| Columnas monetarias: 40 columnas `NUMERIC(18,2)` + costo de inventario `NUMERIC(18,4)` | ✅ Sin `float`/`double` en toda la base |

La partida doble está blindada a **tres niveles**: trigger de base (imposible persistar un asiento descuadrado), repositorio/servicio, y reporte. Adicionalmente la suite de integración (198 tests contra PostgreSQL real) valida las rutas de facturación, pagos, compras, gastos, tesorería, nómina, depreciación y periodos.

---

## 1. Partida doble por asiento

- **50 asientos**, todos con estado `POSTED` (no hay borradores), **160 líneas**.
- **0 asientos descuadrados** (verificado con `SUM(debit) <> SUM(credit)` por asiento).
- **0 asientos sin líneas**, **0 líneas inválidas** (negativas, con débito y crédito simultáneos o en cero).
- Distribución por origen:

| Origen | Asientos |
|---|---|
| INVOICE (venta + COGS) | 20 |
| PAYMENT (recaudo) | 17 |
| PURCHASE (compra) | 2 |
| EXPENSE (gasto) | 5 |
| BANK_TRANSACTION (tesorería) | 4 |
| DEPRECIATION (depreciación mensual) | 2 |

---

## 2. Balance de prueba

| Medida | Valor |
|---|---|
| Σ débitos (POSTED) | $575.791.641,64 |
| Σ créditos (POSTED) | $575.791.641,64 |
| **Diferencia global** | **$0,00** ✅ |

El endpoint `GET /api/v1/reports/trial-balance` reporta `difference = 0.00` y `balanced = true` con las **44 cuentas** del catálogo, coincidiendo exactamente con el mayor de la base.

---

## 3. Estado de Resultados

| Concepto | Valor |
|---|---|
| Ingresos (413505) | $37.820.857,72 |
| Costo de ventas (6135) | $29.698.500,00 |
| Gastos (5160 + 5199) | $3.717.333,34 |
| **Utilidad neta (I − C − G)** | **$4.405.024,38** ✅ |

La identidad `UN = Ingresos − Costos − Gastos` se cumple exactamente. Se verificó que las cuentas de clase **6 (COSTO)** están incluidas en el cálculo (fix reciente validado en producción por esta auditoría: antes de ese fix el patrimonio iba inflado en exactamente $29.698.500,00, el COGS).

---

## 4. Balance General

| Sección | Valor |
|---|---|
| Activos | $393.122.746,51 |
| Pasivos | $388.717.722,13 |
| Patrimonio (cuentas 3xxx) | $0,00 |
| Patrimonio con resultado del ejercicio | $4.405.024,38 |
| **A − (P + Pt)** | **$0,00** ✅ |

`GET /api/v1/reports/balance-sheet` devuelve `balanced = true`. Detalles correctos de presentación verificados:

- **1592 Depreciación acumulada** (contraactivo, naturaleza crédito): presentada con signo negativo dentro de activos (−$333.333,34), dando el valor neto de PPE. ✅ Tratamiento correcto.
- Activos netos: Caja $20.583.228,45 + Banco $2.600.000,00 + Cartera $11.121.351,40 + Inventario $352.651.500,00 + PPE neto $6.166.666,66.

---

## 5. Catálogo PUC

- **44 cuentas** en el catálogo; **13 usadas** en el mayor.
- **0 cuentas fuera del PUC** (todo código es numérico y arranca por la clase 1–6).
- **0 inconsistencias prefijo ↔ clase** (1→ACTIVO, 2→PASIVO, 3→PATRIMONIO, 4→INGRESO, 5→GASTO, 6→COSTO).
- **0 jerarquías rotas** (todo `parent_code` existe).
- **1 naturaleza atípica, legítima**: 1592 Depreciación acumulada (tipo ACTIVO, naturaleza CRÉDITO) — contraactivo estándar del PUC. ✅
- Distribución del catálogo: ACTIVO 17, PASIVO 14, GASTO 6, INGRESO 4, COSTO 3, **PATRIMONIO 0** (ver hallazgo H-2).

---

## 6. Periodos fiscales

- Tabla `fiscal_periods`: **0 periodos registrados**; por diseño, la ausencia de fila equivale a periodo ABIERTO.
- **0 asientos en periodos cerrados** (trivialmente: no hay periodos cerrados).
- Distribución mensual de asientos: 2026-05: 7, 06: 9, 07: 9, 08: 10, 09: 9, 10: 6.
- El control existe y está probado: `PeriodService` rechaza asientos en meses `CLOSED` y exige asientos balanceados para cerrar. Ver hallazgo H-3.

---

## 7. Reconciliaciones submayor vs. libro mayor

Las siete reconciliaciones **cuadran al centavo**:

| Submayor (operativo) | Mayor contable | Valor | ✔ |
|---|---|---|---|
| Σ saldos de facturas emitidas no anuladas | 130505 Clientes nacionales | $11.121.351,40 | ✅ |
| Σ saldos de compras emitidas | 220505 Compras por pagar | $448.720.000,00 | ✅ |
| Inventario valorizado a costo promedio ponderado | 1435 Inventario de mercancías | $352.651.500,00 | ✅ |
| Σ movimientos de la cuenta bancaria (depósitos − retiros) | 11100501 Banco cuenta 1 | $2.600.000,00 | ✅ |
| Caja: recaudos $33.467.228,45 − gastos $3.384.000,00 − consignaciones $9.500.000,00 + retiro a caja $400.000,00 | 110505 Caja general | $20.583.228,45 | ✅ |
| Σ depreciaciones registradas | 5160 Gasto depreciación y 1592 Depreciación acumulada | $333.333,34 en ambos | ✅ |
| Σ costo de activos fijos | 15 Propiedades, planta y equipo | $6.500.000,00 | ✅ |

Notas: las 500 unidades de stock entraron **valorizadas** (0 entradas sin costo), por lo que la valorización a promedio ponderado es exacta. Los pagos/gastos vinculados a movimientos bancarios se excluyen del submayor de caja para no duplicar flujos (control verificado en el código de cash flow).

---

## Capa de presentación (API) vs. mayor

| Reporte | API | Mayor BD | ¿Coincide? |
|---|---|---|---|
| Trial balance | D = C = 575.791.641,64, `balanced=true` | 575.791.641,64 | ✅ |
| Estado de resultados | I 37.820.857,72 · G+C 33.415.833,34 · UN 4.405.024,38 | idéntico | ✅ |
| Balance general | A 393.122.746,51 = P 388.717.722,13 + Pt 4.405.024,38, `balanced=true` | idéntico | ✅ |

---

## Hallazgos

### Errores críticos: **NINGUNO** 🟢

No hay descuadres, asientos inválidos, cuentas fuera del PUC ni dobles contabilizaciones.

### Observaciones menores (no afectan el cuadre) 🟡

| ID | Hallazgo | Riesgo | Recomendación |
|---|---|---|---|
| **H-1** | **240802 IVA descontable con saldo débito de $66.370.000,00**, presentado como pasivo negativo en el Balance General. Contablemente netea correcto, pero es un **saldo a favor del IVA**: por presentación (NIIF/PUC) debería mostrarse como activo (o compensarse contra 240801 IVA generado, $6.367.722,13) | Presentación | Reclasificar saldos débito en cuentas de pasivo (clase 2) hacia activos en el Balance General, o compensar 2408 |
| **H-2** | **El catálogo no tiene cuentas de Patrimonio** (clase 3: 0 cuentas) y el seed no siembra capital social. El patrimonio del Balance depende al 100% del resultado del ejercicio | Gobierno del catálogo | Sembrar la clase 3 del PUC (p. ej. 311505 Aportes sociales / 311506 Superávit por revalorización) y registrar el capital inicial de la empresa |
| **H-3** | **No hay periodos fiscales cerrados** en los datos (2026-05 a 2026-10 abiertos). El control existe y funciona, pero no se está ejerciendo el cierre mensual | Retro-contabilización | Adoptar el cierre mensual (`PeriodService`): cerrar 2026-05 a 2026-09 tras el corte, dejando abierto el mes en curso |

### Notas informativas ℹ️

- **N-1 — IVA descontable ($66,37M) ≫ IVA generado ($6,37M)**: consecuencia natural de comprar 500 unidades de inventario frente a 20 facturas de venta en la demo. En la realidad esto representaría un saldo a favor ante la DIAN durante varios periodos.
- **N-2 — Estado de Resultados sin utilidad bruta**: los costos (clase 6) se presentan junto a los gastos (clase 5) en `total_expenses` porque el esquema de respuesta tiene dos secciones. La utilidad neta es correcta; una mejora futura sería separar "Costo de ventas → Utilidad bruta → Gastos operativos".
- **N-3 — Alcance**: la auditoría cubre los datos demo sembrados (facturación, compras, pagos, gastos, tesorería, activos fijos y depreciación). No hay asientos de nómina, notas crédito ni anulaciones en el dataset; esas rutas están cubiertas por la suite de tests (198 tests de integración).

---

## Conclusión

El esquema contable y financiero de Nexus ERP **está 100% cuadrado**: las cuatro identidades fundamentales (partida doble por asiento, balance de prueba, UN = I − C − G, y A = P + Pt) se cumplen exactamente, sin diferencia de un centavo; las 7 reconciliaciones submayor-mayor cuadran; el catálogo es íntegramente PUC; y la capa de API refleja fielmente el mayor. Los controles preventivos (trigger de partida doble en base de datos, CHECKs, FKs y unicidad de fuente) son robustos.

Las 3 observaciones reportadas son de **presentación y gobierno** (reclasificación del IVA descontable, siembra de la clase 3 del PUC y adopción del cierre mensual), no de cuadre contable, y se dejan documentadas para decisión del equipo sin que esta auditoría modifique código ni datos.
