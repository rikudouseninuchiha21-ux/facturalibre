# Frontend — FacturaLibre MVP

Interfaz administrativa autenticada con panel analítico para consultar
contactos, ítems, impuestos, facturas, bodegas e inventario, y registrar
contactos, ítems, impuestos, bodegas, empleados, periodos de nómina, movimientos
de stock, facturas en borrador y pagos sobre facturas emitidas desde la API de
FacturaLibre.

## Stack

- Next.js 16 con App Router.
- TypeScript.
- Tailwind CSS 4.
- Recharts 3 para los gráficos del dashboard.
- ESLint.
- `pnpm` 10.
- Node.js 20.9 o superior.

## Estructura

```text
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx               # Header con usuario y logout
│   │   ├── page.tsx                 # Dashboard con KPIs y gráficos
│   │   ├── login/page.tsx           # Inicio de sesión
│   │   ├── register/page.tsx        # Bootstrap del primer administrador
│   │   ├── contacts/page.tsx        # Contactos + formulario
│   │   ├── items/page.tsx           # Ítems + formulario
│   │   ├── taxes/page.tsx           # Impuestos + formulario
│   │   ├── invoices/page.tsx        # Listado de facturas
│   │   ├── invoices/new/page.tsx    # Datos para crear una factura
│   │   ├── warehouses/page.tsx      # Bodegas + formulario
│   │   ├── inventory/page.tsx       # Saldos + formulario de movimientos
│   │   ├── employees/page.tsx       # Empleados + formulario
│   │   └── payroll/page.tsx         # Periodos de nómina
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── RegisterForm.tsx
│   │   │   └── LogoutButton.tsx
│   │   ├── contacts/ContactForm.tsx
│   │   ├── dashboard/SalesChart.tsx
│   │   ├── dashboard/StatusChart.tsx
│   │   ├── inventory/MovementForm.tsx
│   │   ├── invoices/InvoiceActions.tsx
│   │   ├── invoices/InvoiceCreateForm.tsx
│   │   ├── invoices/PaymentForm.tsx
│   │   ├── items/ItemForm.tsx
│   │   ├── taxes/TaxForm.tsx
│   │   ├── warehouses/WarehouseForm.tsx
│   │   └── ui/
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       └── table.tsx
│   ├── lib/
│   │   ├── api.ts                   # Cliente HTTP y tipos de la API
│   │   ├── format.ts                # Formato de moneda y cantidades
│   │   ├── server-auth.ts           # Reenvío de cookie en Server Components
│   │   └── session.ts               # Nombre compartido de la cookie
│   └── middleware.ts                # Protección perimetral de páginas
├── Dockerfile
├── next.config.mjs
├── package.json
└── pnpm-lock.yaml
```

Las páginas de listado son Server Components. Consultan el backend en cada
petición (`cache: "no-store"`), por lo que siempre muestran datos actuales. Los
formularios son Client Components y refrescan la página con `router.refresh()`
después de guardar.

## Autenticación

- El primer usuario se crea en `/register`. El backend solo permite ese bootstrap;
  cuando ya existe un usuario, el registro público responde `403`.
- `/login` crea una sesión opaca de 24 horas. El backend envía la cookie
  `facturalibre_session` con `HttpOnly`, `Secure` y `SameSite=Lax`.
- `src/middleware.ts` redirige a `/login` cualquier página sin cookie. Solo
  `/login` y `/register` son públicas.
- El middleware comprueba presencia, no validez. La sesión real se valida en el
  backend; un endpoint de negocio sin sesión válida responde `401`.
- En el navegador, `src/lib/api.ts` envía `credentials: "include"` en cada
  petición.
- En Server Components no existe un cookie jar. `getSessionCookieHeader()` lee la
  cookie con `next/headers` y `api.ts` la reenvía al backend.
- El header muestra el usuario autenticado y el botón de logout. Logout revoca la
  sesión en la base de datos y elimina la cookie.

> Next.js 16 marca la convención `middleware.ts` como deprecada en favor de
> `proxy.ts`. Se mantiene `middleware.ts` en esta fase; la migración queda
> pendiente.

## Dashboard analítico

`/` es un Server Component que consume `GET /api/v1/dashboard/summary`
reenviando la cookie de sesión. La respuesta se muestra en tres tarjetas KPI:
Ingresos Totales, Facturado Total y Saldo Pendiente.

Debajo aparecen dos gráficos de Recharts: `SalesChart` dibuja las ventas
facturadas de los últimos seis meses con un `BarChart`, y `StatusChart` muestra
la distribución de facturas entre borradores, emitidas y anuladas con un
`PieChart`. Ambos son Client Components y reciben los datos ya agregados como
props; el Server Component conserva el acceso autenticado a la API y el layout
con Tailwind.

## Creación de facturas

`/invoices/new` carga contactos, ítems e impuestos en un Server Component y los
pasa a `InvoiceCreateForm`. El formulario administra las líneas con
`useReducer`; cada línea toma nombre, precio y tasa de impuesto del ítem, aunque
los tres valores siguen siendo editables.

Los importes se calculan con `Number` solo para la vista previa y se redondean a
dos decimales por línea, replicando el backend. Los valores decimales se envían
como strings para no perder precisión. Antes del `POST` se genera una
`Idempotency-Key` UUID v4; se conserva mientras el formulario no cambie para que
un reintento no duplique la factura.

Al guardar, el formulario redirige a `/invoices` y ejecuta `router.refresh()`.
La factura queda en estado `draft` hasta que se emita desde el listado.

## Registro de pagos

En `/invoices`, una factura `issued` con saldo mayor que cero muestra la acción
“Registrar Pago”. El botón abre `PaymentForm`, un modal construido con Tailwind
que presenta el saldo pendiente, propone ese saldo como monto inicial y permite
cambiarlo para registrar un abono parcial. También solicita método de pago
(Efectivo, Transferencia o Tarjeta) y una referencia opcional.

Antes del `POST /api/v1/invoices/{id}/payments` se genera una
`Idempotency-Key` UUID v4. La clave se conserva mientras el formulario no cambie
y se invalida al editar el monto, el método o la referencia. Si el backend
rechaza la operación, por ejemplo con un `422` por sobrepago, el mensaje se
muestra dentro del modal y este permanece abierto para corregir los datos.

Al confirmar correctamente, el modal se cierra, se ejecuta `router.refresh()` y
el listado refleja el nuevo saldo y el estado de pago (`Pendiente`, `Parcial`,
`Pagada` o `Sobrepagada`). El modal también se puede cerrar con `Escape`, con la
X, con Cancelar o haciendo clic en el fondo, salvo mientras la petición está en
curso.

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

Con el frontend y el backend en marcha, una petición sin sesión ya no debe
devolver datos:

```bash
curl -i http://127.0.0.1:3000/api/v1/contacts
# HTTP/1.1 401 Unauthorized
```

Abre <http://127.0.0.1:3000/register> y crea el administrador inicial. Después de
registrarte, el dashboard debe mostrar tu nombre en el header. Las rutas de
negocio ya deben cargar datos:

```bash
curl -I http://127.0.0.1:3000/contacts
# HTTP/1.1 307 Temporary Redirect -> /login (sin cookie)
```

Las páginas disponibles son:

```text
/login
/register
/
/contacts
/items
/taxes
/invoices
/invoices/new
/warehouses
/inventory
/employees
/payroll
```

Después abre <http://127.0.0.1:3000/warehouses> y crea una bodega con código
`PRINCIPAL`. Luego entra a <http://127.0.0.1:3000/inventory> para registrar una
entrada `IN` y comprobar que aparece el saldo. Una salida `OUT` mayor que el
stock disponible debe mostrar el error `Stock insuficiente...` sin modificar la
tabla.

El navegador envía la cookie automáticamente. Para probar los endpoints con
`curl` sobre HTTP local hay que extraer el token del header `Set-Cookie` del
login y enviarlo explícitamente con `-H "Cookie: facturalibre_session=..."`,
porque `curl` no reenvía cookies `Secure` sobre HTTP. En producción el sitio debe
servirse por HTTPS.

Los ítems y los impuestos se administran desde `/items` y `/taxes`. Crea primero
el impuesto si quieres asociarlo a un ítem; el selector del formulario de ítems
se carga con los impuestos activos.

## Calidad

```bash
cd frontend
pnpm lint
pnpm build
```

## Alcance actual

Incluye autenticación con login/logout, bootstrap del primer administrador,
protección de páginas y endpoints, un dashboard con KPIs y gráficos, consultas de
contactos, ítems, impuestos, facturas, bodegas, saldos de inventario, empleados y
nómina; creación de contactos, ítems, impuestos, bodegas, movimientos de stock,
empleados, periodos de nómina y facturas en borrador; y emisión, anulación y
registro de pagos totales o parciales sobre facturas emitidas. No incluye CSRF
explícito, rate limiting, alta administrativa de más usuarios, roles, edición de
bodegas ni notas crédito o devolución de pagos.
