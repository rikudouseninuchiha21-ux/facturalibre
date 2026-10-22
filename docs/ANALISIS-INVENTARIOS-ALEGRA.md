# Análisis de UX y flujo del módulo de inventarios de Alegra

> **Proyecto:** FacturaLibre (proyecto educativo)
> **Objeto observado:** sitio público y centro de ayuda públicos de Alegra
> **Fecha de observación:** 2026-10-22
> **Naturaleza:** análisis de experiencia de usuario y flujo funcional. No se copió código ni se accedió a la aplicación autenticada.

---

## 0. Resumen ejecutivo

- Alegra presenta el inventario como un **inventario permanente en tiempo real**, integrado con facturación, punto de venta y contabilidad; no como una lista aislada de existencias. **[VISTO: F1]**
- La navegación principal vive en el módulo `Inventario`, con submódulos para ítems de venta, valor de inventario, ajustes, gestión de ítems, listas de precios, bodegas, categorías y atributos. **[VISTO: capturas públicas de F2, F4, F5, F6 y F7]**
- La creación de productos usa **divulgación progresiva**: un formulario básico en modal y un enlace explícito a `Ir al formulario avanzado`. El tipo de ítem se elige al inicio y queda bloqueado después. **[VISTO: F2 y captura de F2]**
- El listado de productos es una **tabla operativa**: selector de lista de precios, búsqueda, filtros, selección múltiple, acciones por fila, paginación y estados. **[VISTO: capturas públicas de F2]**
- La multi-bodega es de primer nivel: maestro de bodegas, existencias por ubicación, transferencias con origen/destino y documentos de venta que exigen seleccionar bodega. **[VISTO: F4 y captura de F4]**
- El stock no se edita “a mano” en el producto: se mueve mediante **documentos** (venta, compra, ajuste, transferencia). El ajuste de inventario separa aumentos y disminuciones y usa costo promedio ponderado. **[VISTO: F5]**
- Las **alertas de stock mínimo/máximo** se prometen y existen como campos del producto, pero no se localizó la pantalla de configuración, el centro de notificaciones ni la regla exacta de disparo. **[VISTO: promesa y campo; DESCONOCIDO: UI y reglas]**
- Para FacturaLibre, la lección arquitectónica más importante es separar **movimientos de stock**, **saldos por bodega** y **valorización**, en lugar de guardar una única cantidad mutable en el producto.

---

## 1. Alcance, método y convenciones

### 1.1 Qué se hizo

- Se consultó la landing pública vigente de inventarios de Alegra Colombia: `https://www.alegra.com/colombia/inventarios/`. La variante `/colombia/inventario/` devuelve 404. **[VISTO: proceso realizado]**
- Se usaron las técnicas de reconocimiento de la skill **leanrea**: peticiones HTTP de lectura, renderizado con navegador headless, inspección del DOM público y revisión de los activos visuales publicados por Alegra. **[VISTO: proceso realizado]**
- Se complementó la landing con artículos públicos del centro de ayuda de Alegra, porque allí se documentan rutas, formularios y capturas/GIF de la interfaz. **[VISTO: F2–F10]**
- Se revisaron capturas y GIF públicos de la aplicación. Esas imágenes se tratan como **evidencia visual observada en documentación pública**, no como ejecución en vivo de una cuenta autenticada. **[VISTO: activos visuales de F2, F4, F5, F6, F7 y F9]**
- No se inició sesión, no se creó una cuenta, no se usaron credenciales y no se accedió a paneles privados. **[VISTO: proceso realizado]**
- No se copió código fuente ni se reutilizaron componentes. El objetivo fue reconstruir flujos y patrones de UX. **[VISTO: proceso realizado]**

### 1.2 Qué no se hizo

- No se probó el comportamiento real de la aplicación autenticada.
- No se verificaron permisos, roles, límites de plan, concurrencia, latencia ni tiempos de respuesta.
- No se analizó el frontend privado, el backend, la base de datos ni el tráfico de red de Alegra.
- No se validaron las promesas comerciales con una cuenta de prueba.
- No se estudiaron todos los módulos de Alegra: el foco es inventario y su relación con ventas y contabilidad.

### 1.3 Leyenda de evidencia

| Marca | Significado |
|---|---|
| **[VISTO]** | Aparece literalmente en una página pública, en una captura o en un GIF publicado por Alegra. |
| **[INFERIDO]** | Se deduce de la evidencia, pero la fuente no lo afirma de forma explícita. |
| **[DESCONOCIDO]** | No se pudo confirmar con las fuentes públicas. No se inventa un valor ni una regla. |

Cuando una tabla mezcla niveles, la columna **Evidencia** lo indica fila por fila.

### 1.4 Fuentes principales

| ID | URL | Uso en este informe |
|---|---|---|
| F1 | https://www.alegra.com/colombia/inventarios/ | Landing comercial, beneficios, FAQ y activos visuales |
| F2 | https://ayuda.alegra.com/col/crea-productos-y-servicios | Tipos de ítem, creación, listado, edición, importación y exportación |
| F3 | https://ayuda.alegra.com/col/como-importar-tus-productos-y-servicios-a-alegra | Flujo detallado de importación masiva e historial |
| F4 | https://ayuda.alegra.com/col/gestionar-inventario-en-diferentes-bodegas | Bodegas y transferencias entre bodegas |
| F4b | https://ayuda.alegra.com/int/gestiona-tu-inventario-en-diferentes-bodegas-almacenes-dep%C3%B3sitos | Variante internacional: nomenclatura y campos locales de bodega |
| F5 | https://ayuda.alegra.com/col/ajustes-de-inventario-alegra | Ajustes, promedio ponderado y campos del documento |
| F6 | https://ayuda.alegra.com/col/clasificar-productos-de-venta-por-categorias | Categorías y acciones de gestión |
| F7 | https://ayuda.alegra.com/col/crea-listas-de-precios | Listas de precios y asociación a productos, clientes y facturas |
| F8 | https://ayuda.alegra.com/col/crea-productos-combinados-combos-y-kits | Combos y kits |
| F9 | https://ayuda.alegra.com/col/reporte-ventas-por-bodega | Reporte de ventas por bodega |
| F10 | https://ayuda.alegra.com/col/gestionar-inventarios | Caso de uso integral: productos, bodegas, venta y reportes |
| F11 | https://ayuda.alegra.com/col/alegra-contabilidad#inventario | Índice de artículos de inventario |

> Las URLs del centro de ayuda pueden cambiar de slug o redirigir a la variante internacional (`/int/...`). Se citan las versiones consultadas el 2026-10-22.

### 1.5 Activos visuales citados

| ID | Activo público | Qué muestra |
|---|---|---|
| V1 | https://cdn-websites.alegra.com/international/funcionalidades-lp/hero/hero-img-inventarios-2.webp | Hero con selector “Inventario”, ficha de producto y KPIs de stock, costo y unidades |
| V2 | https://cdn-websites.alegra.com/international/funcionalidades-lp/columnas-con-timer-imagenes/funcionalidades-crear-lista.webp | Lista de precios con ítems, sugerencias y acciones |
| V3 | https://cdn-websites.alegra.com/international/funcionalidades-lp/columnas-con-timer-imagenes/funcionalidades-conciliar-inventarios.webp | Importar nuevos, actualización masiva y conciliación de inventario |
| V4 | https://cdn-websites.alegra.com/colombia/funcionalidades-lp/columnas-con-timer-imagenes/funcionalidades-manejo-bodegas.webp | Valor de bodega, categorías y detalle de movimientos |
| V5 | https://ayuda.alegra.com/hs-fs/hubfs/BUSCAR%20%C3%8DTEMS%20COL.gif?width=670&height=377&name=BUSCAR%20%C3%8DTEMS%20COL.gif | Listado de ítems y selector de lista de precios |
| V6 | https://ayuda.alegra.com/hs-fs/hubfs/NUEVO%20%C3%8DTEM%20COL.gif?width=670&height=377&name=NUEVO%20%C3%8DTEM%20COL.gif | Formulario básico de producto |
| V7 | https://ayuda.alegra.com/hs-fs/hubfs/EDITAR%20%C3%8DTEMS%20COL.gif?width=670&height=377&name=EDITAR%20%C3%8DTEMS%20COL.gif | Acciones por fila y paginación |
| V8 | https://ayuda.alegra.com/hs-fs/hubfs/BODEGA.gif | Creación y detalle de una bodega |
| V9 | https://ayuda.alegra.com/hs-fs/hubfs/BODEGA%202.gif | Formulario de transferencia entre bodegas |
| V10 | https://ayuda.alegra.com/hs-fs/hubfs/AJ.gif | Formulario de ajuste de inventario |
| V11 | https://ayuda.alegra.com/hs-fs/hubfs/CATEGOR%C3%8DAS_I.gif | Formulario de categoría |
| V12 | https://ayuda.alegra.com/hs-fs/hubfs/VENTAS%20POR%20BODEGAS.gif | Reporte de ventas por bodega |
| V13 | https://ayuda.alegra.com/hs-fs/hubfs/KITS.gif | Constructor de combos/kits |

---

## 2. Funcionalidades que Alegra promociona

### 2.1 Promesas centrales de la landing

| Capacidad promocionada | Texto o idea observada | Evidencia |
|---|---|---|
| Inventario en tiempo real | “Con cada venta, su inventario se actualiza en tiempo real.” | **[VISTO: F1]** |
| Control integral | “Visualice las unidades, costos, utilidades y el valor de sus productos.” | **[VISTO: F1]** |
| Productos y servicios | Crear productos o servicios e importarlos masivamente; editarlos después. | **[VISTO: F1]** |
| Valor del stock | Consultar el valor total del inventario en tiempo real, con costos y cantidades actuales. | **[VISTO: F1]** |
| Listas de precios | Crear y editar listas para distintos segmentos; crear promociones masivas. | **[VISTO: F1]** |
| Multi-bodega | Gestionar almacenes desde una sola plataforma, añadir, editar y transferir productos. | **[VISTO: F1]** |
| Integración contable | Cada movimiento de compra y venta actualiza inventario y contabilidad. | **[VISTO: F1]** |
| Variantes | “Cree productos o servicios con las variantes necesarias.” | **[VISTO: F1]** |
| Cantidades negativas | “Configure artículos y cantidades de venta en negativo.” | **[VISTO: F1]** |
| Alertas | “Reciba alertas ante productos sin existencias.” | **[VISTO: F1]** |
| Almacenes múltiples | “Gestione la cantidad de almacenes que necesite.” | **[VISTO: F1]** |
| Descuentos | Descuentos por ítem o mediante listas de precios. | **[VISTO: F1]** |
| Importación/exportación | Importar y exportar SKUs de forma masiva en Excel. | **[VISTO: F1]** |
| Combos/kits | Crear combos de productos para ahorrar tiempo. | **[VISTO: F1]** |

### 2.2 Promesas de la FAQ

La FAQ de la landing refuerza el modelo de inventario permanente y agrega matices útiles:

- Un buen software de inventario debe permitir control en tiempo real, registrar entradas y salidas, manejar múltiples bodegas, **recibir alertas de stock bajo** y tener reportes claros. **[VISTO: F1]**
- Alegra “alerta cuando el inventario está bajo”, registra cada movimiento y entrega reportes para decidir. **[VISTO: F1]**
- El sistema permanente registra cada movimiento de stock: entradas, salidas y movimientos internos. **[VISTO: F1]**
- La propuesta incluye stock inicial, actualización en tiempo real e integración con punto de venta. **[VISTO: F1]**

### 2.3 Diferencia importante: “sin existencias” vs. “stock bajo”

- La landing habla de alertas ante **productos sin existencias**. **[VISTO: F1]**
- La FAQ habla de **stock bajo** y de **stock mínimo/máximo** como campos del producto. **[VISTO: F1, F2]**
- No se observó si son la misma alerta, si hay dos umbrales distintos ni cuál es el canal de notificación. **[DESCONOCIDO]**

> **Lectura para FacturaLibre:** conviene modelar dos conceptos separados: `agotado` (cantidad ≤ 0) y `bajo mínimo` (cantidad ≤ stock_min). La UI puede mostrar ambos con severidad distinta.

---

## 3. Arquitectura de navegación observada

### 3.1 Árbol del módulo

La barra lateral pública muestra esta estructura:

```text
Inventario
├── Ítems de venta
├── Valor de inventario
├── Ajustes de inventario
├── Gestión de ítems
├── Listas de precios
├── Bodegas
├── Categorías
└── Atributos
```

**[VISTO: capturas públicas de F2, F4, F5, F6 y F7]**

Además, la navegación general incluye `Ingresos`, `Gastos`, `Contactos`, `Bancos`, `Contabilidad`, `Reportes`, `Configuración` y, en algunas capturas, `Producción` en estado Beta. **[VISTO: capturas públicas]**

### 3.2 Rutas por tarea

| Tarea | Ruta observada | Evidencia |
|---|---|---|
| Crear producto | `Inventario > Ítems de venta > + Nuevo producto de venta` | **[VISTO: F2]** |
| Crear producto desde una factura | `Ingresos > Facturas de venta > Nueva factura > Nuevo ítem` | **[VISTO: F2]** |
| Ver y filtrar productos | `Inventario > Ítems de venta` | **[VISTO: F2]** |
| Editar/desactivar/eliminar producto | `Inventario > Ítems de venta > acciones de la fila` | **[VISTO: F2, V7]** |
| Crear bodega | `Inventario > Bodegas > Nueva bodega` | **[VISTO: F4]** |
| Transferir entre bodegas | `Inventario > Bodegas > Transferencia de bodegas > Nueva transferencia` | **[VISTO: F4]** |
| Ajustar inventario | `Inventario > Ajustes de inventario > Nuevo ajuste` | **[VISTO: F5]** |
| Crear categoría | `Inventario > Categorías > Nueva categoría` | **[VISTO: F6]** |
| Crear categoría desde producto | `Inventario > Ítems de venta > Nuevo ítem > Ir al formulario avanzado > Categoría > Nueva categoría` | **[VISTO: F6]** |
| Crear lista de precios | `Inventario > Listas de precios > + Nueva lista de precios` | **[VISTO: F7]** |
| Asociar lista a producto | `Inventario > Ítems de venta > Editar > Lista de precios > Agregar lista de precio` | **[VISTO: F7]** |
| Asociar lista a cliente | `Contactos > Clientes > Editar > Información comercial > Lista de precios` | **[VISTO: F7]** |
| Importar productos | `Inventario > Ítems de venta > Más acciones > Importar` o `Inventario > Gestión de ítems > Importar nuevos > Importar ítems` | **[VISTO: F2, F3]** |
| Exportar inventario | `Inventario > Ítems de venta > Más opciones > Exportar` | **[VISTO: F2]** |
| Retomar importación | `Inventario > Ítems de venta > Más acciones > Historial de importaciones > Retomar proceso` | **[VISTO: F3]** |
| Reporte de ventas por bodega | `Reportes > Ventas > Ventas por bodega` | **[VISTO: F9]** |

### 3.3 Lectura de la arquitectura

- **Inventario es un módulo de datos maestros y movimientos**, no solo un reporte. Contiene ítems, bodegas, categorías, listas de precios, ajustes y herramientas de carga. **[INFERIDO: estructura de navegación observada]**
- **Las ventas viven fuera de Inventario**, en `Ingresos > Facturas de venta`, pero consumen el stock y obligan a seleccionar bodega. **[VISTO: F4, F10]**
- **La contabilidad también vive fuera**, en `Contabilidad`, aunque el movimiento de inventario genera asientos. **[VISTO: F1; INFERIDO: integración entre módulos]**
- **“Gestión de ítems” e “Ítems de venta”** aparecen como etiquetas relacionadas; la primera se usa para importación y la segunda para el CRUD. **[VISTO: F2, F3]** No se observó si son la misma pantalla con distinto nombre o dos entradas distintas. **[DESCONOCIDO]**
- La documentación internacional usa `Bodegas, Almacenes o Depósitos` para el mismo concepto. **[VISTO: F4b]** Es una variante de nomenclatura, no necesariamente un módulo distinto.
- Algunas capturas muestran etiquetas antiguas como `Operaciones de stock`, `Precios` y `Valor de inventario` en otra disposición. **[VISTO: V13]** Eso sugiere evolución de la interfaz entre versiones. Las rutas textuales de los artículos se toman como la referencia más reciente. **[INFERIDO: deriva de versiones]**

---

## 4. Listado de productos

### 4.1 Estructura observada

La pantalla `Ítems de venta` se organiza así:

```text
Ítems de venta
Crea, edita y administra cada detalle de tus ítems de venta.  [Ver más]
                                             [Más acciones v]  [+ Nuevo producto de venta]

Lista de precios
[ General v ]

[ Buscar... ]                                  [ Filtrar ]

[ ] Nombre             Referencia   Precio    Descripción            Acciones
[ ] 1- Tornillo        rrr02        3.500     rrr                    👁  ✏️  ⏻  🗑
[ ] 3- Martillo madera 3-MARMAD    7.800     Martillo de madera...  👁  ✏️  ⏻  🗑
...
Resultados por página: [10 v]   1-10 de 144   Página [1] de 15
```

**[VISTO: V5, V7]**

### 4.2 Elementos y comportamiento

| Elemento | Lo observado | Lectura UX | Evidencia |
|---|---|---|---|
| Título y descripción | `Ítems de venta` con texto breve y enlace `Ver más` | Explica el propósito sin saturar | **[VISTO: V5]** |
| CTA principal | Botón teal `+ Nuevo producto de venta` | Una sola acción primaria clara | **[VISTO: V5]** |
| Acciones globales | Menú `Más acciones` | Agrupa importar, exportar y otras acciones secundarias | **[VISTO: V5, F2]** |
| Contexto de precios | Selector `Lista de precios` con opción `General` y varias listas | El listado se lee “a través” de una lista de precios | **[VISTO: V5]** |
| Búsqueda | Campo `Buscar...` | Búsqueda global del módulo | **[VISTO: V5]** |
| Filtros | Botón `Filtrar`, chips de filtros y `Remover filtros` | Filtros visibles y reversibles | **[VISTO: V5, V7]** |
| Selección | Checkbox por fila y checkbox de cabecera | Permite acciones masivas | **[VISTO: V7]** |
| Columnas | `Nombre`, `Referencia`, `Precio`, `Descripción`, `Acciones` | Tabla compacta, orientada a operación | **[VISTO: V7]** |
| Acciones por fila | Ojo, lápiz, interruptor y papelera | Detalles, editar, activar/desactivar, eliminar | **[VISTO: V7]** |
| Tooltip | `Desactivar` al pasar sobre el interruptor | Aclara acciones ambiguas | **[VISTO: V7]** |
| Paginación | `Resultados por página: 10`, `1-10 de 144`, `Página 1 de 15` | Controla volumen sin perder contexto | **[VISTO: V7]** |

### 4.3 Reglas de gestión observadas

- `Detalles` muestra la información del ítem. **[VISTO: F2]**
- `Editar` permite cambiar la información. **[VISTO: F2]**
- `Desactivar` deja de usar el ítem sin eliminarlo. **[VISTO: F2]**
- `Eliminar` borra definitivamente, pero **se deshabilita si el ítem tiene movimientos asociados**. **[VISTO: F2]**
- Se pueden seleccionar varios ítems para desactivar o eliminar en lote. **[VISTO: F2]**
- Antes de desactivar un producto inventariable, la cantidad disponible debe ser cero; si no, se debe hacer un ajuste. **[VISTO: F2]**
- El estado del ítem se refleja en un control tipo interruptor y en filtros de estado. **[VISTO: V7]**

### 4.4 Lo que no se pudo confirmar

- El contenido exacto de la pantalla `Detalles` de un producto. **[DESCONOCIDO]**
- Si el listado permite ordenar por todas las columnas o solo por algunas. **[DESCONOCIDO]**
- Si la búsqueda cubre nombre, referencia, descripción y código de barras, o solo algunos campos. **[DESCONOCIDO]**
- Si el listado cambia cuando el producto tiene variantes, lotes o múltiples bodegas. **[DESCONOCIDO]**
- Si el precio mostrado es el de la lista seleccionada o el precio base. **[INFERIDO: probablemente el de la lista seleccionada, por el selector de contexto; no confirmado]**

### 4.5 Implicación para FacturaLibre

El listado debe ser una **tabla de trabajo**, no una galería de tarjetas. Para un ERP pequeño, la densidad y la rapidez importan más que el artificio visual. Patrones a reproducir:

- CTA primaria única.
- Búsqueda siempre visible.
- Filtros por estado, categoría y bodega.
- Selección múltiple con barra de acciones contextual.
- Acciones por fila con iconos conocidos y tooltips.
- Paginación con tamaño de página configurable.
- Estado vacío que explique cómo crear el primer ítem o importarlo.

---

## 5. Detalle y edición de producto

### 5.1 Formulario básico

La captura pública muestra un modal titulado `Formulario básico de productos`:

```text
Tipo de ítem *      [ Producto ] [ Servicio ] [ Combo ]
                    Una vez creado, no podrás cambiar el tipo ni su condición variable.

Nombre *
Bodega *            [ Principal v ]     Unidad de medida *   [ Unidad v ]
Cantidad inicial *                       Costo por unidad *
Precio base *       Impuesto *           Precio Total *
[ Campos adicionales obligatorios ]
[ Ir al formulario avanzado ]            [ Cancelar ] [ Crear producto ]
```

**[VISTO: V6]**

| Campo | Propósito | Evidencia |
|---|---|---|
| Tipo de ítem | Producto, Servicio o Combo; se elige al crear | **[VISTO: V6]** |
| Nombre | Identificación del ítem | **[VISTO: V6]** |
| Bodega | Ubicación inicial del stock | **[VISTO: V6]** |
| Unidad de medida | Unidad, caja, kg, etc. | **[VISTO: V6]** |
| Cantidad inicial | Stock de apertura | **[VISTO: V6]** |
| Costo por unidad | Costo inicial para valorización | **[VISTO: V6]** |
| Precio base | Precio antes de impuestos | **[VISTO: V6]** |
| Impuesto | Impuesto aplicable | **[VISTO: V6]** |
| Precio Total | Precio con impuesto | **[VISTO: V6]** |
| Campos adicionales obligatorios | Aviso de completeness | **[VISTO: V6]** |
| Ir al formulario avanzado | Divulgación progresiva | **[VISTO: V6]** |

### 5.2 Tipos de ítem

| Tipo | Comportamiento documentado | Evidencia |
|---|---|---|
| Inventariable | Controla cantidades y costos (Kárdex), stock mínimo/máximo, variantes, reportes de valor de inventario y rentabilidad, y cuentas contables de ingresos, inventario y costo de venta. | **[VISTO: F2, F3]** |
| No inventariable | No maneja cantidades ni costos; no aparece en reportes de inventario; solo afecta cuentas de ingresos. | **[VISTO: F2, F3]** |
| Servicio | Intangible; se comporta como no inventariable. | **[VISTO: F2, F3]** |
| Combo/kit | Se crea como no inventariable, pero descuenta los componentes inventariables al vender. | **[VISTO: F8]** |

Reglas adicionales:

- No se puede convertir un producto inventariable en no inventariable, ni viceversa, si ya tiene movimientos. La recomendación es desactivarlo y crear uno nuevo. **[VISTO: F2, F3]**
- Excepción: un producto no inventariable que aún no está vinculado a documentos sí podría convertirse en inventariable. **[VISTO: F3]**
- Los combos pueden incluir ítems con variantes. **[VISTO: F8]**
- El costo promedio de un combo es la suma del costo promedio de sus componentes inventariables. **[VISTO: F8]**
- Una vez que un combo está asociado a documentos, no se pueden cambiar sus componentes. **[VISTO: F8]**

### 5.3 Formulario avanzado

La documentación indica que el formulario avanzado permite agregar más detalles. **[VISTO: F2]**

A partir de los artículos y capturas se pueden asociar a ese formulario, como mínimo:

- Categoría, incluida la creación de una nueva categoría sin salir del formulario. **[VISTO: F6]**
- Listas de precios. **[VISTO: F7]**
- Variantes/atributos. **[VISTO: F1, F2]** La UI exacta del constructor de variantes no se observó. **[DESCONOCIDO]**
- Cuentas contables de ingresos, inventario y costo de venta. **[VISTO: F2, F3]**
- Stock mínimo y máximo. **[VISTO: F2]**

No se observó el orden exacto de las secciones, el conjunto completo de campos ni las validaciones del formulario avanzado. **[DESCONOCIDO]**

### 5.4 Detalle del producto

- La acción `Detalles` existe en el listado. **[VISTO: F2, V7]**
- No se capturó la pantalla de detalle de un producto. **[DESCONOCIDO]**
- Por analogía con el detalle de bodega —que muestra estado, campos, acciones e ítems asociados— es razonable esperar una vista de resumen con información maestra, stock, movimientos y documentos. **[INFERIDO]** No debe presentarse como observado.

### 5.5 Implicación para FacturaLibre

- El formulario básico debe resolver el 80 % de los casos: tipo, nombre, referencia/SKU, unidad, bodega, cantidad inicial, costo, precio e impuesto.
- El formulario avanzado debe agrupar categoría, variantes, listas de precios, cuentas contables y umbrales de stock.
- El tipo de ítem debe elegirse con consecuencias visibles; si es inmutable después de crear, la UI debe explicarlo antes de guardar.
- Evitar un formulario único gigantesco. La divulgación progresiva reduce fricción y errores.

---

## 6. Stock en tiempo real y valorización

### 6.1 Cómo se comunica el “tiempo real”

La landing y el caso de uso lo describen en tres niveles:

1. **Venta → actualización automática:** “Con cada venta, su inventario se actualiza en tiempo real.” **[VISTO: F1]**
2. **Factura → actualización automática:** “Alegra actualiza inventario automáticamente cada vez que creas una factura.” **[VISTO: F10]**
3. **Consulta antes de vender:** el sistema muestra existencias exactas por bodega antes de facturar. **[VISTO: F10]**

El mecanismo técnico —eventos, colas, polling, websockets, transacciones— no se observó. **[DESCONOCIDO]**

### 6.2 Evidencia visual del hero

La imagen principal muestra:

- Un selector de contexto `Inventario`.
- Una ficha de producto con imagen, cantidad `Cant. 251` y valor `$17,576,012`.
- Tres KPIs: `Stock 235.000 (+3.80%)`, `Costo 235.000 (+4.20%)` y `Unidades 225.380 (+1.80%)`.
- Una sensación de dashboard operativo, no de formulario contable.

**[VISTO: V1]**

> Es una pieza de marketing: los valores son ilustrativos. No deben interpretarse como datos reales de una cuenta ni como el diseño exacto de la pantalla autenticada. **[INFERIDO: naturaleza promocional del activo]**

### 6.3 Valorización y costo promedio

El artículo de ajustes describe el método:

- Alegra usa **promedio ponderado** para valuar el inventario. **[VISTO: F5]**
- El costo se actualiza automáticamente cuando se compra a precios diferentes. **[VISTO: F5]**
- Ejemplo documentado: 10 unidades a $100.000 + 10 unidades a $120.000 = $2.200.000 / 20 = $110.000 por unidad. **[VISTO: F5]**
- En un aumento, el sistema pide el costo unitario de lo que entra para recalcular el promedio. **[VISTO: F5]**
- En una disminución, aplica el costo promedio actual y desaconseja modificarlo. **[VISTO: F5]**

### 6.4 El ajuste como documento de stock

El formulario de ajuste muestra estas columnas:

```text
Bodega *        Fecha *
Centro de costo  Numeración *
Observaciones

Ítems de venta
[ Item ] [ Cantidad actual ] [ Tipo de ajuste ] [ Cantidad ] [ Costo promedio ]
[ Cantidad final ] [ Cantidad final hoy ] [ Total ajustado ]
[ + Agregar producto ]                         [ Desde un archivo o imagen ]
```

**[VISTO: V10, F5]**

Campos clave:

| Campo | Significado | Evidencia |
|---|---|---|
| `Cantidad actual` | Unidades registradas antes del ajuste | **[VISTO: F5]** |
| `Tipo de ajuste` | Incremento o disminución | **[VISTO: F5]** |
| `Cantidad` | Unidades a sumar o restar | **[VISTO: F5]** |
| `Costo promedio` | Costo unitario según promedio ponderado | **[VISTO: F5]** |
| `Cantidad final` | Proyección después del ajuste | **[VISTO: F5]** |
| `Cantidad final hoy` | Stock resultante en tiempo real después del movimiento | **[VISTO: F5]** |
| `Total ajustado` | Valor monetario que se mueve contablemente | **[VISTO: F5]** |

Acciones sobre ajustes guardados: `Ver detalle`, `Editar`, `Eliminar`. **[VISTO: F5]**
Se pueden ajustar varios productos en un mismo documento con `Agregar producto`. **[VISTO: F5]**

### 6.5 Vista de bodega y movimientos

La imagen de gestión de bodegas muestra:

- `Valor estimado de bodega $2.896.300 COP`.
- Gráfico de dona `Categorías en la bodega`.
- Tabla `Detalle de movimientos` con `Bodega de origen`, `Fecha` y `Observaciones`.

**[VISTO: V4]**

Esto sugiere que la bodega no es solo un filtro: tiene **valorización propia, composición por categoría y trazabilidad de movimientos**. **[INFERIDO: a partir de la captura]**

### 6.6 Modelo mental inferido

La evidencia pública encaja con este flujo:

```text
Documento (venta, compra, ajuste, transferencia)
        ↓
Movimiento de stock (entrada/salida, item, bodega, cantidad, costo)
        ↓
Saldo por bodega y saldo consolidado
        ↓
Valorización (costo promedio, valor del inventario)
        ↓
Reportes y asientos contables
```

**[INFERIDO: patrón consistente con F1, F4, F5, F9 y F10]**

### 6.7 Lo que no se pudo confirmar

- Latencia real de la actualización. **[DESCONOCIDO]**
- Si la actualización es inmediata al guardar la factura o al emitirla. **[DESCONOCIDO]**
- Si una factura en borrador reserva stock o solo lo descuenta al emitirse. **[DESCONOCIDO]**
- Si se permite vender sin stock y cómo se comporta el sistema. **[DESCONOCIDO]**
- Si el costo promedio es global o por bodega. **[DESCONOCIDO]**
- Si hay bloqueo optimista o resolución de conflictos en ventas concurrentes. **[DESCONOCIDO]**
- Si existe un Kárdex visual con saldo anterior, movimiento y saldo posterior. **[DESCONOCIDO]**

### 6.8 Implicación para FacturaLibre

- **No guardar el stock como un campo editable del producto.** Guardar movimientos y derivar saldos.
- Mantener una tabla de saldos por `item_id + warehouse_id` para consultas rápidas, pero reconstruible desde el libro de movimientos.
- Hacer que cada movimiento tenga `source_type`, `source_id`, `source_line_id` y una clave de idempotencia.
- Definir explícitamente la política de costeo antes de implementar: promedio ponderado global o por bodega. La fuente pública no resuelve esa decisión. **[DESCONOCIDO]**
- Mostrar siempre el stock en el contexto correcto: por bodega, consolidado y con desglose de movimientos.

---

## 7. Multi-bodega y transferencias

### 7.1 Creación de bodega

Ruta: `Inventario > Bodegas > Nueva bodega`. **[VISTO: F4]**

Formulario observado:

```text
Nueva bodega
Nombre *
Dirección
Centro de costo
Observaciones

[ Cancelar ] [ Guardar ]
```

**[VISTO: V8, F4]**

Campos documentados:

| Campo | Uso | Evidencia |
|---|---|---|
| `Nombre` | Identificación de la bodega | **[VISTO: F4, V8]** |
| `Dirección` | Ubicación física | **[VISTO: F4, V8]** |
| `Centro de costo` | Asociación contable/analítica | **[VISTO: F4, V8]** |
| `Observaciones` | Notas internas | **[VISTO: F4, V8]** |
| `Código SUNAT` | Solo para Perú | **[VISTO: F4b]** |

### 7.2 Detalle de bodega

La captura muestra una vista de detalle con:

- Nombre de la bodega como título.
- Estado `Activo` / `Desactivado`.
- Acciones `Editar` y `Eliminar`.
- Campos `Nombre`, `Observaciones`, `Dirección`, `Centro de costo`.
- Sección `Ítems asociados` con filtro y tabla de `Nombre`, `Referencia`, `Precio`, `Descripción`, `Acciones`.
- Toast `Éxito / Operación exitosa`.

**[VISTO: V8]**

### 7.3 Transferencias

La opción de transferencias aparece cuando hay más de una bodega. **[VISTO: F4]**

Ruta: `Inventario > Bodegas > Transferencia de bodegas > Nueva transferencia entre bodegas`. **[VISTO: F4]**

Formulario observado:

```text
Nueva transferencia entre bodegas
Bodega origen *        Bodega destino *
Fecha *                Observaciones

Ítems de venta
[ Item ] [ Referencia ] [ Cantidad actual ] [ Cantidad a transferir ]
[ + Agregar ítem ]                         Total transferido: 0
[ Cancelar ] [ Guardar ]
```

**[VISTO: V9, F4]**

| Elemento | Comportamiento | Evidencia |
|---|---|---|
| `Bodega origen` | Descuenta stock de la bodega seleccionada | **[VISTO: F4]** |
| `Bodega destino` | Incrementa stock de la bodega seleccionada | **[VISTO: F4]** |
| `Fecha` | Fecha efectiva del traslado | **[VISTO: V9]** |
| `Observaciones` | Motivo o nota del traslado | **[VISTO: V9]** |
| `Cantidad actual` | Stock disponible en origen | **[VISTO: V9]** |
| `Cantidad a transferir` | Unidades que se moverán | **[VISTO: V9]** |
| `Total transferido` | Suma de unidades del documento | **[VISTO: V9]** |

### 7.4 Reglas documentadas

- Al crear facturas, cotizaciones o remisiones, se debe seleccionar la bodega que contiene los productos. **[VISTO: F4]**
- En Alegra POS, los productos se descuentan de la bodega configurada para la terminal. **[VISTO: F4]**
- Una bodega se puede editar, deshabilitar o eliminar desde la barra de acciones, siempre que no tenga movimientos asociados. **[VISTO: F4]**
- El reporte de ventas por bodega usa la bodega de despacho, no el origen histórico del stock: si un producto se trasladó, aparece en la bodega desde donde se facturó. **[VISTO: F9]**

### 7.5 Lo que no se pudo confirmar

- Si una transferencia genera numeración propia. **[DESCONOCIDO]**
- Si se puede transferir parcialmente y dejar pendiente. **[DESCONOCIDO]**
- Si requiere aprobación o flujo de dos pasos. **[DESCONOCIDO]**
- Si el costo se mueve con la transferencia y cómo se recalcula por bodega. **[DESCONOCIDO]**
- Si se permite transferir más que la cantidad disponible. **[DESCONOCIDO]**
- Si hay reservas de stock en documentos no emitidos. **[DESCONOCIDO]**
- Si la bodega tiene capacidad, zona o ubicación interna. **[DESCONOCIDO]**

### 7.6 Implicación para FacturaLibre

- La transferencia debe ser **atómica**: una salida en origen y una entrada en destino, con el mismo `transfer_id`.
- Todos los movimientos deben llevar `warehouse_id`; el saldo consolidado se calcula sumando bodegas.
- La selección de bodega debe estar presente en facturas, cotizaciones y notas de venta, no escondida en configuración.
- El POS o punto de venta debe tener una bodega por defecto, configurable por terminal.
- La baja de una bodega debe impedirse si tiene movimientos; usar desactivación lógica.
- Definir si el costeo es por bodega o global. Si se transfiere costo, la decisión afecta transferencias y reportes.

---

## 8. Listas de precios, categorías, atributos y combos

### 8.1 Listas de precios

Ruta: `Inventario > Listas de precios > + Nueva lista de precios`. **[VISTO: F7]**

Flujo documentado:

1. Crear la lista.
2. Asociarla a productos desde `Editar > Lista de precios > Agregar lista de precio`.
3. Asociarla a clientes desde `Contactos > Clientes > Editar > Información comercial > Lista de precios`.
4. Elegirla en la factura de venta.

**[VISTO: F7]**

Reglas:

- Los productos se asocian por defecto a la lista general. **[VISTO: F7]**
- Para usar otras listas, primero se crean y luego se asocian a productos o clientes. **[VISTO: F7]**
- También se pueden agregar listas al importar productos o mediante actualización masiva. **[VISTO: F7]**
- En la factura se puede seleccionar una lista distinta a la del cliente. **[VISTO: F7]**

La imagen promocional muestra una interfaz con:

- Pestañas `Items` y `Sugerencias`.
- Buscador y filtro.
- Columnas `Nombre` y `Referencia`.
- Acción `+` para agregar.
- Menú de acciones `Editar`, `Duplicar`, `Agregar items`, `Eliminar`.
- Toast de éxito al crear la lista.

**[VISTO: V2]**

**Lectura UX:** la lista de precios es una entidad de primera clase, no un campo de texto en el producto. El listado de productos cambia de contexto según la lista seleccionada. **[VISTO: V5, F7]**

### 8.2 Categorías

Ruta: `Inventario > Categorías > Nueva categoría`. **[VISTO: F6]**

Formulario observado:

```text
Nueva categoría
Nombre
Descripción
[ Imagen de la categoría ]
[ Cancelar ] [ Guardar categoría ]
```

**[VISTO: V11, F6]**

Acciones: `Ver detalle`, `Editar`, `Desactivar`, `Eliminar`. **[VISTO: F6]**

Reglas:

- `Ver detalle` muestra la información y la lista de productos/servicios asociados. **[VISTO: F6]**
- No se puede eliminar una categoría con productos asociados; sí se puede desactivar. **[VISTO: F6]**
- Se puede crear una categoría desde el formulario avanzado de un producto, sin ir al módulo de categorías. **[VISTO: F6]**

### 8.3 Atributos y variantes

- El menú `Inventario > Atributos` aparece en las capturas. **[VISTO: V6, V7]**
- La landing promete variantes. **[VISTO: F1]**
- El artículo de productos confirma que los inventariables permiten variantes. **[VISTO: F2]**
- No se observó el constructor de atributos, la combinación de valores, la generación masiva de variantes ni el stock por variante. **[DESCONOCIDO]**

**Lectura para FacturaLibre:** si se implementan variantes, conviene que cada variante sea un ítem vendible con su propio SKU, costo y stock, agrupado bajo un producto padre. Es una inferencia de diseño, no una observación de Alegra. **[INFERIDO]**

### 8.4 Combos y kits

Ruta: `Inventario > Ítems de venta > + Nuevo ítem de venta > Tipo de ítem: Combo`. **[VISTO: F8]**

Reglas:

- Los combos se crean como productos no inventariables. **[VISTO: F8]**
- Al vender un combo, se descuentan las cantidades de los productos inventariables que lo componen. **[VISTO: F8]**
- Pueden incluir ítems con variantes. **[VISTO: F8]**
- El costo promedio del combo es la suma de los costos promedio de sus componentes inventariables. **[VISTO: F8]**
- Los componentes no inventariables no entran en el costo. **[VISTO: F8]**
- Para aparecer en `Rentabilidad por ítems`, el combo debe tener al menos un componente inventariable. **[VISTO: F8]**
- Una vez asociado a documentos, no se pueden cambiar los componentes. **[VISTO: F8]**

La captura del constructor muestra un modal `Seleccionar producto` con `Producto`, `Cantidad`, `Unidad de medida`, `Costo`, y un botón `Agregar producto`; a la derecha, una tarjeta de vista previa del combo con precio y acciones `Guardar` / `Guardar y crear otro`. **[VISTO: V13]**

### 8.5 Implicación para FacturaLibre

- **Listas de precios:** modelar `PriceList` y `PriceListItem`; no sobrescribir el precio base.
- **Categorías:** entidad con nombre, descripción e imagen; borrado lógico si tiene ítems.
- **Variantes:** producto padre + variantes vendibles; evitar duplicar lógica de stock.
- **Combos:** modelar una lista de componentes (BOM) y generar movimientos de salida por cada componente al vender; no mantener stock propio del combo.

---

## 9. Importación, actualización masiva y conciliación

### 9.1 Herramientas promocionadas

La landing muestra tres herramientas:

- `Importar nuevos`.
- `Actualización masiva`.
- `Conciliación de inventario`.

La imagen muestra carga desde Excel y un toast de éxito `¡Ya están creados!`. **[VISTO: V3]**

### 9.2 Flujo de importación de productos

Según la documentación:

1. `Inventario > Ítems de venta > Más acciones > Importar`.
2. Elegir tipo: `Inventariables`, `No inventariables` o `Servicios`.
3. Descargar la plantilla de Excel.
4. Completar y guardar el archivo.
5. Seleccionar o arrastrar el archivo.
6. Elegir fecha inicial.
7. Revisar la información.
8. `Importar ítems`.

**[VISTO: F3]**

Variante de ruta: `Inventario > Gestión de ítems > Importar nuevos > Importar ítems`. **[VISTO: F2]**

### 9.3 Reglas y guardrails

- La importación masiva no está disponible para servicios ni combos. **[VISTO: F2]**
- Para servicios se puede elegir `No inventariables`. **[VISTO: F2]**
- No se deben mezclar productos inventariables, no inventariables y servicios en la misma plantilla. **[VISTO: F2, F3]**
- Se debe conservar el orden de la plantilla; no agregar columnas, filas ni celdas. **[VISTO: F2, F3]**
- La primera fila de títulos no se importa. **[VISTO: F2, F3]**
- `Alegra Sheet` permite editar la información dentro del flujo de importación si hay errores. **[VISTO: F3]**
- Las cuentas contables se ingresan por nombre, sin código. **[VISTO: F3]**
- Se puede retomar una importación en estado `Borrador` desde `Historial de importaciones`. **[VISTO: F3]**

### 9.4 Exportación

1. `Inventario > Ítems de venta`.
2. `Más opciones > Exportar`.
3. Elegir tipo de archivo y separador decimal.
4. `Exportar`.

**[VISTO: F2]**

### 9.5 Importación de ajustes desde archivo o imagen

- El ajuste manual permite `Desde un archivo o imagen`. **[VISTO: F5, V10]**
- Se pueden cargar hasta 100 productos simultáneamente. **[VISTO: F5]**
- Es compatible con Excel, PDF e imágenes. **[VISTO: F5]**
- Está disponible desde el Plan Pro de Alegra Contabilidad. **[VISTO: F5]**
- El flujo es: preparar datos, convertir a PDF/imagen, cargar, procesar y guardar. **[VISTO: F5]**

### 9.6 Conciliación de inventario

- La herramienta `Conciliación de inventario` aparece en la landing. **[VISTO: V3]**
- No se observó su flujo, su algoritmo, sus estados ni su tratamiento de diferencias. **[DESCONOCIDO]**

### 9.7 Lo que no se pudo confirmar

- Reglas exactas de `Actualización masiva`. **[DESCONOCIDO]**
- Cómo se resuelven conflictos entre la planilla y datos existentes. **[DESCONOCIDO]**
- Si la conciliación compara stock físico contra stock del sistema y genera un ajuste automático. **[DESCONOCIDO]**
- Si hay aprobación, conteo ciego o auditoría. **[DESCONOCIDO]**
- Límites por plan más allá del dato de “hasta 100 productos” en ajustes. **[DESCONOCIDO]**

### 9.8 Implicación para FacturaLibre

La importación es una **oportunidad de diferenciación** para un ERP pequeño. Recomendaciones:

- Asistente paso a paso, no una carga directa sin contexto.
- Plantilla versionada y validada.
- Vista previa con errores por fila antes de confirmar.
- Importación idempotente: reintentar no debe duplicar ítems.
- Informe de errores descargable.
- Historial de importaciones con estados `Borrador`, `Procesando`, `Completada`, `Con errores`.
- Actualización masiva separada de creación: una cosa es crear ítems y otra cambiar precios, costos o stock.
- Conciliación como documento de conteo físico con diferencias y ajuste propuesto; no como una edición directa de cantidades.

---

## 10. Reportes y análisis

### 10.1 Reportes documentados

| Reporte | Uso | Evidencia |
|---|---|---|
| Ventas por bodega | Comparar desempeño por bodega y ver productos/cantidades/valores | **[VISTO: F9]** |
| Rentabilidad por ítem | Ver ganancia real por producto, incluidos combos | **[VISTO: F8, F10]** |
| Valor de inventario / inventario valorizado | Ver el valor del stock | **[VISTO: F1, F2, F3]** |
| Ventas generales | Visión amplia de facturas y devoluciones | **[VISTO: F10]** |
| Ventas por ítem | Rotación y ajuste de stock | **[VISTO: F10]** |
| Ventas por cliente | Mejores compradores y fidelización | **[VISTO: F10]** |
| Ventas por vendedor | Desempeño comercial | **[VISTO: F10]** |
| Estado de cuenta de cliente | Consulta de cuenta | **[VISTO: F10]** |
| Ventas diarias | Resumen por forma de pago y numeración | **[VISTO: F10]** |

### 10.2 Reporte de ventas por bodega

Ruta: `Reportes > Ventas > Ventas por bodega`. **[VISTO: F9]**

Filtros y salida:

- Período.
- `Generar reporte`.
- Descarga en Excel.
- Columnas: `Bodega`, `Producto`, `Cantidad vendida`, `Valor total`.

**[VISTO: F9]**

La captura muestra:

- Breadcrumb `Reportes > Ventas > Ventas por bodega`.
- Título y descripción.
- Botón `Descargar`.
- Filtro de período y centro.
- KPIs: ventas brutas, notas crédito, antes de impuestos, impuestos, después de impuestos.
- Gráfico `Total de ventas` con vista `Diario`/`Mensual`.
- Panel `Top 5 ítems más vendidos` por unidades.

**[VISTO: V12]**

**Nota conceptual:** el reporte refleja la bodega de despacho, no el origen histórico del stock. Un producto transferido aparece en la bodega desde la que se facturó. **[VISTO: F9]**

### 10.3 Lo que no se pudo confirmar

- Frecuencia de actualización de los dashboards. **[DESCONOCIDO]**
- Exportaciones disponibles además de Excel. **[DESCONOCIDO]**
- Permisos por rol para ver costos, márgenes o valorización. **[DESCONOCIDO]**
- Existencia de reporte de Kárdex detallado por ítem y bodega. **[DESCONOCIDO]**
- Existencia de reporte de productos sin movimiento o stock muerto. **[DESCONOCIDO]**

### 10.4 Implicación para FacturaLibre

Un MVP de reportes puede empezar con cuatro vistas:

1. **Stock por bodega:** item, bodega, cantidad, costo, valor.
2. **Kárdex:** fecha, documento, tipo, entrada, salida, saldo.
3. **Bajo stock:** item, stock actual, mínimo, faltante, bodega.
4. **Ventas y rentabilidad por ítem:** unidades, ingresos, costo, margen.

Los dashboards con gráficos pueden llegar después; primero deben ser correctos y reconciliables.

---

## 11. Patrones de UX observados

| Patrón | Cómo aparece | Por qué funciona | Evidencia |
|---|---|---|---|
| Divulgación progresiva | Modal básico + `Ir al formulario avanzado` | Reduce fricción sin limitar casos complejos | **[VISTO: V6, F2]** |
| Tabla primero | Listado denso con filtros y acciones por fila | Escala mejor que tarjetas para catálogos grandes | **[VISTO: V5, V7]** |
| Acción primaria única | `+ Nuevo producto de venta` destacado | Evita competencia visual | **[VISTO: V5]** |
| Acciones contextuales | Menú `Más acciones`, iconos por fila | Mantiene la pantalla limpia | **[VISTO: V5, V7]** |
| Tooltips | `Desactivar` al pasar el cursor | Aclara iconos ambiguos | **[VISTO: V7]** |
| Selección múltiple | Checkboxes y acciones en lote | Acelera tareas repetitivas | **[VISTO: V7, F2]** |
| Creación inline | Nueva categoría desde el producto; nuevo ítem desde factura | Evita perder el contexto | **[VISTO: F2, F6]** |
| Contexto explícito | Selector de lista de precios; bodega en documentos | Evita ambigüedad de precios y stock | **[VISTO: V5, F4]** |
| Guardrails | Tipo inmutable; borrar deshabilitado con movimientos; desactivar con stock cero | Protege integridad sin ocultar la acción | **[VISTO: F2]** |
| Baja lógica | `Activo` / `Desactivado` en bodegas e ítems | Conserva historial y relaciones | **[VISTO: F2, V8]** |
| Feedback inmediato | Toasts `Éxito`, `¡Ya están creados!` | Confirma acciones y reduce incertidumbre | **[VISTO: V3, V8]** |
| Importación guiada | Plantilla, revisión, importación, historial | Reduce errores de carga masiva | **[VISTO: F3]** |
| Ayuda en contexto | `Saber más`, iconos de ayuda, `AlegraTips` | Educación sin salir del flujo | **[VISTO: V6, V8, F5, F6]** |
| Jerarquía visual | Fondo claro, tarjetas blancas, acento teal | Separa navegación, contenido y acciones | **[VISTO: capturas públicas]** |

### 11.1 Principios que conviene adoptar

1. **La acción principal debe ser obvia; las secundarias deben estar agrupadas.**
2. **El estado del dato debe ser visible:** activo, inactivo, con movimientos, sin stock.
3. **Las reglas de negocio deben explicarse antes de bloquear una acción**, no solo después.
4. **Las operaciones masivas deben tener vista previa y confirmación.**
5. **La navegación debe nombrar el dominio del usuario:** productos, bodegas, ajustes, transferencias, listas de precios.
6. **La ayuda debe estar donde surge la duda:** junto al campo, no solo en un centro de ayuda externo.

---

## 12. Vacíos de información y riesgos de asumir

| Pregunta | Estado | Por qué importa para FacturaLibre |
|---|---|---|
| ¿Cómo se configura la alerta de stock mínimo/máximo? | **[DESCONOCIDO]** | Define el modelo de umbrales y la UI de configuración |
| ¿Cuál es el canal de alerta: campana, email, push? | **[DESCONOCIDO]** | Define infraestructura y prioridad del MVP |
| ¿La alerta es por ítem, por bodega o consolidada? | **[DESCONOCIDO]** | Afecta el cálculo y la navegación |
| ¿La actualización de stock es inmediata o eventual? | **[DESCONOCIDO]** | Afecta la percepción de “tiempo real” y la concurrencia |
| ¿Una factura en borrador reserva stock? | **[DESCONOCIDO]** | Evita sobreventa o bloqueos innecesarios |
| ¿Se permite stock negativo? | **[VISTO: se promocionan cantidades negativas; DESCONOCIDO: reglas]** | Afecta validaciones y reportes |
| ¿El costo promedio es global o por bodega? | **[DESCONOCIDO]** | Cambia transferencias, ajustes y valorización |
| ¿Cómo funciona la conciliación de inventario? | **[DESCONOCIDO]** | Define si se implementa conteo físico o solo ajuste |
| ¿Cómo se gestionan variantes y su stock? | **[VISTO: existen; DESCONOCIDO: UI y modelo]** | Evita duplicar productos o perder trazabilidad |
| ¿Qué permisos existen para costos y valorización? | **[DESCONOCIDO]** | Relevante para roles y seguridad |
| ¿Hay auditoría de cambios y movimientos? | **[INFERIDO: los bloqueos por movimientos sugieren historial; DESCONOCIDO: alcance]** | Define el modelo de trazabilidad |
| ¿La API pública expone los mismos conceptos? | **[DESCONOCIDO en este informe]** | No se debe asumir que la UI y la API comparten modelo exacto |

> **Regla de oro:** no convertir una promesa de marketing o una captura parcial en una regla de negocio. Lo que no se observó queda como desconocido.

---

## 13. Recomendaciones para el módulo de inventarios de FacturaLibre

### 13.1 Arquitectura de dominio (prioridad alta)

El módulo puede montarse sobre el modelo actual de `items` y el servicio contable existente, pero el inventario requiere entidades nuevas. Una propuesta conceptual:

```text
Item
 ├── type: product | service | combo
 ├── reference / SKU
 ├── unit
 ├── cost
 ├── track_inventory
 ├── stock_min / stock_max
 ├── category_id
 └── accounting_accounts

Warehouse
 └── name, address, cost_center, active

StockMovement
 ├── item_id
 ├── warehouse_id
 ├── type: sale | sale_return | purchase | purchase_return |
 │         adjustment_in | adjustment_out | transfer_out | transfer_in | initial
 ├── quantity
 ├── unit_cost
 ├── source_type / source_id / source_line_id
 ├── occurred_at
 └── idempotency_key

StockBalance
 ├── item_id + warehouse_id (unique)
 ├── quantity
 ├── value
 └── version

StockTransfer
 ├── origin_warehouse_id
 ├── destination_warehouse_id
 ├── date
 ├── observations
 └── lines

StockAdjustment
 ├── warehouse_id
 ├── date
 ├── numbering
 ├── observations
 └── lines (increase/decrease, quantity, unit_cost)

PriceList / PriceListItem
ItemCategory
ItemVariant / Attribute
ItemComponent (para combos)
```

**[INFERIDO: propuesta de diseño a partir de los flujos observados]**

Principios:

- **Libro de movimientos como fuente de verdad.** Los saldos son una proyección reconstruible.
- **Un movimiento por efecto:** una transferencia genera salida y entrada; una venta genera salida; una devolución genera entrada.
- **Idempotencia:** cada documento de origen no debe duplicar movimientos si se reintenta.
- **Bloqueo optimista:** usar `version` en `StockBalance`, consistente con la decisión de FacturaLibre para datos maestros.
- **Baja lógica:** no borrar bodegas, ítems o categorías con historia.
- **Trazabilidad:** cada movimiento debe responder quién, cuándo, desde qué documento y por qué.

### 13.2 Decisiones que deben tomarse antes de codificar

| Decisión | Opciones | Recomendación |
|---|---|---|
| Política de costeo | Promedio ponderado global / por bodega / FIFO | Empezar con promedio ponderado; documentar si es global o por bodega |
| Stock negativo | Permitir / bloquear / permitir con advertencia | Bloquear por defecto; permitir solo con configuración explícita |
| Reservas | Sin reservas / reservar en borrador / reservar al emitir | Empezar sin reservas; descontar al confirmar la venta |
| Transferencias | Directas / con aprobación | Directas en MVP; aprobación después |
| Conciliación | Ajuste manual / conteo con diferencias | Conteo con diferencias y ajuste propuesto |
| Variantes | Ítems independientes / producto padre + variantes | Producto padre + variantes vendibles |
| Combos | Stock propio / BOM con descuento de componentes | BOM con descuento de componentes |

**[INFERIDO: decisiones de diseño, no observaciones de Alegra]**

### 13.3 Roadmap sugerido

#### MVP

- Extender `Item` con tipo, referencia, unidad, costo, `track_inventory`, stock mínimo/máximo y categoría.
- Crear `Warehouse` y `StockMovement`.
- Calcular `StockBalance` por ítem y bodega.
- Formulario básico de producto con cantidad inicial y bodega.
- Listado de productos con búsqueda, filtros, acciones y paginación.
- Ajuste de inventario con aumento/disminución y costo promedio.
- Transferencia entre bodegas.
- Kárdex básico y stock por bodega.
- Alerta visual de bajo stock y agotado.
- Asientos contables automáticos reutilizando la integración contable existente.

#### Siguiente iteración

- Listas de precios.
- Categorías con imagen y baja lógica.
- Importación/exportación con vista previa y errores.
- Reporte de ventas y rentabilidad por ítem.
- Reporte de ventas por bodega.
- Combos/kits.
- Variantes.
- Historial de importaciones.

#### Posterior

- Conciliación de inventario con conteo físico.
- Actualización masiva avanzada.
- Reservas de stock.
- Aprobaciones de transferencias.
- Alertas por email/push.
- Reportería personalizada.

### 13.4 UX concreta para FacturaLibre

- **Pantalla de inventario:** KPIs de valor, unidades y productos bajo mínimo; accesos a productos, bodegas, ajustes y reportes.
- **Listado de productos:** tabla con `Nombre`, `SKU/Referencia`, `Categoría`, `Bodega`, `Stock`, `Costo`, `Precio`, `Estado`, `Acciones`.
- **Formulario de producto:** modal básico + sección avanzada; el tipo de ítem se elige primero y se explica su inmutabilidad.
- **Detalle de producto:** resumen, stock por bodega, últimos movimientos, documentos asociados y acciones.
- **Bodegas:** listado con estado, valor estimado, número de ítems y acciones; detalle con ítems asociados y movimientos.
- **Transferencias:** asistente con origen, destino, fecha, observaciones, selector de ítems y cantidad disponible visible.
- **Ajustes:** documento con bodega, fecha, numeración, observaciones y líneas con cantidad actual, tipo, cantidad, costo y cantidad final.
- **Alertas:** badge en navegación y lista filtrable; cada alerta debe explicar “stock actual vs. mínimo” y permitir ir al ítem o a la bodega.
- **Importación:** wizard con plantilla, carga, mapeo, vista previa, errores y confirmación.
- **Feedback:** toasts para éxito, banners para errores, confirmaciones para acciones destructivas.
- **Ayuda:** tooltips y enlaces “Saber más” junto a campos complejos, especialmente costo, stock mínimo y cuentas contables.

### 13.5 Lo que no conviene copiar

- No copiar la estética, iconografía ni textos exactos de Alegra.
- No asumir que su modelo de datos es el adecuado para FacturaLibre.
- No implementar “tiempo real” como un campo que se actualiza en el frontend sin un libro de movimientos.
- No prometer alertas de stock mínimo hasta definir umbral, canal y frecuencia.
- No construir conciliación, variantes o combos antes de estabilizar el flujo básico de productos, bodegas y movimientos.

---

## 14. Conclusiones

Alegra resuelve el inventario como un **sistema de documentos y movimientos**, con una capa de maestros (ítems, bodegas, categorías, listas de precios) y una capa de análisis (valorización, ventas por bodega, rentabilidad). Su UX prioriza la operación: tablas densas, acciones contextuales, formularios progresivos, guardrails claros y ayudas inline.

Para FacturaLibre, la inspiración más valiosa no es una pantalla concreta, sino la separación conceptual:

```text
documento → movimiento → saldo → valorización → reporte/contabilidad
```

Si esa cadena se implementa con idempotencia, trazabilidad y reglas explícitas, el módulo podrá crecer hacia multi-bodega, listas de precios, variantes, combos e importación masiva sin rehacer el núcleo. Si se empieza con un campo `stock` editable en el producto, cada nueva función exigirá parches.

La segunda lección es de producto: **no mostrar todo a la vez**. El formulario básico, la creación inline, los filtros persistentes y la importación guiada demuestran que la complejidad puede esconderse detrás de un flujo claro sin perder potencia.

---

## 15. Trazabilidad de afirmaciones críticas

| Afirmación | Nivel | Fuente |
|---|---|---|
| La landing vigente es `/colombia/inventarios/`; `/colombia/inventario/` da 404 | **[VISTO]** | Comprobación HTTP directa |
| El inventario se actualiza con cada venta | **[VISTO]** | F1 |
| Existen productos inventariables, no inventariables y servicios | **[VISTO]** | F2, F3 |
| El tipo de ítem no se puede convertir si tiene movimientos | **[VISTO]** | F2, F3 |
| El listado tiene selector de lista de precios, filtros y acciones por fila | **[VISTO]** | V5, V7, F2 |
| El formulario básico tiene tipo, nombre, bodega, unidad, cantidad inicial, costo, precio e impuesto | **[VISTO]** | V6 |
| Las bodegas se crean en `Inventario > Bodegas > Nueva bodega` | **[VISTO]** | F4, V8 |
| Las transferencias requieren más de una bodega y mueven stock entre origen y destino | **[VISTO]** | F4, V9 |
| Los documentos de venta deben seleccionar bodega | **[VISTO]** | F4 |
| El ajuste usa promedio ponderado y distingue aumento/disminución | **[VISTO]** | F5, V10 |
| Existen campos de stock mínimo y máximo | **[VISTO]** | F2, F3 |
| La UI de alertas de stock mínimo no se observó | **[DESCONOCIDO]** | Búsqueda en centro de ayuda sin artículo específico |
| El costo promedio es global o por bodega | **[DESCONOCIDO]** | F5 no lo aclara |
| Una factura en borrador reserva stock | **[DESCONOCIDO]** | No observado |
| La conciliación de inventario existe como promesa | **[VISTO]** | V3 |
| El flujo de conciliación no se observó | **[DESCONOCIDO]** | No hay artículo/captura específica |
| La arquitectura de movimientos → saldos es la adecuada para FacturaLibre | **[INFERIDO]** | Diseño propuesto a partir de los flujos observados |

---

*Informe elaborado para el proyecto educativo FacturaLibre. Las marcas de evidencia distinguen observación pública, inferencia y vacío de información. No se copió código ni se accedió a la aplicación autenticada de Alegra.*
