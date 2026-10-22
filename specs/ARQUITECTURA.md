# Arquitectura técnica — FacturaLibre MVP

> **Estado:** aceptado para el MVP
> **Fecha:** 2026-10-21
> **Alcance:** Colombia, COP, MVP educativo y open source
> **Documentos base:** `specs/ESPECIFICACION-FUNCIONAL.md`, `specs/DECISIONES.md`
> **Regla de este documento:** decide estructura y fronteras. **No contiene código de aplicación.**

---

## 0. Cómo leer este documento

Cada decisión importante está escrita como un **ADR corto** (Architecture Decision Record) con cinco partes:

1. **Contexto:** qué problema obliga a decidir.
2. **Opciones consideradas:** alternativas reales, no paja.
3. **Decisión:** qué se eligió.
4. **Justificación:** por qué, con criterio explícito.
5. **Consecuencias:** qué ganamos, qué perdemos y cómo mitigamos.

Cuando una decisión depende de una norma o de una política que no podemos fijar con certeza, aparece **`REQUIERE VALIDACIÓN`** y se indica con quién. No se inventan benchmarks: las comparaciones son por capacidades, ecosistema o criterio de ingeniería, no por números que no hemos medido.

---

## 1. Resumen ejecutivo

Elegimos un **monolito modular API-first**, no una red de microservicios: un solo backend desplegable con módulos internos bien separados.

- **Backend:** Python + FastAPI + PostgreSQL + SQLAlchemy 2 + Alembic.
- **Frontend:** Next.js + TypeScript sobre la misma API `/api/v1`.
- **Dinero:** `NUMERIC` en base de datos y `Decimal` en código; nunca `float`.
- **Autenticación:** sesiones opacas para la UI y tokens opacos para integraciones; sin JWT.
- **Prioridad:** que una factura, un pago y una numeración sean correctos, idempotentes y auditables.
- **Frontera fiscal:** todo lo que implique reglas DIAN, retenciones o firma electrónica requiere validación humana antes de implementarse.

En una frase: elegimos la arquitectura que hace **correcta** la factura antes que **escalable**, porque el MVP no tiene un problema de escala demostrado y sí un problema de integridad fiscal.

---

## 2. Stack técnico con ADRs

### Stack resultante (vista rápida)

| Capa | Elección | Versión / criterio |
|---|---|---|
| Lenguaje backend | Python | 3.12+; CI fija la misma versión que producción |
| Framework backend | FastAPI + Pydantic v2 | OpenAPI 3.1, validación estricta |
| Base de datos | PostgreSQL | 16 o superior, fijada en Docker Compose |
| ORM / migraciones | SQLAlchemy 2 + Alembic | Sesiones síncronas, transacciones explícitas |
| Driver | psycopg 3 | Conexión síncrona |
| Frontend | Next.js + TypeScript | App Router, React Server Components donde aplique |
| Paquetes backend | `uv` | Lockfile comprometido |
| Paquetes frontend | `pnpm` | Lockfile comprometido |
| Autenticación | Sesiones opacas + API tokens | Sin JWT en MVP |
| Pruebas backend | pytest + Hypothesis + testcontainers | PostgreSQL real en integración |
| Pruebas frontend | Vitest + Playwright | Unitarias y E2E crítico |
| Despliegue | Docker Compose + Caddy | Un VPS; sin Kubernetes |
| Contrato | OpenAPI 3.1 en `/api/v1` | Snapshot versionado y cliente generado |

---

### ADR-001 — Lenguaje y framework backend

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** FacturaLibre es una API financiera con cálculos decimales, validación fuerte de entrada, documentación OpenAPI y un equipo pequeño que ya trabaja con Python, Node, Rust y Go. El backend debe ser fácil de entender para contribuidores open source y rápido de iterar sin sacrificar corrección.

**Opciones consideradas.**

1. **Python 3.12+ con FastAPI.** Pydantic v2, OpenAPI automático, `Decimal` nativo, `uv` para dependencias.
2. **NestJS con TypeScript.** Tipado de extremo a extremo, estructura opinionada, ecosistema Node.
3. **Go con Chi o Fiber.** Binario único, buen rendimiento, tipado estático.
4. **Rust con Axum.** Seguridad de memoria y rendimiento, curva de aprendizaje alta.

**Decisión.** **Python 3.12+ + FastAPI + Pydantic v2**, con `uv`, Ruff y mypy. FastAPI genera el contrato OpenAPI y valida en el borde; el dominio se escribe en Python puro.

**Justificación.** Es la combinación con mejor relación entre velocidad de desarrollo, legibilidad y soporte nativo de decimales para este equipo. Pydantic permite rechazar `float` y campos desconocidos sin escribir un validador por endpoint. No se elige por rendimiento: no hay benchmark propio que demuestre que sea más rápido que Go o Rust, y el cuello de botella del MVP será la base de datos y las reglas de negocio, no el lenguaje. NestJS es viable, pero obliga a manejar decimales con una librería y añade una capa de decoradores que no compensa para un equipo que ya domina Python. Go y Rust ofrecen más control, pero aumentan el tiempo de iteración y la cantidad de código para el mismo MVP.

**Consecuencias.**

- **Positivas:** OpenAPI casi gratis, validación declarativa, `Decimal` nativo, curva de entrada baja para contribuidores, `uv` acelera instalaciones reproducibles.
- **Negativas:** el tipado es gradual; el GIL limita trabajo CPU intensivo; los errores de `async`/`await` son fáciles de cometer; el ecosistema de frontend no comparte tipos con Python.
- **Mitigaciones:** mypy en CI, Ruff, revisión de código, y tipos TypeScript generados desde OpenAPI para el frontend. Si en el futuro aparece una carga CPU-bound real, se aísla en un servicio aparte; no se reescribe el backend por anticipado.

---

### ADR-002 — Base de datos

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** El sistema maneja montos, impuestos, saldos, numeraciones consecutivas y auditoría. Necesita aritmética exacta, transacciones ACID, bloqueos de fila y restricciones que impidan datos imposibles.

**Opciones consideradas.**

1. **PostgreSQL 16+.** `NUMERIC` exacto, ACID, DDL transaccional, `SELECT … FOR UPDATE`, índices parciales, `JSONB`, Row Level Security.
2. **MySQL 8+.** `DECIMAL` exacto y buen rendimiento general, pero menos herramientas de aislamiento y defensa en profundidad para este caso.
3. **SQLite.** Muy simple para desarrollo, pero un solo escritor y afinidad `NUMERIC` que puede convertir valores a `REAL`/`INTEGER`; no es una base para producción concurrente.

**Decisión.** **PostgreSQL 16 o superior**, con `NUMERIC` para dinero, `TIMESTAMPTZ` para marcas de tiempo, restricciones `CHECK` y transacciones explícitas. La versión exacta se fija en la imagen de Docker Compose.

**Justificación.** No hay un benchmark propio que demuestre superioridad de rendimiento; la decisión es por **capacidades**. PostgreSQL ofrece exactitud decimal, bloqueo de filas, DDL transaccional e índices parciales, que son herramientas directas para numeración, saldos e idempotencia. MySQL también soporta `DECIMAL`, pero PostgreSQL simplifica el aislamiento futuro con RLS y las migraciones. SQLite se descarta para producción porque el MVP tendrá escrituras concurrentes de facturas y pagos; usarlo en tests crearía un entorno distinto al real.

**Consecuencias.**

- **Positivas:** integridad fuerte, transacciones claras, un solo motor para desarrollo y producción, soporte de `NUMERIC`, `JSONB` y bloqueos.
- **Negativas:** hay que operar una base de datos; los tests de integración requieren un contenedor; no se puede usar SQLite como atajo.
- **Mitigaciones:** Docker Compose para desarrollo, testcontainers para CI, backups automáticos y una prueba de restauración periódica. Ninguna consulta de negocio usa SQL crudo sin revisión.

---

### ADR-003 — Framework frontend

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** La API es el producto, pero el MVP necesita una interfaz administrativa usable: crear facturas con varias líneas, editar cantidades y precios, ver totales en vivo, aplicar pagos y consultar cartera. El usuario ya tiene Node y Next.js en su entorno.

**Opciones consideradas.**

1. **Next.js con App Router y TypeScript.** Server Components para lecturas, Client Components para el editor, ecosistema amplio.
2. **SvelteKit.** Menos peso, reactividad simple, buena experiencia de desarrollo.
3. **HTMX + Jinja2 servido por FastAPI.** Un solo runtime, menos JavaScript, despliegue más simple.

**Decisión.** **Next.js + TypeScript** como aplicación separada, consumiendo la API `/api/v1` a través del mismo origen (proxy inverso). Server Components para listados y detalle; Client Components para el editor de factura y la aplicación de pagos. Cliente TypeScript generado desde OpenAPI.

**Justificación.** El editor de factura es la pantalla más compleja del MVP: agregar/quitar líneas, recalcular descuentos e impuestos, validar en vivo y aplicar pagos. Next.js resuelve eso con un ecosistema maduro y con la familiaridad del equipo; SvelteKit también podría hacerlo, pero tiene una comunidad más pequeña para contribuidores open source. HTMX es la opción con menos infraestructura, pero la interacción dinámica del editor terminaría requiriendo JavaScript a medida de todos modos. No se afirma que Next.js sea “más rápido”: se elige por capacidad de interacción y ecosistema.

**Consecuencias.**

- **Positivas:** UI rica, renderizado en servidor para pantallas de solo lectura, ecosistema de componentes y pruebas, separación clara entre API y presentación.
- **Negativas:** dos runtimes (Python y Node), dos builds, riesgo de deriva entre tipos del backend y frontend, más superficie de despliegue.
- **Mitigaciones:** mismo repositorio, Docker Compose, proxy same-origin para evitar CORS, cliente generado desde OpenAPI y pruebas de contrato en CI. Si el equipo prioriza simplicidad operativa por encima de la UI, HTMX sigue siendo una alternativa documentada, no una decisión irreversible.

---

### ADR-004 — ORM y migraciones

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** El backend es Python. Necesitamos mapear agregados financieros, controlar transacciones, aplicar migraciones revisables y evitar que el ORM oculte escrituras peligrosas.

**Opciones consideradas.**

1. **SQLAlchemy 2.0 + Alembic + psycopg 3.** ORM maduro, unit of work explícito, migraciones versionadas, SQL cuando hace falta.
2. **Prisma.** Excelente experiencia en TypeScript, pero no es la opción natural para un backend Python.
3. **Drizzle.** TypeScript-only; misma objeción.
4. **SQL crudo con un migrador simple.** Control total, pero más código repetitivo y más riesgo de inconsistencias.

**Decisión.** **SQLAlchemy 2.0 con sesiones síncronas + Alembic + psycopg 3.** Los casos de uso abren una unidad de trabajo y confirman o revierten explícitamente. Pydantic modela la API; las entidades de dominio no heredan de modelos SQLAlchemy.

**Justificación.** SQLAlchemy permite un mapeo explícito, consultas con `FOR UPDATE`, transacciones claras y separación entre dominio e infraestructura. Se eligen sesiones **síncronas** porque el MVP no tiene una necesidad real de concurrencia masiva y la corrección transaccional es más fácil de razonar y probar; FastAPI ejecuta endpoints síncronos en un threadpool. Prisma y Drizzle obligarían a un backend Node o a una capa artificial. SQL crudo se reserva para reportes o consultas concretas revisadas, no para el CRUD principal.

**Consecuencias.**

- **Positivas:** transacciones explícitas, migraciones versionadas, soporte de `NUMERIC`, pruebas con PostgreSQL real, independencia del dominio respecto al ORM.
- **Negativas:** hay que mapear entre entidades de dominio y modelos de persistencia; el threadpool limita la concurrencia; Alembic exige disciplina y revisión de SQL generado.
- **Mitigaciones:** mapper explícito por agregado, `expire_on_commit=False`, una sesión por request, pruebas de integración con PostgreSQL y revisión obligatoria de migraciones. Si en el futuro dominan las llamadas externas lentas, se evalúa async sin cambiar el dominio.

---

### ADR-005 — Autenticación

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** Hay dos tipos de cliente: la UI web (humana) y las integraciones (máquina a máquina). Necesitamos logout real, revocación, sesiones seguras y una API que no dependa de microservicios.

**Opciones consideradas.**

1. **JWT de acceso + refresh tokens.** Stateless, cómodo para móvil y SSO, pero la revocación y la rotación agregan complejidad.
2. **Sesiones opacas en servidor.** Token aleatorio, almacenado como hash, revocable al instante.
3. **API tokens opacos.** Para integraciones, con scopes y fecha de último uso.
4. **Proveedor externo de identidad.** Útil para SSO empresarial, sobredimensionado para el MVP.

**Decisión.** **Sesiones opacas para la UI + API tokens opacos para integraciones. Sin JWT en el MVP.** Contraseñas con **Argon2id** (RFC 9106); tokens de sesión y API generados con CSPRNG, almacenados como hash; cookie `HttpOnly`, `Secure`, `SameSite=Lax`; CSRF token en mutaciones autenticadas por cookie; rotación de sesión al iniciar sesión y al cambiar privilegios.

**Justificación.** En un monolito, JWT no aporta una ventaja real y sí complica la revocación, el logout y la rotación de claves. Una sesión opaca permite invalidar un usuario o un dispositivo de inmediato. Los API tokens resuelven la automatización sin meter credenciales de usuario en scripts.

**Consecuencias.**

- **Positivas:** revocación inmediata, modelo simple, sin gestión de claves criptográficas para JWT, cookies protegidas contra lectura desde JavaScript.
- **Negativas:** cada request autenticada consulta la base de datos; hay que limpiar sesiones expiradas; la autenticación por cookie exige protección CSRF; escalar horizontalmente requiere una base compartida (ya la tenemos).
- **Mitigaciones:** índice por hash de token, cache de sesión a corto plazo si se mide necesidad, limpieza programada, expiración por inactividad y absoluta, y pruebas de revocación. La UI y la API comparten origen para simplificar cookies.
- **`REQUIERE VALIDACIÓN`:** revisión de seguridad independiente antes de producción y revisión legal de la política de datos y contraseñas. Responsables: security reviewer y abogado.

---

### ADR-006 — Monolito modular vs microservicios

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** FacturaLibre maneja transacciones que cruzan factura, líneas, impuestos, numeración, pago y auditoría. Un error de consistencia entre esos pasos produce documentos duplicados o saldos incorrectos. El equipo es pequeño y el MVP no tiene necesidad demostrada de escalar servicios por separado.

**Opciones consideradas.**

1. **Monolito tradicional en capas.** Simple, pero termina con lógica de facturación dispersa.
2. **Monolito modular.** Un despliegue, módulos con fronteras explícitas y contratos internos.
3. **Microservicios.** Servicios independientes para facturas, pagos, impuestos y numeración, con comunicación por red.

**Decisión.** **Monolito modular**: un backend desplegable, una base de datos, módulos internos (`invoices`, `payments`, `credit_notes`, `taxes`, `contacts`, `items`, `numbering`, `identity`, `audit`) con interfaces públicas y dependencias controladas.

**Justificación.** La facturación exige transacciones ACID que abarcan varios conceptos. En microservicios, esas transacciones se convierten en sagas, compensaciones y consistencia eventual: complejidad que el MVP no necesita y que aumenta el riesgo de duplicados. Un monolito modular permite refactorizar y extraer un módulo más adelante si aparece una razón medida (equipo, carga, despliegue independiente). No se elige por moda ni por rendimiento.

**Consecuencias.**

- **Positivas:** una transacción, un despliegue, debugging simple, menos infraestructura, consistencia fuerte.
- **Negativas:** un solo dominio de fallo; riesgo de acoplamiento si no se respetan las fronteras; escalado vertical y por réplicas del monolito.
- **Mitigaciones:** reglas de importación (`import-linter`), módulos con API pública, pruebas de arquitectura, ADRs para dependencias nuevas y outbox en Fase2 para eventos. La extracción a servicios queda como opción futura, no como objetivo.

---

### ADR-007 — Testing

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** Los errores en dinero, impuestos o estados no se detectan con una prueba feliz. Necesitamos pruebas unitarias del dominio, integración con PostgreSQL real, contrato de API y un E2E que recorra el flujo crítico.

**Opciones consideradas.**

1. **pytest.** Fixtures, parametrización, plugins, integración natural con Hypothesis y testcontainers.
2. **unittest.** Incluido en la biblioteca estándar, pero más verboso y con menos ecosistema.
3. **Solo pruebas E2E.** Detectan regresiones visibles, pero son lentas y no localizan la causa.

**Decisión.** **pytest** como framework principal, con `pytest-cov`, Hypothesis para propiedades, testcontainers para PostgreSQL, `httpx` para la API y Playwright/Vitest para el frontend. Cobertura mínima: **85 % global** y **95 % en los módulos críticos** (`money`, `tax`, `invoice`, `payment`, `numbering`).

**Justificación.** pytest permite organizar pruebas por comportamiento, parametrizar casos y ejecutar property-based testing, que es especialmente útil para totales e invariantes. Los porcentajes son un **piso de ingeniería**, no un benchmark ni una garantía de calidad: cubrir una línea no significa probar el caso. El foco está en invariantes y casos límite.

**Consecuencias.**

- **Positivas:** pruebas legibles, buena localización de fallos, propiedades que atrapan casos no imaginados, integración fiel con PostgreSQL.
- **Negativas:** los tests de integración son más lentos; testcontainers requiere Docker en CI; el E2E puede ser frágil; la cobertura se puede “jugar”.
- **Mitigaciones:** pirámide de pruebas, contenedor reutilizado en local, E2E solo para rutas críticas, y revisión de que las pruebas asserten comportamiento y no solo ejecución. Mutation testing queda como mejora opcional, no como bloqueo del MVP.

**Pruebas obligatorias del MVP.**

- Dominio: redondeo, descuentos, impuestos aditivos, saldo, transiciones de estado.
- Propiedades: `sum(line_totals) == invoice.total`; `total - applied - credited == balance`.
- Integración: numeración concurrente, idempotencia, aislamiento por tenant, `SELECT FOR UPDATE`.
- API: códigos de error, `ETag`/`If-Match`, `Idempotency-Key`, paginación.
- E2E: login → crear factura → emitir → registrar pago → consultar saldo.
- Migraciones: base vacía y base con datos de la versión anterior.

---

### ADR-008 — Estructura de carpetas backend

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** El monolito necesita fronteras claras para no convertirse en un conjunto de controladores gigantes. A la vez, el MVP no justifica la ceremonia completa de DDD con eventos, agregados y capas redundantes.

**Opciones consideradas.**

1. **Organización por capas globales** (`api/`, `services/`, `models/`, `repositories/`). Fácil al inicio, difícil de escalar.
2. **Organización por módulos con capas internas.** Cada contexto tiene su dominio, aplicación, infraestructura y API.
3. **Organización por framework** (todo en `routers/` y `models/`). Rápida, pero acopla el negocio a FastAPI y SQLAlchemy.

**Decisión.** **Módulo primero, capas dentro**, con arquitectura hexagonal ligera:

```text
backend/
  src/facturalibre/
    main.py
    config.py
    shared/
      domain/          # Money, Percentage, errores, ids, reloj
      application/     # UnitOfWork, puertos comunes
      infrastructure/  # DB, logging, seguridad, settings
    modules/
      identity/
        domain/
        application/
        infrastructure/
        api/
      contacts/
      items/
      taxes/
      invoices/
      payments/
      credit_notes/
      numbering/
      audit/
    api/
      v1/
      errors.py
      middleware.py
  migrations/          # Alembic
  tests/
    unit/
    integration/
    api/
    e2e/
```

**Reglas de dependencia.**

- `domain/` no importa FastAPI, SQLAlchemy, Pydantic ni HTTP.
- `application/` orquesta casos de uso y define puertos; no conoce detalles de PostgreSQL.
- `infrastructure/` implementa repositorios, mappers y adaptadores.
- `api/` traduce HTTP a comandos y respuestas; no contiene reglas de negocio.
- `shared/` es un kernel pequeño: dinero, errores, reloj, ids. Si crece, se divide.
- Un módulo no importa `infrastructure/` de otro módulo; solo su API pública de aplicación.

**Justificación.** Las fronteras por módulo permiten entender facturación sin leer todo el sistema y dejan la puerta abierta a extraer un servicio si algún día hace falta. La separación dominio/aplicación/infraestructura hace testeable el cálculo sin base de datos y evita que SQLAlchemy contamine las reglas.

**Consecuencias.**

- **Positivas:** tests de dominio rápidos, bajo acoplamiento, ubicación predecible del código, posibilidad de extracción futura.
- **Negativas:** más archivos y mappers; riesgo de sobreingeniería; requiere disciplina y revisión.
- **Mitigaciones:** CRUD simples pueden ser delgados; no se crean capas vacías; `import-linter` en CI; una guía de “dónde va cada cosa”. La arquitectura se simplifica si una frontera no aporta valor, no se mantiene por dogma.

Las tres decisiones siguientes no son de “stack”, pero condicionan toda la arquitectura: cómo se representa el dinero, cómo se aísla un tenant y cómo se asigna un número fiscal.

---

### ADR-009 — Dinero, precisión y redondeo

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** `float` no representa exactamente decimales; un centavo de diferencia puede invalidar un documento o descuadrar una cartera. La base de datos, la API y el dominio deben hablar el mismo idioma numérico.

**Opciones consideradas.**

1. **`float`/`double`.** Rápido de escribir, inaceptable para dinero.
2. **Enteros en centavos.** Exacto, pero complica precios unitarios fraccionarios, tasas, descuentos porcentuales y multimoneda.
3. **`Decimal` en aplicación + `NUMERIC` en base de datos.** Exacto, explícito y compatible con SQL.

**Decisión.** **`Decimal` + `NUMERIC`**. Precios unitarios y cálculos intermedios con `NUMERIC(19,6)`; montos monetarios con `NUMERIC(19,2)` para COP; tasas con `NUMERIC(7,4)`; tipos de cambio futuros con `NUMERIC(19,8)`. Redondeo `ROUND_HALF_UP` centralizado, por línea, y luego suma de líneas redondeadas. JSON serializa montos como **string**, nunca como número.

**Justificación.** `Decimal` conserva la escala y permite auditar cada paso. Los enteros en centavos son tentadores, pero obligan a definir cuántos decimales tiene un precio unitario y una tasa; en cuanto aparece un porcentaje o una moneda con 3 decimales, el modelo se complica. `NUMERIC` en PostgreSQL garantiza que lo que se guarda es lo que se calculó.

**Consecuencias.**

- **Positivas:** exactitud, reproducibilidad, auditoría, compatibilidad con SQL, sin sorpresas de coma flotante.
- **Negativas:** serialización como string requiere que los clientes no asuman números JSON; algunas librerías de gráficos necesitan conversión; más disciplina en cada cálculo.
- **Mitigaciones:** un único `Money` inmutable, una única función de redondeo, `CHECK` en base de datos, pruebas de propiedad y validación de que ningún esquema acepte `float`.
- **`REQUIERE VALIDACIÓN`:** la regla exacta de redondeo de la DIAN por tipo de documento y versión del anexo técnico. Responsables: contador y experto DIAN.

---

### ADR-010 — Multi-tenencia y aislamiento

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** FacturaLibre puede usarse como instancia autoalojada por una empresa o como servicio con varias empresas. El MVP debe evitar fugas de datos entre tenants sin construir una infraestructura de aislamiento desproporcionada.

**Opciones consideradas.**

1. **Una instancia por tenant.** Aislamiento máximo, operación multiplicada.
2. **Esquema compartido con `tenant_id`.** Simple de migrar y operar; el aislamiento depende del código.
3. **Un esquema por tenant.** Mejor aislamiento lógico, migraciones y conexiones más complejas.
4. **Una base por tenant.** Aislamiento fuerte, costo operativo alto.

**Decisión.** **Esquema compartido con `tenant_id` en todas las tablas de negocio**, filtros obligatorios en repositorios, claves foráneas compuestas que incluyan `tenant_id`, índices que empiecen por `tenant_id` y pruebas automáticas de aislamiento. **Row Level Security (RLS)** se evalúa en Fase2 como defensa en profundidad.

**Justificación.** El esquema compartido mantiene las migraciones y el costo operativo bajo, que es lo que un MVP open source necesita. Las claves compuestas impiden que una línea de factura apunte a una factura de otro tenant. RLS desde el día uno añade complejidad de conexión y pruebas; se pospone, pero no se descarta.

**Consecuencias.**

- **Positivas:** una sola migración, costo bajo, despliegue simple, camino claro a SaaS.
- **Negativas:** un bug de consulta puede filtrar datos; un tenant ruidoso afecta a otros; RLS no está activo en MVP.
- **Mitigaciones:** `TenantContext` obligatorio, repositorios que jamás reciben `tenant_id` desde el cliente, pruebas que fallan si una consulta no filtra, revisión de seguridad y RLS en Fase2.
- **`REQUIERE VALIDACIÓN`:** revisión de seguridad antes de exponer una instancia multi-tenant a internet y revisión legal de privacidad. Responsables: security reviewer y abogado. Si el producto se ofrece como SaaS multi-tenant antes de Fase2, **RLS es un requisito de salida**, no una mejora opcional.

---

### ADR-011 — Numeración y límites transaccionales

**Estado:** Aceptado · **Fecha:** 2026-10-21

**Contexto.** Una factura emitida necesita un número consecutivo sin duplicados ni saltos injustificados. La asignación compite con reintentos de red, emisiones simultáneas y errores a mitad de transacción.

**Opciones consideradas.**

1. **Secuencia de PostgreSQL.** Rápida, pero no transaccional: un rollback deja huecos.
2. **`MAX(numero) + 1`.** Sufre carreras y duplicados bajo concurrencia.
3. **UUID como número visible.** Evita colisiones, pero no cumple una numeración consecutiva legible.
4. **Fila de secuencia bloqueada por tenant/tipo/prefijo.** `SELECT … FOR UPDATE`, incremento y asignación en la misma transacción.

**Decisión.** **Fila de secuencia bloqueada** en `document_sequences`, por tenant, tipo de documento y prefijo. El número se asigna **solo al emitir**, no al crear el borrador, dentro de la misma transacción que cambia el estado a `issued`. Restricción única `(tenant_id, document_type, prefix, number)` y `Idempotency-Key` en la misma frontera transaccional.

**Justificación.** La fila bloqueada serializa solo la emisión de ese tenant, no toda la base. Si la transacción falla, el incremento se revierte y el número no se consume. La restricción única es la última defensa contra un bug de concurrencia. Asignar el número al emitir evita quemar folios en borradores abandonados.

**Consecuencias.**

- **Positivas:** sin duplicados, sin huecos por rollback, trazabilidad fiscal, lógica fácil de probar.
- **Negativas:** la fila de secuencia es un punto de serialización por tenant; un tenant con emisión masiva puede esperar; los rangos autorizados deben gestionarse.
- **Mitigaciones:** transacción corta, sin llamadas externas dentro de ella, índice único y pruebas de emisión concurrente. Si un tenant necesita más throughput, se particiona por prefijo o se evalúa una estrategia específica.
- **`REQUIERE VALIDACIÓN`:** prefijos, rangos, resolución de numeración y contingencia ante la DIAN. Responsables: contador y experto DIAN.

---

## 3. Diagrama de arquitectura

```text
┌─────────────────────┐          ┌─────────────────────┐
│ Navegador           │          │ Cliente API externo │
│ Next.js             │          │ Bearer token opaco  │
└──────────┬──────────┘          └──────────┬──────────┘
           │ HTTPS                          │ HTTPS
           └───────────────┬────────────────┘
                           │
                 ┌─────────▼──────────────────┐
                 │ Caddy / reverse proxy      │
                 │  /        → web:3000       │
                 │  /api/*   → api:8000       │
                 └─────────┬──────────────────┘
                           │
                 ┌─────────▼──────────────────────────────┐
                 │ FastAPI — monolito modular             │
                 │                                        │
                 │  api/v1                                │
                 │   ├─ auth / tenant                     │
                 │   ├─ idempotencia                      │
                 │   ├─ rate limit                        │
                 │   └─ RFC 9457                          │
                 │                                        │
                 │  modules/                              │
                 │   ├─ invoices                          │
                 │   ├─ payments                          │
                 │   ├─ credit_notes                      │
                 │   ├─ taxes                             │
                 │   ├─ contacts / items                  │
                 │   ├─ numbering                         │
                 │   ├─ identity                          │
                 │   └─ audit                             │
                 │                                        │
                 │  application/ use cases                │
                 │  domain/ Money, Invoice                │
                 └─────────┬──────────────────────────────┘
                           │ SQLAlchemy 2 + psycopg 3
                           │ (transacciones, locks)
                 ┌─────────▼──────────────────────────────┐
                 │ PostgreSQL 16+                         │
                 │  NUMERIC · restricciones · índices     │
                 │  únicos · auditoría · idempotencia     │
                 └────────────────────────────────────────┘

Sin Redis, sin Kafka, sin workers, sin Kubernetes en el MVP.
```

**Unidades de despliegue del MVP.**

1. `web`: Next.js.
2. `api`: FastAPI.
3. `db`: PostgreSQL.
4. `proxy`: Caddy con TLS y enrutamiento same-origin.

El **rate limit** del MVP es un *token bucket* por tenant/token, vive en memoria de cada proceso y asume una sola instancia con un solo worker de `api`. Si se despliegan varias réplicas o workers, se mueve a un almacén compartido (PostgreSQL) antes de considerarlo correcto.

**Módulos y responsabilidad.**

| Módulo | Responsabilidad | No hace |
|---|---|---|
| `identity` | Usuarios, tenants, membresías, sesiones, API tokens | Reglas de facturación |
| `contacts` | Clientes/proveedores, datos fiscales | Impuestos |
| `items` | Productos/servicios, precios | Totales de factura |
| `taxes` | Catálogo de impuestos y vigencias | Cálculo de la factura |
| `invoices` | Borrador, líneas, totales, emisión, anulación | Aplicar pagos directamente |
| `payments` | Pagos, aplicaciones, reversas | Crear facturas |
| `credit_notes` | Notas crédito y aplicaciones | Editar facturas |
| `numbering` | Secuencias y asignación de números | Decidir si se emite |
| `audit` | Registro append-only de acciones | Lógica de negocio |
| `shared` | Money, errores, ids, reloj, unit of work | Reglas específicas de un módulo |

**Modelo de datos mínimo (tablas, no columnas).**

- Identidad: `tenants`, `users`, `memberships`, `sessions`, `api_tokens`.
- Maestros: `contacts`, `items`, `taxes`.
- Facturación: `invoices`, `invoice_lines`, `invoice_line_taxes`.
- Cobros: `payments`, `payment_allocations`.
- Correcciones: `credit_notes`, `credit_note_lines`, `credit_note_applications`.
- Numeración: `document_sequences`.
- Soporte: `idempotency_keys` (TTL 24 h), `audit_log`.
- Fase2: `withholdings`, `outbox`, `webhook_subscriptions`, `webhook_deliveries`.

Los identificadores de entidades son **UUID v7** (ordenables por tiempo); las claves de idempotencia son **UUID v4** (aleatorias). Ningún id autoincremental se expone al cliente.

**Reglas de integridad que la base de datos debe hacer cumplir.**

- `(tenant_id, document_type, prefix, number)` único cuando `number` no es nulo.
- `total >= 0`, `balance >= 0` y `amount >= 0`.
- `balance = total - aplicaciones netas - notas crédito` en el MVP, verificado por la aplicación y reconciliado por pruebas. Cuando se activen retenciones (Fase2), la fórmula será `balance = total - notas crédito - retenciones - pagos netos`.
- `payment_allocations` no puede superar el monto del pago ni el saldo de la factura.
- Claves foráneas compuestas con `tenant_id` para impedir referencias cruzadas.
- `version` en agregados mutables para bloqueo optimista.
- `TIMESTAMPTZ` para eventos; `DATE` para fechas de negocio.

---

## 4. Flujo de una petición: “crear factura”

El flujo se divide en **crear borrador** y **emitir**. Son dos transacciones distintas a propósito: un borrador no consume número fiscal.

### 4.1 Crear el borrador

1. **UI.** El usuario completa el editor. Next.js valida la forma para dar feedback inmediato, pero no es la fuente de verdad. Genera un `Idempotency-Key` UUID v4 por intento de envío y lo reutiliza en reintentos.
2. **HTTP.** `POST /api/v1/invoices` con cookie de sesión, token CSRF y cabecera `Idempotency-Key`. El navegador llama al mismo origen; Caddy enruta `/api/*` a FastAPI.
3. **Borde.** FastAPI asigna `request_id`, aplica cabeceras de seguridad, autentica la sesión (hash del token), resuelve el tenant y aplica rate limit. Si el usuario no pertenece al tenant, `403`; si no hay sesión, `401`.
4. **Idempotencia.** Se intenta insertar la clave `(tenant_id, método, ruta, key)` en `idempotency_keys` dentro de la misma transacción del caso de uso. La restricción única resuelve la carrera: si otra petición ya la completó, se devuelve la respuesta guardada; si está en curso, `409`; si el cuerpo cambió, `409`.
5. **Validación.** Pydantic rechaza campos desconocidos, `float` y tipos incorrectos. Valida IDs, fechas, moneda `COP`, cantidades positivas y consistencia básica. Los errores devuelven RFC 9457 con `code` y `field_errors`.
6. **Caso de uso.** `CreateInvoice` abre la unidad de trabajo y carga contacto, ítems e impuestos **con filtro de tenant**, verificando que estén activos y que las referencias existan.
7. **Dominio.** Se construyen las líneas: base bruta, descuento, base gravable, impuestos aditivos, total de línea. `Money` cuantiza con `ROUND_HALF_UP`; se aplican invariantes (`descuento <= base`, `total >= 0`, `suma de líneas == total`). No se toca la base de datos todavía.
8. **Persistencia.** Se guarda la factura como `draft`, `payment_status = unpaid`, `balance = total`, `number = NULL`, con líneas e impuestos. Se registra la acción en `audit_log` (actor, tenant, entidad, acción, después).
9. **Commit.** Se actualiza el registro de idempotencia con el estado HTTP y el cuerpo de respuesta, y se confirma la transacción. Si algo falla, se revierte todo: no queda factura ni clave a medias.
10. **Respuesta.** `201 Created`, `Location: /api/v1/invoices/{id}`, `ETag` con la versión. La UI navega al detalle.

### 4.2 Emitir la factura

1. `POST /api/v1/invoices/{id}/issue` con `Idempotency-Key`; **no** exige `If-Match`, porque es un comando idempotente por estado y no un reemplazo del recurso.
2. Se abre transacción y se bloquea la factura con `SELECT … FOR UPDATE`. Si está `void`, `409`; si ya está `issued`, se devuelve el estado actual sin asignar otro número; si es `draft`, continúa.
3. Se bloquea la fila de `document_sequences` del tenant/tipo/prefijo con `SELECT … FOR UPDATE`, se toma el siguiente número y se incrementa el contador.
4. Se valida que el número esté dentro del rango autorizado (si existe resolución) y se actualiza la factura: `lifecycle_status = issued`, `number`, `issued_at`, `version + 1`.
5. Se registra auditoría y se confirma. La restricción única evita duplicados aunque falle la lógica.
6. Si la transacción falla, el incremento se revierte: el número no se quema.
7. Si la respuesta se pierde y el cliente reintenta, la factura ya está `issued`; la operación devuelve el mismo documento, no crea otro.
8. **Nunca** se llama a un servicio externo (correo, DIAN, webhook) dentro de esta transacción. En Fase2, el evento se escribe en `outbox` y un worker lo publica después del commit.

### 4.3 Por qué crear y emitir están separados

- Un borrador puede abandonarse sin gastar un folio.
- La emisión tiene reglas propias (número, fecha, estado) y puede requerir validaciones adicionales.
- El reintento de emisión es idempotente por estado, no por duplicar el documento.
- La factura emitida es inmutable: se corrige con nota crédito o anulación.

---

## 5. Estrategia de migraciones y versionado de la API

### 5.1 Versionado de la API (`v1`)

- **Versión en la ruta:** `/api/v1`. El prefijo `/api` es de despliegue; la versión de contrato es `v1`. No se versiona por cabecera ni por query param.
- **Contrato:** OpenAPI 3.1 generado por FastAPI, con snapshot comprometido en el repositorio.
- **Cambios aditivos:** campos nuevos opcionales, endpoints nuevos y códigos de error nuevos documentados. Los clientes deben tolerar campos y valores de enum desconocidos.
- **Cambios rupturistas:** renombrar o eliminar campos, cambiar tipos, volver obligatorio un campo opcional, cambiar el significado de un estado o de un cálculo, o cambiar el esquema de autenticación. Van a `/v2`.
- **Deprecación:** mínimo **6 meses** de aviso, con cabeceras `Deprecation` y `Sunset` (RFC 8594), changelog y guía de migración.
- **Compatibilidad:** pruebas de contrato en CI y diff de OpenAPI contra el snapshot. Un cambio rupturista sin `/v2` rompe el build.
- **Formatos estables:** montos como string decimal; fechas de negocio `YYYY-MM-DD`; timestamps RFC 3339; errores `application/problem+json` (RFC 9457, antes 7807); paginación por cursor.
- **Cliente frontend:** tipos generados desde OpenAPI; no se escriben DTOs a mano duplicando el contrato.

**REQUIERE VALIDACIÓN:** la política de compatibilidad y los plazos de deprecación deben confirmarse con los primeros consumidores reales; 6 meses es una decisión de ingeniería, no una obligación legal.

### 5.2 Migraciones de base de datos

- **Herramienta:** Alembic. Una historia lineal, una sola cabeza, revisiones revisadas por una persona.
- **Nunca `create_all` en producción.** El esquema se construye solo con migraciones.
- **Nunca migrar al arrancar la aplicación.** Se ejecuta un job explícito antes del despliegue, con lock para evitar dos migraciones simultáneas.
- **Expand/contract** para cambios compatibles:
  1. agregar tabla/columna nullable o nuevo índice,
  2. desplegar código que escribe/lee de forma compatible,
  3. backfill por lotes,
  4. agregar restricción o `NOT NULL`,
  5. eliminar lo viejo en una release posterior.
- **Sin cambios destructivos en la misma release** que el código que los usa. `DROP` exige backup verificado y ventana.
- **Migraciones de datos** idempotentes, reanudables y en lotes; no bloquean la tabla completa.
- **Rollback:** en producción se prefiere **forward fix**; los `down` se usan en desarrollo. Un rollback de código no revierte datos ya migrados.
- **Pruebas:** migración sobre base vacía y sobre un dump representativo de la versión anterior; restaurar backup en un entorno limpio.
- **Backups:** dump diario y prueba de restauración semanal en el MVP. PITR queda para Fase2 si el volumen lo justifica.

### 5.3 Release y despliegue

1. CI: lint, tipos, tests, migraciones, contrato OpenAPI, build de imágenes.
2. Job de migración contra la base de destino.
3. Despliegue de `api` y `web`.
4. Smoke tests: salud, login, crear borrador, emitir en un tenant de prueba, consultar saldo.
5. Si falla: volver a la imagen anterior y aplicar forward fix; si hubo cambio destructivo, restaurar backup.

**Feature flags** para todo lo fiscal nuevo (por ejemplo, emisión electrónica DIAN). Una bandera apagada debe dejar el sistema en el comportamiento anterior, no a medias.

### 5.4 Observabilidad mínima

- **Logs estructurados en JSON** con `request_id`, `tenant_id`, ruta, estado y latencia. Nunca se registran tokens, contraseñas ni cuerpos completos con datos personales.
- **Salud:** `/health/live` (proceso vivo) y `/health/ready` (base de datos accesible y migraciones al día).
- **Métricas:** requests por ruta/estado, latencia, errores de validación, facturas emitidas, pagos aplicados, replays de idempotencia y fallos de bloqueo.
- **Alertas mínimas:** tasa de error alta, `ready` fallando, errores de emisión y backups fallidos.
- **Trazabilidad:** `request_id` se propaga a logs y a la auditoría; OpenTelemetry queda como opción si aparece la necesidad de trazas distribuidas (no en MVP).

---

## 6. Lo que NO haremos en el MVP

| Excluido | Por qué | Cuándo / fase |
|---|---|---|
| Microservicios | Transacciones distribuidas y operación extra sin necesidad medida. | Solo si un módulo necesita escala o despliegue independiente. |
| Kubernetes / service mesh | Un VPS con Docker Compose cubre el MVP; K8s añade costo cognitivo. | Si hay múltiples entornos y equipos. |
| Event sourcing | La auditoría append-only y el estado actual bastan; reconstruir todo por eventos es complejidad innecesaria. | No está en el roadmap. |
| CQRS | Un solo modelo de lectura/escritura es suficiente; no hay carga que lo justifique. | Si aparecen reportes que compiten con escrituras. |
| Kafka / RabbitMQ | No hay eventos externos en MVP; el outbox de Fase2 usará PostgreSQL. | Fase2, solo si el volumen lo exige. |
| Redis / Celery | Sesiones, idempotencia y limpieza caben en PostgreSQL; no hay workers críticos. | Si se mide una necesidad real. |
| GraphQL / gRPC público | REST + OpenAPI es suficiente y más fácil de consumir. | No está en el roadmap. |
| Multi-región / sharding | El MVP no tiene esa escala. | Fase3 o nunca. |
| Multimoneda | Decisión pospuesta en `DECISIONES.md`; MVP solo COP. | Fase2. |
| Facturación electrónica DIAN (XML, CUFE, firma) | Alto riesgo legal y técnico; requiere validación experta. | Fase2/Fase3 con experto DIAN. |
| Webhooks | No hay consumidores todavía; el polling cubre el MVP. | Fase2. |
| RLS en PostgreSQL | Se mitiga con filtros y pruebas; RLS añade complejidad de conexión. | Fase2, como defensa en profundidad. |
| SSO / MFA | No es necesario para el MVP; añade superficie de autenticación. | Fase2/Fase3. |
| App móvil nativa | La UI web responsive cubre el caso inicial. | Si se valida la demanda. |
| BI / data warehouse | Reportes SQL simples y exportaciones cubren el MVP. | Fase3. |
| IA / blockchain | No resuelven ningún problema del MVP. | No está en el roadmap. |

---

## 7. Riesgos arquitectónicos y mitigaciones

| Riesgo | Impacto | Mitigación | Validación |
|---|---|---|---|
| Reglas fiscales DIAN incorrectas (redondeo, códigos, numeración) | Crítico: documentos rechazados, impuestos mal | Frontera fiscal explícita, casos dorados, feature flag, no emitir electrónicamente en MVP | Contador + experto DIAN |
| Factura duplicada o número repetido por concurrencia | Crítico: inconsistencia fiscal | Idempotencia y numeración en la misma transacción, `FOR UPDATE`, restricción única, pruebas concurrentes | Revisión de código + pruebas |
| Fuga de datos entre tenants | Crítico: incidente de seguridad y legal | `tenant_id` obligatorio, FKs compuestas, tests de aislamiento, RLS Fase2 | Security review |
| Deriva de redondeo entre líneas, totales y pagos | Alto: descuadres silenciosos | `Money` único, `NUMERIC`, redondeo centralizado, pruebas de propiedad y reconciliación | Contador para regla DIAN |
| Pérdida de datos en una migración | Crítico: irrecuperable | Expand/contract, backups, restauración probada, migraciones revisadas | Operaciones |
| Monolito acoplado que se vuelve inmanejable | Medio: velocidad y calidad | Módulos, `import-linter`, API pública interna, ADRs | Revisión de arquitectura |
| Deriva entre API y frontend | Medio: bugs de integración | OpenAPI snapshot, cliente generado, contract tests | CI |
| Robo de sesión o CSRF | Alto: acceso a datos financieros | Cookie segura, CSRF, Argon2id, rotación, rate limit, revocación | Security review |
| Instancia única cae y no hay HA | Alto: indisponibilidad | Healthchecks, reinicio automático, backups, ventana de mantenimiento | Operaciones |
| Scope creep hacia DIAN/multimoneda antes de validar | Alto: MVP no termina | Lista explícita de no-goals, fases y feature flags | Product owner |

**Los tres riesgos que más me preocupan.**

1. **La integridad transaccional del documento fiscal.** Si la numeración, la idempotencia y la aplicación de pagos no comparten la misma frontera, aparecen facturas duplicadas o saltos que no se arreglan con un `UPDATE`.
2. **La fuga entre tenants.** Un filtro olvidado en un repositorio es suficiente. Por eso hay pruebas de aislamiento y RLS está planificado como segunda capa.
3. **La regla fiscal asumida sin experto.** La arquitectura puede ser correcta y el documento igualmente inválido si el redondeo o el código de impuesto no son los que exige la DIAN.

---

## 8. Validaciones pendientes antes de producción

| Tema | Qué falta decidir | Con quién |
|---|---|---|
| Redondeo y base gravable DIAN | Regla exacta por tipo de documento y versión del anexo | Contador + experto DIAN |
| Numeración y resoluciones | Prefijos, rangos, vigencia, contingencia | Contador + experto DIAN |
| Facturación electrónica | XML, CUFE, firma, transmisión, aceptación | Experto DIAN / proveedor autorizado |
| Retenciones | Tarifas, bases, códigos y excepciones | Contador |
| Conservación documental y privacidad | Plazos, soportes, Ley 1581 | Abogado + contador |
| Autenticación y multi-tenencia | Revisión de seguridad, política de sesión y aislamiento | Security reviewer |
| RPO/RTO y backups | Frecuencia, retención y prueba de restauración | Product owner + operaciones |
| Términos y licencia | Responsabilidad, uso del software, datos | Abogado |

---

## 9. Cierre

La arquitectura no es la más moderna: es la que hace que una factura sea **correcta antes que escalable**. Un monolito modular con PostgreSQL, transacciones explícitas y una frontera fiscal clara permite entender, probar y auditar el MVP. Si el proyecto crece, las fronteras ya están dibujadas para extraer lo que haga falta; si no crece, no habremos pagado el costo de una arquitectura distribuida que nunca necesitamos.
