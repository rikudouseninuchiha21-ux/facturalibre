# Frontend — FacturaLibre MVP

Interfaz administrativa mínima para consultar contactos y facturas desde la API
de FacturaLibre.

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
│   │   ├── contacts/page.tsx        # Listado de contactos
│   │   └── invoices/page.tsx        # Listado de facturas
│   ├── components/ui/
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   └── table.tsx
│   └── lib/
│       ├── api.ts                   # Cliente HTTP y tipos de la API
│       └── format.ts                # Formato de moneda
├── Dockerfile
├── next.config.mjs
├── package.json
└── pnpm-lock.yaml
```

Las páginas `/contacts` y `/invoices` son Server Components. Consultan el backend
en cada petición (`cache: "no-store"`), por lo que siempre muestran datos
actuales.

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
puedes verificar las páginas:

```bash
curl -I http://127.0.0.1:3000/contacts
curl -I http://127.0.0.1:3000/invoices
```

Después abre <http://127.0.0.1:3000/contacts> y
<http://127.0.0.1:3000/invoices>.

Si el listado está vacío, crea datos mediante la API; el scaffold no incluye
formularios de creación.

## Calidad

```bash
cd frontend
pnpm lint
pnpm build
```

## Alcance actual

Este scaffold incluye únicamente consultas de lectura. No incluye formularios de
creación o edición, autenticación, estado global ni lógica de negocio. Esas
partes corresponden a fases posteriores.
