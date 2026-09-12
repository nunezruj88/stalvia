# StalvIA 🛒

> **Estalvia** (del catalán _estalviar_, ahorrar) + **IA** (inteligencia artificial).

Aplicación personal para registrar tickets y comparar precios de supermercados en Cataluña.

**Estado: prototipo en desarrollo.** Hay backend, interfaz y cinco conectores implementados, pero la instalación desde cero necesita correcciones y las comparaciones todavía pueden mostrar ahorros incorrectos. Este README documenta el código revisado y las mejoras pendientes; no implica que estas mejoras estén implementadas.

## Qué hace actualmente

1. Recibe una foto de un ticket.
2. Envía la imagen a la API de OpenAI para extraer productos, cantidades y precios.
3. Consulta cinco conectores y guarda sus resultados en Redis durante cuatro horas.
4. Guarda la compra y las observaciones de precios en PostgreSQL.
5. Muestra comparaciones, historial de compras y estadísticas básicas.
6. Permite registrar manualmente un producto y su precio.

La extracción y la comparación se ejecutan dentro de la misma petición. Todavía no existe una pantalla para revisar y corregir el ticket antes de guardarlo.

### Estado de los supermercados

| Supermercado | Implementación | Validación pendiente |
|---|---|---|
| Mercadona | Consulta HTTP a una API no oficial | Disponibilidad del endpoint, formato de respuesta, ubicación y equivalencia |
| Carrefour | Playwright / Chromium | Selectores, acceso al catálogo y equivalencia |
| Bonpreu / Esclat | Playwright / Chromium | Selectores, acceso al catálogo y equivalencia |
| El Corte Inglés | Playwright / Chromium | Selectores, acceso al catálogo y equivalencia |
| Alcampo | Playwright / Chromium | Selectores, acceso al catálogo y equivalencia |

**Que exista un conector no garantiza que funcione contra la tienda en vivo.** Todos seleccionan el primer resultado. Mercadona tiene el almacén `vlc1` fijado en el código; no se debe asumir que representa el catálogo o los precios de la ubicación del usuario.

## Arquitectura actual

```text
Navegador
    │
    ▼
Cloudflare Access + Tunnel (configuración externa)
    │
    ▼
nginx externo (dirección y puerto propios)
    ├── /      → host de StalvIA:3000 → frontend React / Vite
    └── /api/  → host de StalvIA:8000 → backend FastAPI
                                           ├── PostgreSQL
                                           ├── Redis
                                           ├── API de OpenAI
                                           └── conectores de supermercados
```

Docker Compose define **cuatro servicios**: `postgres`, `redis`, `backend` y `frontend`. No incluye nginx ni el conector de Cloudflare Tunnel.

El almacenamiento de imágenes en Cloudflare R2 está **pendiente**. El modelo contiene `ticket_image_url`, pero no hay integración de almacenamiento.

| Capa | Tecnología del repositorio |
|---|---|
| Frontend | React 18, Vite 5, React Router; configuración de Tailwind pendiente |
| Backend | Python 3.12, FastAPI, SQLAlchemy |
| Base de datos | PostgreSQL 16, Alembic, extensión pg_trgm |
| Caché | Redis 7; TTL de comparación de cuatro horas |
| Extracción de tickets | SDK de OpenAI, modelo configurado en código: `gpt-4o-mini` |
| Conectores | httpx y Playwright / Chromium |
| Entorno previsto | Docker Compose en un host o LXC de Proxmox |
| Acceso remoto previsto | nginx externo, Cloudflare Tunnel y Cloudflare Access |

Las versiones declaradas no constituyen una validación de compatibilidad o seguridad actual.

## Estructura del proyecto

```text
stalvia/
├── .env.example
├── .github/workflows/ci.yml
├── docker-compose.yml
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini.example
│   ├── main.py                 # API, extracción y comparación
│   ├── crud.py                 # Persistencia y consultas
│   ├── schemas.py              # Esquemas de respuesta
│   ├── models.py               # Modelos SQLAlchemy
│   ├── database.py
│   ├── migrations/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/           # Sin migración inicial versionada
│   └── scrapers/
│       ├── mercadona.py
│       ├── carrefour.py
│       ├── bonpreu.py
│       ├── elcorteingles.py
│       └── alcampo.py
├── frontend/
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── index.css
│       ├── components/
│       │   ├── ComparisonTable.jsx
│       │   ├── ProductRow.jsx
│       │   └── PriceSummary.jsx
│       ├── pages/
│       │   ├── Home.jsx
│       │   ├── Manual.jsx
│       │   ├── History.jsx
│       │   └── Analytics.jsx
│       └── services/api.js
├── nginx/nginx.conf
└── postgres/init.sql
```

## Correcciones necesarias antes del despliegue

### 1. Instalación reproducible de la base de datos

Actualmente, `postgres/init.sql` intenta crear índices sobre `products` y `product_aliases` antes de que existan las tablas. Esto provoca un error durante la inicialización de una base nueva.

Además, `backend/migrations/versions/` no contiene una migración inicial. Ejecutar `alembic upgrade head` en este estado no crea el esquema de la aplicación.

Trabajo pendiente:

- Crear y versionar una migración inicial revisada.
- Crear la extensión `pg_trgm` antes de los índices que dependen de ella.
- Crear las tablas antes de sus índices.
- Eliminar del script de inicialización los índices prematuros.
- Leer la conexión de Alembic desde `DATABASE_URL`, evitando duplicar credenciales.
- Comprobar la instalación con una base vacía y la actualización de una base existente.

Las migraciones deben generarse y revisarse durante el desarrollo. **No generar una migración nueva en cada despliegue.** La generación automática tampoco sustituye la definición explícita de extensiones e índices especiales.

Si ya hubo un intento de inicialización fallido, revisar los registros y el estado de la base: los scripts de inicialización no se vuelven a ejecutar automáticamente sobre un volumen ya inicializado. No borrar un volumen con datos para solucionar este problema.

### 2. Proveedor de IA y validación del ticket

El código utiliza OpenAI, aunque la variable se llama `ANTHROPIC_API_KEY` y algunos comentarios mencionan Claude o Kimi.

Trabajo pendiente:

- Renombrar la variable a `OPENAI_API_KEY` en código y ejemplos.
- Hacer configurable el modelo y validar la configuración al arrancar.
- Usar un cliente asíncrono y manejar errores y tiempos de espera.
- Validar la estructura extraída, fechas, cantidades y precios antes de consultar tiendas o escribir en la base.
- Conservar totales de línea y descuentos; comprobar su concordancia con el total del ticket.
- Permitir revisar y corregir el ticket antes de guardarlo.
- Detectar subidas duplicadas para evitar compras repetidas.
- Limitar tamaño y formatos de imagen en el backend.

### 3. Comparaciones fiables

El cálculo actual suma solo los productos encontrados en cada supermercado y elige el total más bajo. Una tienda con un único precio puede aparecer como más barata que otra con la cesta completa.

Antes de presentar ahorros como fiables:

- Mostrar cobertura por tienda, por ejemplo, «7 de 10 productos».
- Comparar la misma cesta o el mismo subconjunto de productos en ambos lados.
- Marcar una cesta incompleta y no presentarla como una compra completa más barata.
- Tratar un precio ausente como desconocido, sin convertirlo en cero.
- Separar coincidencias exactas, alternativas equivalentes y resultados dudosos.
- Comprobar código de barras, marca, variedad, formato, cantidad y unidad.
- Normalizar €/kg, €/l o €/unidad cuando corresponda.
- Mostrar el producto encontrado, su enlace, fecha de consulta y ubicación.
- Distinguir errores del conector de productos no encontrados.

### 4. Catálogo e histórico

La identificación actual reutiliza productos por similitud textual superior a `0.6`. Puede mezclar variedades o tamaños diferentes. El alta manual tampoco prioriza la búsqueda por código de barras.

Trabajo pendiente:

- Priorizar códigos de barras e identificadores de la tienda.
- Usar similitud textual para proponer coincidencias y revisar las ambiguas.
- Evitar duplicados y conflictos en altas concurrentes.
- Registrar origen del precio —ticket, manual o conector— y momento real de observación.
- Conservar tamaño, unidad y ubicación de la oferta comparada.
- Revisar la deduplicación diaria para no perder cambios de precio.
- Configurar el borrado de las líneas al eliminar una compra.
- Usar aritmética decimal para importes.

La media de todos los precios de una tienda describe la muestra registrada; **no demuestra qué supermercado es más barato** si las muestras contienen productos distintos. La clasificación debe basarse en una cesta común.

### 5. Recursos, interfaz y operación

- Limitar la concurrencia y reutilizar navegadores. Un ticket de 20 productos puede lanzar hasta 80 instancias de Chromium con el diseño actual.
- Procesar análisis largos como trabajos con estado y progreso.
- Evitar que una caída de Redis impida registrar el ticket.
- Completar Tailwind y PostCSS: faltan sus configuraciones.
- Conectar la cámara al elemento de vídeo después de montarlo en `Manual.jsx`.
- Mostrar errores y opciones de reintento en historial y estadísticas.
- Separar desarrollo y producción: actualmente se usa Vite en modo desarrollo y Uvicorn con `--reload`.
- Añadir comprobaciones de disponibilidad de base de datos y caché; `/api/health` solo devuelve una respuesta fija.
- Restringir el acceso directo a los puertos de origen y configurar Cloudflare Access.
- Añadir copias de seguridad y comprobar su restauración.
- Fijar dependencias reproducibles, añadir el archivo de bloqueo del frontend y revisar actualizaciones.

No se ha validado un dimensionamiento mínimo. La propuesta inicial de 2 GB de RAM no debe considerarse suficiente hasta limitar la concurrencia y medir el consumo.

## Preparación del entorno

**Esta sección prepara el despliegue; la instalación completa requiere primero las correcciones anteriores.**

### Requisitos

- Host Linux o LXC con Docker Engine y el complemento Docker Compose instalados.
- Git.
- PostgreSQL y Redis se ejecutan mediante Compose.
- Clave de OpenAI para el código actual.
- Para acceso remoto: nginx externo, dominio y Cloudflare Tunnel con una política de Access.

En Proxmox, elegir una plantilla disponible y adaptar almacenamiento, identificador, red y recursos al entorno. La dirección `10.8.1.105` usada abajo es solo un ejemplo. No es necesario instalar dependencias Python en el host.

### Clonar y preparar variables

```bash
git clone https://github.com/nunezruj88/stalvia.git
cd stalvia
cp .env.example .env
```

Editar `.env` sin subir credenciales al repositorio:

```dotenv
# Compatibilidad temporal: el código actual espera una clave de OpenAI
# bajo este nombre heredado. Una clave de Anthropic no sirve aquí.
ANTHROPIC_API_KEY=REEMPLAZAR_POR_CLAVE_DE_OPENAI

POSTGRES_DB=stalvia
POSTGRES_USER=stalvia
POSTGRES_PASSWORD=REEMPLAZAR_POR_PASSWORD
DATABASE_URL=postgresql://stalvia:REEMPLAZAR_POR_PASSWORD@postgres:5432/stalvia
REDIS_URL=redis://redis:6379
```

Mantener la contraseña coherente con `DATABASE_URL`. Los caracteres reservados de la contraseña deben codificarse al incluirla en una URL. Cambiar únicamente el nombre a `OPENAI_API_KEY` no funcionará hasta modificar también el backend.

Mientras Alembic mantenga su configuración actual:

```bash
cp backend/alembic.ini.example backend/alembic.ini
```

Editar `sqlalchemy.url` con la misma conexión. Ese archivo está excluido de Git; esta duplicación es temporal hasta que Alembic lea la variable de entorno.

### Arranque después de corregir y versionar las migraciones

El siguiente orden solo es válido una vez corregido `init.sql` y añadida la migración inicial:

```bash
docker compose up -d postgres redis
docker compose run --rm backend alembic upgrade head
docker compose up -d --build backend frontend
docker compose ps
docker compose logs --tail=100 postgres backend frontend
```

Comprobar los cuatro servicios y verificar el esquema antes de cargar tickets. Las migraciones se ejecutan dentro del contenedor porque `postgres` es el nombre del servicio en la red de Compose.

### nginx externo

Usar la dirección del host de StalvIA en el nginx externo. Por ejemplo:

```nginx
server {
    listen 80;
    server_name stalvia.example.com;
    client_max_body_size 10M;

    location / {
        proxy_pass http://10.8.1.105:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api/ {
        proxy_pass http://10.8.1.105:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }
}
```

Validar y recargar la configuración del nginx externo:

```bash
nginx -t
nginx -s reload
```

El archivo actual `nginx/nginx.conf` utiliza `frontend` y `backend` como nombres de host. Solo es aplicable si nginx comparte una red Docker donde esos nombres se resuelvan; para nginx externo debe adaptarse como en el ejemplo.

El timeout de 60 segundos no garantiza que termine el análisis actual. La solución prevista es el procesamiento con progreso, en lugar de depender de una petición HTTP larga. El límite del proxy tampoco sustituye la validación de archivos en el backend.

### Cloudflare Tunnel y Access

Configurar el hostname público para dirigirlo a **la dirección y puerto alcanzables del nginx externo**, por ejemplo:

```text
Hostname público: stalvia.example.com
Servicio de origen: http://<DIRECCION_NGINX>:80
```

No apuntar a `10.8.1.105:8080` salvo que se haya configurado expresamente un servicio en ese puerto: el Compose actual no lo publica.

Crear una aplicación y una política de Cloudflare Access que autoricen al usuario previsto. Publicar un túnel no configura por sí solo esa autorización. Restringir también las rutas directas a los puertos `3000` y `8000` para impedir que el origen permita eludir Access.

## Modelo de datos

| Entidades | Uso actual o previsto |
|---|---|
| `purchases`, `purchase_items` | Tickets y líneas de compra |
| `products`, `product_aliases` | Catálogo y variantes de nombres |
| `price_history` | Observaciones de precios |
| `stores` | Tiendas; actualmente se reutiliza la primera de cada cadena |
| `categories`, `brands` | Clasificación y marcas |
| `promotions` | Modelo definido; gestión de promociones pendiente |
| `price_alerts` | Modelo definido; notificaciones pendientes |
| `shopping_lists`, `shopping_list_items` | Modelos definidos; funcionalidad pendiente |

La existencia de los modelos no significa que las tablas se creen automáticamente ni que todas las funciones estén disponibles.

## Validación y criterios para una primera versión

El flujo de CI actual ejecuta Ruff para el backend y compila el frontend. No ejecuta pruebas funcionales ni valida conectores en vivo. Consultar el estado actualizado en [GitHub Actions](https://github.com/nunezruj88/stalvia/actions).

Antes de considerar utilizable la primera versión:

- [ ] Instalar desde una base vacía y aplicar migraciones sin errores.
- [ ] Completar la revisión del backend y la compilación del frontend.
- [ ] Verificar visualmente estilos y navegación.
- [ ] Probar extracción válida, salida inválida, imagen excesiva y fallo del proveedor.
- [ ] Revisar y corregir el ticket antes del guardado.
- [ ] Probar productos con pesos, formatos y descuentos diferentes.
- [ ] Verificar que precios ausentes y cestas parciales no generen falsos ahorros.
- [ ] Probar alta, consulta y borrado de compras con líneas.
- [ ] Probar código de barras y evitar fusiones incorrectas de productos.
- [ ] Validar un conector en vivo y distinguir sus errores de ausencia de productos.
- [ ] Medir consumo y tiempo con tickets representativos.
- [ ] Verificar Access, restricción del origen y restauración de copias.

## Hoja de ruta

1. **Base reproducible:** migraciones, configuración de IA, estilos e instrucciones de instalación.
2. **Registro fiable:** revisión del ticket, validaciones, duplicados e historial.
3. **Comparación fiable:** equivalencia, unidades, cobertura y un primer conector validado.
4. **Ampliación gradual:** resto de supermercados, ubicación, caché y procesamiento con progreso.
5. **Analítica:** evolución por producto y comparaciones sobre cestas comunes.
6. **Funciones futuras:** alertas, listas de compra y almacenamiento opcional de imágenes en R2.

## Uso y distribución

Proyecto destinado a uso personal. El repositorio no incluye un archivo de licencia independiente.
