# Backend — FacturaLibre

Backend del MVP: FastAPI, SQLAlchemy 2, Alembic y PostgreSQL 16. En esta etapa
existe `GET /health`, el esquema de datos inicial, los CRUD de catálogos maestros
(`contacts`, `items`, `taxes`), la creación/emisión/anulación de facturas y los
pagos sobre facturas emitidas. **Todavía no hay notas crédito ni pagos
multi-factura.**

## Requisitos

- Python 3.12 o superior.
- `uv` instalado.
- Docker y Docker Compose (para la base de datos y el despliegue local).
- PostgreSQL 16 para ejecutar migraciones y pruebas de esquema.

## Primera ejecución

En un checkout nuevo **no hace falta ejecutar Alembic a mano**. Desde la raíz del
repositorio:

```bash
cp .env.example .env
# Edita .env y cambia POSTGRES_PASSWORD
docker compose up --build
```

Al arrancar el backend, `entrypoint.sh` hace lo siguiente:

1. Espera a que PostgreSQL acepte conexiones (máximo 30 segundos).
2. Ejecuta `/app/.venv/bin/alembic upgrade head`.
3. Inicia Uvicorn con el `CMD` de la imagen.

El proceso es idempotente: si la base ya está migrada, Alembic no aplica nada. Si
la migración falla, el contenedor se detiene con un error en vez de arrancar una
API sin tablas.

El backend queda en `http://127.0.0.1:8000` y la base de datos **no** se expone al
host.

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

Para comprobar que las migraciones se aplicaron:

```bash
docker compose logs backend
docker compose exec backend alembic current
```

## Desarrollo local con recarga automática

El repositorio incluye `docker-compose.override.yml` en la raíz. Docker Compose
lo fusiona automáticamente cuando se ejecuta `docker compose` sin `-f`, así que
el backend de desarrollo:

- Monta `./backend/app` en `/app/app` y `./backend/tests` en `/app/tests`.
- Ejecuta Uvicorn con `--reload` y `--reload-dir /app/app`.
- Conserva el entrypoint: PostgreSQL se espera y Alembic migra antes de arrancar.

Después del primer build, los cambios en `backend/app/` se recargan solos. No
hace falta reconstruir la imagen ni reiniciar el contenedor:

```bash
# Primera vez o después de cambiar Dockerfile/pyproject.toml
docker compose up -d --build

# Día a día: el código se recarga automáticamente
docker compose up -d
docker compose logs -f backend
```

Para comprobar la recarga sin editar código, en otra terminal:

```bash
touch backend/app/main.py
```

En los logs del backend debe aparecer un mensaje de `WatchFiles detected changes`
seguido de `Reloading...`.

Los cambios en dependencias (`backend/pyproject.toml`), en el `Dockerfile` o en
`entrypoint.sh` sí requieren `docker compose up -d --build`, porque viven dentro
de la imagen y no en los volúmenes de desarrollo.

Para volver al modo producción, sin recarga automática y sin los volúmenes de
desarrollo, se ignora explícitamente el override:

```bash
docker compose -f docker-compose.yml up -d --build
```

Para verificar la configuración fusionada:

```bash
docker compose config
```

El bloque `backend` debe mostrar el comando con `--reload` y los dos volúmenes
`bind` hacia `backend/app` y `backend/tests`.

## Endpoints de catálogos

Base local: `http://127.0.0.1:8000/api/v1`.

Los listados aceptan `?limit=20&offset=0`; `limit` debe estar entre 1 y 100. Las
respuestas de listado son un arreglo JSON. Los `DELETE` son *soft delete*: la fila
permanece en la base con `deleted_at`, pero deja de aparecer y responde `404`.
Las actualizaciones usan `PATCH` y requieren la `version` actual; si no coincide,
responden `409`. Los errores de validación responden `422`. En los ejemplos,
reemplaza `$CONTACT_ID`, `$ITEM_ID` y `$TAX_ID` por los ids devueltos al crear.

### Contactos

```bash
BASE=http://127.0.0.1:8000/api/v1

# Crear
curl -s -X POST "$BASE/contacts" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Cliente Uno","email":"cliente1@example.com","tax_id":"900123456"}'

# Listar con paginación
curl -s "$BASE/contacts?limit=20&offset=0"

# Obtener uno (reemplaza CONTACT_ID por el id devuelto al crear)
curl -s "$BASE/contacts/$CONTACT_ID"

# Actualizar; version debe ser la versión actual
curl -s -X PATCH "$BASE/contacts/$CONTACT_ID" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Cliente Actualizado","version":1}'

# Soft delete
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE "$BASE/contacts/$CONTACT_ID"
```

### Ítems

```bash
# Crear; tax_id es opcional. Usa el id de un impuesto si quieres asociarlo.
curl -s -X POST "$BASE/items" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Producto Uno","description":"Producto de prueba","unit_price":"1250.50","tax_id":null}'

# Listar
curl -s "$BASE/items?limit=20&offset=0"

# Obtener
curl -s "$BASE/items/$ITEM_ID"

# Actualizar
curl -s -X PATCH "$BASE/items/$ITEM_ID" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Producto Actualizado","unit_price":"999.99","version":1}'

# Soft delete
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE "$BASE/items/$ITEM_ID"
```

### Impuestos

```bash
# Crear; rate es un porcentaje entre 0 y 100 con hasta 4 decimales
curl -s -X POST "$BASE/taxes" \
  -H 'Content-Type: application/json' \
  -d '{"name":"IVA 19 %","rate":"19.0000"}'

# Listar
curl -s "$BASE/taxes?limit=20&offset=0"

# Obtener
curl -s "$BASE/taxes/$TAX_ID"

# Actualizar
curl -s -X PATCH "$BASE/taxes/$TAX_ID" \
  -H 'Content-Type: application/json' \
  -d '{"name":"IVA actualizado","rate":"19.5000","version":1}'

# Soft delete
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE "$BASE/taxes/$TAX_ID"
```

## Endpoints de facturas

Crear una factura requiere el header `Idempotency-Key` con un UUID. La misma Key
con el mismo body devuelve la respuesta original y no duplica la factura; con un
body distinto responde `409`. Las facturas nacen en `draft`/`unpaid`, sin número,
y solo se numeran al emitirlas con `POST /invoices/{id}/issue`.

```bash
# IDs creados en los ejemplos de contactos/ítems/impuestos
IDEMPOTENCY_KEY=$(python -c 'import uuid; print(uuid.uuid4())')

# Crear factura con 2 líneas. Si no se envía tax_rate, se usa el del ítem.
curl -s -X POST "$BASE/invoices" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d "{
    \"contact_id\": \"$CONTACT_ID\",
    \"issue_date\": \"2026-10-21\",
    \"due_date\": \"2026-11-20\",
    \"currency\": \"COP\",
    \"lines\": [
      {
        \"item_id\": \"$ITEM_ID\",
        \"quantity\": \"3\",
        \"unit_price\": \"10.10\",
        \"discount_percent\": \"10\"
      },
      {
        \"item_id\": \"$ITEM_ID\",
        \"description\": \"Línea con IVA explícito\",
        \"quantity\": \"2.5\",
        \"unit_price\": \"19.99\",
        \"discount_percent\": \"0\",
        \"tax_rate\": \"19\"
      }
    ]
  }"

# Emitir: asigna FV00000001, FV00000002, etc.
# Reemplaza INVOICE_ID por el id devuelto al crear la factura.
curl -s -X POST "$BASE/invoices/$INVOICE_ID/issue"

# Anular una factura emitida que no tenga pagos. El motivo es obligatorio
# (1 a 500 caracteres). Si tiene pagos responde 409: no hay devolución en el MVP.
curl -s -X POST "$BASE/invoices/$INVOICE_ID/void" \
  -H 'Content-Type: application/json' \
  -d '{"reason":"Error en monto"}'

# Consultar una factura con sus líneas
curl -s "$BASE/invoices/$INVOICE_ID"

# Listar con paginación
curl -s "$BASE/invoices?limit=20&offset=0"

# Borrar: solo funciona si sigue en draft; si está emitida responde 409
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE "$BASE/invoices/$INVOICE_ID"
```

## Endpoints de pagos

Los pagos solo se aceptan sobre facturas `issued`. El `POST` requiere el header
`Idempotency-Key` con un UUID: la misma Key con el mismo body devuelve el pago
original sin duplicarlo; con otro body responde `409`. El monto debe ser mayor
que cero, tener máximo dos decimales, no superar el saldo de la factura y usar
una fecha de pago no futura. Un sobrepago responde `422` y una factura que no
está emitida responde `409`.

Cada pago actualiza el saldo, el `payment_status`, la `version` y el
`updated_at` de la factura en la misma transacción. Eliminar un pago vuelve a
calcular esos valores y responde `404` si el pago ya no existe.

```bash
# Pagar una factura emitida. Reemplaza INVOICE_ID por el id de la factura.
PAYMENT_KEY=$(python -c 'import uuid; print(uuid.uuid4())')

curl -s -X POST "$BASE/invoices/$INVOICE_ID/payments" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $PAYMENT_KEY" \
  -d '{
    "amount": "50.00",
    "payment_date": "2026-10-21",
    "method": "transfer",
    "reference": "TRX-001"
  }'

# Listar pagos por fecha descendente, con paginación
curl -s "$BASE/invoices/$INVOICE_ID/payments?limit=20&offset=0"

# Eliminar un pago (hard delete); vuelve a calcular saldo y estado
# Reemplaza PAYMENT_ID por el id devuelto al crear el pago.
curl -s -o /dev/null -w '%{http_code}\n' \
  -X DELETE "$BASE/invoices/$INVOICE_ID/payments/$PAYMENT_ID"
```

Ejemplo numérico: una factura con total `119.00` que recibe un pago de `50.00`
queda con balance `69.00` y `payment_status` en `partially_paid`.

## Ejecutar solo el backend con uv

Necesitas una instancia de PostgreSQL accesible. La URL se lee de `DATABASE_URL`
(en `.env` o en el entorno). Alembic usa la misma variable; no hay credenciales
hardcodeadas en `alembic.ini`.

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Si corres fuera de Docker, `DATABASE_URL` debe apuntar a `localhost`, no al
servicio `db`. El archivo `.env.example` ya trae ese ejemplo.

## Migraciones

Ejecuta siempre desde `backend/`:

```bash
cd backend
uv run alembic upgrade head          # aplica todas las migraciones pendientes
uv run alembic current               # muestra la revisión aplicada
uv run alembic history --verbose     # historial de revisiones
```

Para crear una migración nueva después de cambiar los modelos:

```bash
uv run alembic revision --autogenerate -m "descripcion breve"
```

Revisa siempre el archivo generado antes de aplicarlo. Para revertir:

```bash
uv run alembic downgrade -1          # revierte la última migración
uv run alembic downgrade base        # vuelve a un esquema vacío
uv run alembic upgrade head          # vuelve a aplicar todo
```

La migración inicial crea las tablas `contacts`, `items`, `taxes`, `invoices`,
`invoice_lines`, `payments`, `number_sequences` e `idempotency_keys`, además de
los tipos ENUM de estado de factura. La migración `20261021_0002` añade
`voided_reason` y `voided_at` a `invoices`; su `downgrade` elimina ambas columnas.

### Base de datos de test

`tests/test_schema.py`, los tests CRUD, los tests de facturas y los tests de pagos
requieren una base PostgreSQL real y **separada** de la de desarrollo. La variable
`TEST_DATABASE_URL` no se lee de `.env`: se pasa por el entorno. Un ejemplo con
un contenedor temporal, sin tocar `docker-compose.yml`:

```bash
docker run --rm -d --name facturalibre-test-db \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=facturalibre_test \
  -p 127.0.0.1:55432:5432 \
  postgres:16-alpine

cd backend
export TEST_DATABASE_URL=postgresql+psycopg://test:test@127.0.0.1:55432/facturalibre_test
export DATABASE_URL="$TEST_DATABASE_URL"
uv run alembic upgrade head
uv run pytest
uv run pytest tests/test_schema.py

docker stop facturalibre-test-db
```

Si `TEST_DATABASE_URL` no está definida, las pruebas que necesitan PostgreSQL se
omiten. Las pruebas de `/health` no necesitan base de datos. Cada test CRUD corre
en una transacción externa que se revierte al terminar, sin dejar datos de prueba.

## Calidad

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

## Estructura

```text
backend/
  alembic.ini                  # configuración de Alembic; la URL viene de DATABASE_URL
  app/
    main.py                    # FastAPI + /health
    core/config.py             # variables de entorno con pydantic-settings
    domain/
      models/                  # Contact, Item, Tax, Invoice, InvoiceLine, Payment,
                               # NumberSequence e IdempotencyKey
      *_repository.py           # consultas y updates con SQLAlchemy 2
      calculations.py           # redondeo, totales y estado de pago
      exceptions.py            # errores de recurso ausente, versión y estado
    application/
      *_schemas.py             # schemas Pydantic v2 de catálogos, facturas y pagos
    infrastructure/
      database.py              # engine, SessionLocal, Base y get_db()
      migrations/              # env.py, plantilla y versiones de Alembic
    api/v1/
      contacts.py              # CRUD de contactos
      items.py                 # CRUD de ítems
      taxes.py                 # CRUD de impuestos
      invoices.py              # crear, emitir, anular, consultar y borrar borradores
      payments.py              # pagos sobre facturas emitidas
  tests/
    conftest.py                # PostgreSQL de test y sesión transaccional
    test_health.py             # smoke test de /health
    test_schema.py             # tablas, estados y tipos NUMERIC contra PostgreSQL
    test_contacts.py           # CRUD y optimistic locking de contactos
    test_items.py              # CRUD y optimistic locking de ítems
    test_taxes.py              # CRUD y optimistic locking de impuestos
    test_invoices.py           # cálculos, idempotencia, numeración y estados
    test_payments.py           # pagos, saldos, idempotencia y borrado
  Dockerfile
  entrypoint.sh                # espera PostgreSQL, migra y cede el control al CMD
  pyproject.toml
```

## Notas

- No hay `uv.lock` en esta etapa. Al ejecutar `uv sync` se genera; conviene
  commitearlo para builds reproducibles.
- El `Dockerfile` usa `uv` sin versión fijada todavía; antes de producción se
  debe fijar versión o digest.
- Las migraciones se ejecutan automáticamente al arrancar el contenedor mediante
  `entrypoint.sh`; no es necesario ejecutar `alembic upgrade head` a mano.
- El esquema es de una sola instancia/tenant en esta fase. La multi-tenencia y
  la emisión electrónica DIAN (CUFE/CUDE/firma) quedan fuera de este paso.
