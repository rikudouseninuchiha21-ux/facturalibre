# FacturaLibre

Proyecto educativo y open source para aprender cómo se diseña un sistema de facturación para Colombia. La API y sus decisiones están documentadas en `specs/`; esta etapa monta la infraestructura mínima para empezar a construir.

> **Advertencia:** FacturaLibre es software educativo. No está listo para producción, no garantiza cumplimiento fiscal y no sustituye la validación de un contador, un abogado o un experto DIAN.

## Estado actual

Fase 4C-1: scaffold del frontend.

- Backend FastAPI con CRUD de catálogos (`contacts`, `items`, `taxes`), facturas
  (`invoices`) y pagos (`payments`): crear, emitir, consultar, anular y borrar
  borradores con soft delete; registrar, listar y eliminar pagos con idempotencia.
- PostgreSQL 16 en Docker, sin puerto expuesto al host.
- Backend accesible solo en `127.0.0.1:8000` para desarrollo.
- Ocho tablas de dominio y migraciones de Alembic.
- Frontend Next.js 16 con App Router, TypeScript, Tailwind CSS y `pnpm`.
  Incluye dashboard, listado de contactos y listado de facturas.
- Sin formularios, autenticación ni estado global en el frontend todavía.
- Sin notas crédito ni devolución de pagos todavía.

## Requisitos

- Docker Engine con Docker Compose v2.
- `uv` para ejecutar el backend fuera de Docker.
- `pnpm` 10 y Node.js 20.9+ para ejecutar el frontend fuera de Docker.
- Python 3.12+ solo si corres el backend localmente.

## Arranque rápido

```bash
cp .env.example .env
# Edita .env y cambia POSTGRES_PASSWORD por una contraseña local.
docker compose up --build
```

Cuando los servicios estén sanos:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}

curl -I http://127.0.0.1:3000/
# HTTP/1.1 200 OK
```

El frontend queda disponible en <http://127.0.0.1:3000>. El rewrite de Next.js
reenvía `/api/v1/*` al backend, así que el navegador no necesita CORS.

La base de datos **no** está publicada en el host: solo el backend puede hablar con ella dentro de la red de Compose.

Para aplicar el esquema de datos:

```bash
docker compose exec backend alembic upgrade head
```

Para ver logs:

```bash
docker compose logs -f backend frontend
```

Para detener:

```bash
docker compose down
```

Para borrar también los datos locales (⚠️ irreversible):

```bash
docker compose down -v
```

## Pruebas

```bash
cd backend
uv sync
uv run pytest
```

Las pruebas de `/health` no necesitan base de datos. Las pruebas de esquema, CRUD,
facturas y pagos usan `TEST_DATABASE_URL` contra un PostgreSQL real; consulta
`backend/README.md`.

## Calidad de código

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

Frontend:

```bash
cd frontend
pnpm lint
pnpm build
```

## Estructura

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/config.py
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/v1/
│   ├── tests/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/ui/
│   │   └── lib/
│   ├── Dockerfile
│   ├── next.config.mjs
│   ├── package.json
│   └── README.md
├── specs/
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## Documentación

- `specs/ESPECIFICACION-FUNCIONAL.md`: análisis de la API pública de referencia.
- `specs/DECISIONES.md`: decisiones propias de FacturaLibre.
- `specs/ARQUITECTURA.md`: arquitectura técnica del MVP.

## Notas

- La contraseña de `.env.example` es un marcador, no una credencial real.
- El backend lee `DATABASE_URL` desde el entorno; Docker Compose la construye con las variables `POSTGRES_*`.
- El `Dockerfile` instala `uv` sin fijar versión todavía; se fijará antes de producción.
- No hay `uv.lock` en esta etapa; se genera al ejecutar `uv sync` y conviene commitearlo.
- El frontend usa `BACKEND_INTERNAL_URL` para el rewrite y los Server Components;
  en Docker Compose vale `http://backend:8000`.
