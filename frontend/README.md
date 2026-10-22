# Frontend — FacturaLibre MVP

Interfaz administrativa para consultar contactos, facturas, bodegas e inventario,
y registrar contactos, bodegas y movimientos de stock desde la API de
FacturaLibre.

## Stack

- Next.js 16 con App Router.
- TypeScript.
- Tailwind CSS 4.
- ESLint.
- `pnpm` 10.
- Node.js 20.9 o superior.

## Estructura

```text
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                 # Dashboard
│   │   ├── contacts/page.tsx        # Contactos + formulario
│   │   ├── invoices/page.tsx        # Listado de facturas
│   │   ├── warehouses/page.tsx      # Bodegas + formulario
│   │   └── inventory/page.tsx       # Saldos + formulario de movimientos
│   ├── components/
│   │   ├── contacts/ContactForm.tsx
│   │   ├── inventory/MovementForm.tsx
│   │   ├── invoices/InvoiceActions.tsx
│   │   ├── warehouses/WarehouseForm.tsx
│   │   └── ui/
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       └── table.tsx
│   └── lib/
│       ├── api.ts                   # Cliente HTTP y tipos de la API
│       └── format.ts                # Formato de moneda y cantidades
├── Dockerfile
├── next.config.mjs
├── package.json
└── pnpm-lock.yaml
```

Las páginas de listado son Server Components. Consultan el backend en cada
petición (`cache: "no-store"`), por lo que siempre muestran datos actuales. Los
formularios son Client Components y refrescan la página con `router.refresh()`
después de guardar.

## Arranque con Docker

Desde la raíz del repositorio:

```bash
docker compose up --build
```

Docker Compose carga automáticamente `docker-compose.override.yml`, que usa la
etapa `dev` del Dockerfile, monta `./frontend/src` y ejecuta `pnpm dev` con
hot-reload.

Abre <http://127.0.0.1:3000>.

Para ver los logs del frontend:

```bash
docker compose logs -f frontend
```

Los cambios en `src/` se recargan automáticamente. Si cambias `package.json`,
`next.config.mjs` o el Dockerfile, reconstruye:

```bash
docker compose up --build
```

### Modo producción con Docker

Para usar la imagen final sin el override de desarrollo:

```bash
docker compose -f docker-compose.yml up --build -d
```

En este modo, `BACKEND_INTERNAL_URL` se pasa como argumento de build y como
variable de entorno al contenedor con el valor `http://backend:8000`.

## Arranque local con pnpm

Requisitos: Node.js 20.9+ y pnpm 10.

```bash
cd frontend
pnpm install
pnpm dev
```

El backend debe estar disponible en `http://127.0.0.1:8000`. Si está en otra URL:

```bash
BACKEND_INTERNAL_URL=http://127.0.0.1:8000 pnpm dev
```

Para una compilación local de producción:

```bash
pnpm build
pnpm start
```

## Proxy y CORS

El backend no configura CORS y no es necesario para este scaffold:

- **Navegador:** las peticiones usan rutas relativas como
  `/api/v1/contacts`. Next.js las reenvía al backend mediante el rewrite de
  `next.config.mjs`, por lo que son same-origin.
- **Server Components:** `src/lib/api.ts` llama directamente al backend usando
  `BACKEND_INTERNAL_URL`, porque `fetch` en Node no acepta una URL relativa.
- **Docker:** el valor correcto es `http://backend:8000`, no
  `http://127.0.0.1:8000` (esa dirección apuntaría al propio contenedor del
  frontend).

El rewrite conserva la ruta completa:

```text
/api/:path*  ->  ${BACKEND_INTERNAL_URL}/api/:path*
```

## Verificar la conexión con el backend

Con el frontend y el backend en marcha:

```bash
curl -i http://127.0.0.1:3000/api/v1/contacts
```

La respuesta debe ser `HTTP/1.1 200 OK` y un arreglo JSON de contactos. También
puedes verificar las páginas y los endpoints de inventario:

```bash
curl -I http://127.0.0.1:3000/contacts
curl -I http://127.0.0.1:3000/invoices
curl -I http://127.0.0.1:3000/warehouses
curl -I http://127.0.0.1:3000/inventory
curl -s http://127.0.0.1:3000/api/v1/warehouses
curl -s http://127.0.0.1:3000/api/v1/inventory/balances
```

Después abre <http://127.0.0.1:3000/warehouses> y crea una bodega con código
`PRINCIPAL`. Luego entra a <http://127.0.0.1:3000/inventory> para registrar una
entrada `IN` y comprobar que aparece el saldo. Una salida `OUT` mayor que el
stock disponible debe mostrar el error `Stock insuficiente...` sin modificar la
tabla.

Si no hay ítems disponibles, créalos mediante `POST /api/v1/items`; el frontend
actual no incluye formulario de ítems.

## Calidad

```bash
cd frontend
pnpm lint
pnpm build
```

## Alcance actual

Incluye consultas de contactos, facturas, bodegas y saldos de inventario;
creación de contactos y bodegas; emisión y anulación de facturas; y registro de
movimientos de stock `IN`/`OUT`. No incluye autenticación, estado global ni
formularios de ítems, impuestos o edición de bodegas.
