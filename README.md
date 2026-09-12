# StalvIA 🛒

**Estalvia** (ahorrar, en catalán) + **IA**. Aplicación personal para registrar tickets y explorar precios de supermercados en Cataluña.

## Estado y funcionamiento

Versión 0.2: base de instalación y flujo de revisión corregidos. Los conectores de tiendas siguen siendo experimentales: una respuesta de búsqueda no demuestra que el producto sea equivalente.

1. Sube una foto JPEG, PNG o WebP de hasta 8 MB y 20 megapíxeles.
2. El proveedor de IA configurado extrae un borrador. La extracción no guarda ninguna compra.
3. Revisa supermercado, fecha, nombres, cantidades, precios y totales. Puedes añadir o eliminar líneas.
4. Confirma el ticket. El servidor comprueba campos y concordancia del total; conserva los totales de línea, incluidos descuentos.
5. Busca precios. La interfaz consulta producto a producto y muestra el progreso; el ticket sigue guardado aunque falle una tienda.
6. Comprueba el enlace y el formato de cada resultado. Solo las coincidencias confirmadas entran en la comparación. Las cestas incompletas no pueden aparecer como ganadoras.

La confirmación de coincidencias es una estimación de esta sesión; no se guarda como una equivalencia permanente ni como precio verificado en el histórico. Confirma únicamente el mismo producto, formato y unidad de venta. La conversión automática entre envases, kg y litros sigue pendiente.

### Supermercados

| Tienda | Conector | Limitación |
|---|---|---|
| Mercadona | HTTP a API no oficial | Almacén configurable; endpoint y catálogo sujetos a cambios |
| Carrefour | Playwright | Selectores y acceso sujetos a cambios |
| Bonpreu / Esclat | Playwright | Selectores y acceso sujetos a cambios |
| El Corte Inglés | Playwright | Selectores y acceso sujetos a cambios |
| Alcampo | Playwright | Selectores y acceso sujetos a cambios |

Los conectores devuelven candidatos, no coincidencias automáticas. Un error se diferencia de un precio no disponible. Nunca se interpreta un precio ausente como cero. No se garantiza cobertura de ninguna tienda hasta validar el conector y la ubicación en el entorno de destino.

## Mantenimiento

La sección **Mantenimiento** reúne el catálogo guardado, la búsqueda por nombre o código de barras y el alta manual de productos con su precio en un supermercado. El listado está paginado para poder consultar todos los productos.

**Ver precios y comparar** muestra la última observación guardada de cada supermercado, con fecha y origen. Consultar el catálogo o guardar un producto no inicia búsquedas externas. El botón **Comparar precios en supermercados** permite solicitarlas expresamente, también sin haber subido un ticket. Confirma que coinciden producto y formato antes de comparar los resultados. La vista distingue precios almacenados de candidatos encontrados y no guarda estos candidatos como precios verificados.

## Arquitectura

```text
Navegador → Cloudflare Access / Tunnel → nginx externo
                                             │
                                             ▼
                                  host de StalvIA:3000
                                  nginx + React compilado
                                             │ /api/
                                             ▼
                                       backend:8000
                                  ├── PostgreSQL 16
                                  ├── Redis (caché opcional)
                                  ├── IA configurable
                                  └── conectores de tiendas
```

Compose contiene cuatro servicios persistentes (`postgres`, `redis`, `backend`, `frontend`) y una tarea `migrate` que termina después de aplicar Alembic. El nginx que sirve los archivos de React está dentro de `frontend`; el proxy de entrada y Cloudflare Tunnel son externos.

- Backend: Python 3.12, FastAPI, SQLAlchemy y Alembic.
- Frontend: React 18, React Router, Vite y Tailwind 3. Las versiones exactas se registran en `package-lock.json`.
- OCR: adaptadores asíncronos para OpenAI, Anthropic y servicios compatibles con OpenAI; selección mediante `.env`.
- Conectores: máximo configurable de consultas simultáneas, con un navegador compartido y contextos aislados.
- Redis: caché de candidatos durante cuatro horas. Sus fallos no impiden consultar tiendas ni guardar tickets.
- PostgreSQL: compras, catálogo y precios observados. R2 todavía no está integrado.

## Instalación nueva

Requisitos: host Linux o LXC preparado para Docker Engine y Docker Compose, Git y espacio suficiente para PostgreSQL y Chromium. No es necesario instalar Python o Node en el host. Dimensionar recursos con tickets reales; no se garantiza un mínimo de RAM.

```bash
git clone https://github.com/nunezruj88/stalvia.git
cd stalvia
cp .env.example .env
```

Editar `.env`:

```dotenv
AI_PROVIDER=openai
AI_API_KEY=REEMPLAZAR_POR_CLAVE_DEL_PROVEEDOR
AI_MODEL=gpt-4o-mini
POSTGRES_DB=stalvia
POSTGRES_USER=stalvia
POSTGRES_PASSWORD=REEMPLAZAR_POR_PASSWORD_SEGURA
REDIS_URL=redis://redis:6379
SCRAPER_CONCURRENCY=2
MERCADONA_WAREHOUSE=vlc1
BIND_ADDRESS=127.0.0.1
```

La aplicación puede arrancar sin configurar IA para el registro manual; la lectura de fotos devolverá un mensaje de configuración pendiente. Usa una clave del proveedor elegido.

La conexión de la aplicación y de Alembic se construye a partir de `POSTGRES_*`, incluyendo contraseñas con caracteres reservados. `DATABASE_URL` es opcional y tiene prioridad si se define. Si se proporciona una URL manualmente, codificar los caracteres reservados de sus credenciales.

```bash
docker compose up -d --build
docker compose ps -a
docker compose logs --tail=100 migrate backend frontend
```

La tarea `migrate` debe terminar con código 0. El backend arranca después de la migración y la interfaz después de que el backend esté disponible. Una tarea `migrate` terminada correctamente no es un contenedor fallido.

Abrir `http://localhost:3000` en el host o mediante un túnel SSH. `/api/health` comprueba el acceso a la tabla de compras y muestra el proveedor, el modelo y si la configuración de OCR está completa. No verifica la validez de la clave ni hace una llamada de pago.

### Cambiar de proveedor de IA

Edita las siguientes variables en `.env`. No hace falta modificar código. El modelo elegido debe admitir imágenes y estar disponible en tu cuenta.

**OpenAI** (configuración predeterminada):

```dotenv
AI_PROVIDER=openai
AI_API_KEY=CLAVE_DE_OPENAI
AI_MODEL=gpt-4o-mini
AI_BASE_URL=
AI_JSON_MODE=
```

**Anthropic** (API nativa de Messages):

```dotenv
AI_PROVIDER=anthropic
AI_API_KEY=CLAVE_DE_ANTHROPIC
AI_MODEL=IDENTIFICADOR_DE_MODELO_CON_VISION
AI_BASE_URL=
AI_JSON_MODE=
```

**Servicio compatible con OpenAI**, incluido un servidor local:

```dotenv
AI_PROVIDER=openai_compatible
AI_API_KEY=CLAVE_DEL_SERVICIO
AI_MODEL=IDENTIFICADOR_DE_MODELO_CON_VISION
AI_BASE_URL=https://proveedor.example/v1
AI_JSON_MODE=false
```

Reemplaza los identificadores y la URL del ejemplo por los del servicio. Debe implementar Chat Completions y admitir imágenes mediante `image_url` con datos base64; la compatibilidad de texto por sí sola no basta. La clave puede quedar vacía en servidores locales sin autenticación. Desde Docker, `localhost` apunta al propio contenedor: utiliza una dirección alcanzable desde el backend.

Después de cambiar `.env`, recrea el backend para cargar las variables nuevas:

```bash
docker compose up -d --force-recreate backend
```

- `AI_API_KEY` y `AI_MODEL` tienen prioridad. Las instalaciones existentes pueden seguir usando `OPENAI_API_KEY` y `OPENAI_MODEL` con OpenAI. Anthropic también admite `ANTHROPIC_API_KEY`. Las variables específicas de un proveedor no se reutilizan para otros proveedores.
- Al cambiar de proveedor, actualiza también la clave y el modelo y limpia `AI_BASE_URL` si vuelves a OpenAI o Anthropic.
- `AI_JSON_MODE` vacío activa JSON mode con OpenAI y lo desactiva en servicios compatibles. Actívalo con `true` solo si el servicio lo admite. No se aplica al adaptador de Anthropic.
- `AI_TIMEOUT_SECONDS` limita la espera total (45 segundos por defecto, entre 1 y 90). `AI_MAX_TOKENS` limita la respuesta (6000 por defecto, entre 256 y 16384); el modelo puede imponer límites adicionales.
- Todos los proveedores usan las mismas validaciones y mantienen la revisión antes de guardar. Una respuesta incompleta o inválida se rechaza. No hay cambio automático a otro proveedor ni reintentos de pago automáticos.

Los adaptadores están en `backend/ai.py`; el resto de la aplicación usa una única función de extracción. Las claves permanecen en el backend. Referencias de los protocolos: [JSON mode de OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs) y [Messages de Anthropic](https://platform.claude.com/docs/en/api/messages/create).

### Migraciones y bases existentes

La revisión `0001` crea la extensión `pg_trgm`, las tablas y después los índices. Está versionada y no importa modelos cambiantes durante su ejecución. El antiguo `postgres/init.sql` ya no se monta en Compose.

No generar migraciones durante el despliegue ni copiar contraseñas a `alembic.ini`: la configuración versionada no contiene secretos.

**Si ya hay tablas creadas manualmente o migraciones locales anteriores**, guardar una copia y reconciliar ese esquema con la revisión inicial antes de ejecutar el nuevo Compose. Esta revisión inicial está destinada a una base vacía. No borrar el volumen ni ejecutar `alembic stamp` a ciegas para ocultar un conflicto. No hay una conversión automática de instalaciones antiguas desconocidas.

Para futuras actualizaciones con migraciones compatibles ya revisadas:

```bash
git pull --ff-only
docker compose build
docker compose run --rm migrate
docker compose up -d
```

## Proxy y acceso remoto

Los puertos se vinculan por defecto a `127.0.0.1`. Si el proxy está en otro host o LXC, cambiar `BIND_ADDRESS` a la dirección LAN del host de StalvIA y permitir acceso únicamente desde el proxy mediante las reglas de red correspondientes.

Adaptar `nginx/nginx.conf` al dominio y dirección del host reales. El ejemplo envía todo a `http://10.8.1.105:3000`; el nginx interno dirige `/api/` al backend y sirve correctamente rutas como `/history`.

Validar y recargar el nginx externo:

```bash
nginx -t
nginx -s reload
```

En Cloudflare Tunnel, dirigir el hostname público a **la dirección y puerto del nginx externo**, por ejemplo `http://<DIRECCION_NGINX>:80`. El proyecto no publica ningún servicio en el puerto 8080.

Crear también una aplicación y una política de Cloudflare Access para el usuario autorizado. El túnel no establece esa política por sí solo. Restringir el acceso directo al origen para evitar que se eluda Access. El backend no incluye cuentas de usuario propias.

Los proxies admiten cuerpos de hasta 9 MB para incluir el envoltorio multipart; el backend limita el archivo a 8 MB. Las comparaciones tienen un tiempo máximo por producto y pueden reintentarse sin perder el ticket.

## Datos y límites de las estadísticas

- Se conserva el total impreso de cada línea; no se sustituye por cantidad × precio.
- La misma imagen tiene un identificador único que evita volver a guardar ese archivo. Otra fotografía del mismo ticket puede requerir revisión manual.
- Los códigos de barras distinguen productos. Se eliminó la fusión automática por similitud textual. Los nombres sin código siguen sin acreditar equivalencia entre productos.
- Borrar una compra elimina sus líneas; las observaciones históricas se conservan.
- El histórico registra precios manuales y de tickets con su origen. Las líneas con descuentos o cantidades fraccionarias no entran automáticamente en el histórico de precios unitarios comparables.
- La estadística entre tiendas utiliza los últimos precios de una cesta común de productos con código de barras. Si no hay una cesta común entre al menos dos tiendas, no presenta una clasificación.
- No se almacenan las imágenes del ticket. Se envían al proveedor configurado para su lectura.

## Desarrollo y pruebas

Las dependencias directas de Python están fijadas en `backend/requirements.txt`; la interfaz usa `npm ci` y su archivo de bloqueo. Usar Python 3.12 y Node 22.12 o superior.

```bash
cd backend
python -m venv .venv
# Activar el entorno virtual según el sistema operativo
python -m pip install -r requirements-dev.txt
ruff check .
pytest -q
```

La prueba de integración con PostgreSQL requiere `TEST_POSTGRES_URL` apuntando a una base desechable ya migrada. Las demás pruebas aíslan la base y simulan OCR y conectores: no consumen llamadas de IA ni demuestran que una tienda esté disponible en vivo.

```bash
cd frontend
npm ci
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

GitHub Actions comprueba estilo, pruebas del backend, instalación y reinstalación del esquema en PostgreSQL 16, cálculos de la interfaz, flujo de revisión en navegador y construcción de contenedores. Consultar resultados actuales en [GitHub Actions](https://github.com/nunezruj88/stalvia/actions).

## Copias de seguridad

Guardar un volcado antes de actualizar. Por ejemplo, desde la raíz del proyecto:

```bash
mkdir -p backups
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > backups/stalvia.sql
```

Copiar los respaldos fuera del host y probar su restauración sobre una base independiente. La frecuencia y el destino de las copias dependen de la instalación; no hay una programación automática incluida.

## Pendiente

- Validar y mantener cada conector contra las tiendas reales y la ubicación elegida.
- Normalizar envases, pesos y volúmenes; tratar promociones complejas y devoluciones.
- Guardar equivalencias confirmadas con identificadores de tienda y metadatos de formato.
- Distinguir tiendas físicas de una misma cadena y canales de venta.
- Reanudar búsquedas después de cerrar la página mediante trabajos persistentes.
- Añadir alertas, listas de compra y almacenamiento opcional en R2.

## Uso y distribución

Proyecto destinado a uso personal. El repositorio no incluye un archivo de licencia independiente.
