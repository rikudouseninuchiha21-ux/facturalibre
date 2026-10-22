# FacturaLibre

Proyecto educativo y open source para aprender cómo se diseña un sistema de facturación para Colombia. La API y sus decisiones están documentadas en `specs/`; esta etapa monta la infraestructura mínima para empezar a construir.

> **Advertencia:** FacturaLibre es software educativo. No está listo para producción, no garantiza cumplimiento fiscal y no sustituye la validación de un contador, un abogado o un experto DIAN.

## Estado actual

Fase 3b-1: facturas en borrador, emisión y consulta sobre el esquema inicial.

- Backend FastAPI con CRUD de catálogos (`contacts`, `items`, `taxes`) y facturas
  (`invoices`): crear, emitir, consultar y borrar borradores.
- PostgreSQL 16 en Docker, sin puerto expuesto al host.
- Backend accesible solo en `127.0.0.1:8000` para desarrollo.
- Ocho tablas de dominio y su primera migración de Alembic.
- Frontend todavía no scaffolded; solo existe `frontend/README.md`.
- Sin pagos, anulación ni notas crédito todavía.

## Requisitos

- Docker Engine con Docker Compose v2.
- `uv` para ejecutar el backend fuera de Docker.
- `pnpm` para el frontend, cuando se cree en la siguiente fase.
- Python 3.12+ solo si corres el backend localmente.

## Arranque rápido

```bash
cp .env.example .env
# Edita .env y cambia POSTGRES_PASSWORD por una contraseña local.
docker compose up --build
```

Cuando ambos servicios estén sanos:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

La base de datos **no** está publicada en el host: solo el backend puede hablar con ella dentro de la red de Compose.

Para aplicar el esquema de datos:

```bash
docker compose exec backend alembic upgrade head
```

Para ver logs:

```bash
docker compose logs -f backend
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

Las pruebas de `/health` no necesitan base de datos. Las pruebas de esquema y de
CRUD y facturas usan `TEST_DATABASE_URL` contra un PostgreSQL real; consulta
`backend/README.md`.

## Calidad de código

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app
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
│   ├── README.md
│   └── .gitkeep
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
- El frontend se creará con `create-next-app` en un sub-paso posterior.
