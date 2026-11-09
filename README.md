# AD Mail Nexus Manager — fase 1

Backend de la aplicación interna. Esta entrega implementa la base, usuarios, roles,
sesiones y solicitudes de demostración. **No ejecuta campañas ni envía mensajes.**
NEXUS 360° es un sistema externo: no se duplicaron su registro ni sus resultados.

## Requisitos

- Python **3.14**, `uv` y PostgreSQL **18** (o Docker Compose para la base).
- Node.js 22.12+ o 24 para el repositorio frontend `AD-Mail-Mexus-main`.
- Las versiones exactas del backend están fijadas en `uv.lock`.

## Inicio rápido: backend local y PostgreSQL en Docker

Ejecute desde esta carpeta:

```bash
cp .env.example .env
uv python install 3.14
uv sync --frozen
```

Edite `.env`: reemplace `CAMBIAR` por una contraseña propia en **ambas** variables
`POSTGRES_PASSWORD` y `DATABASE_URL`. Use una contraseña alfanumérica aleatoria
para evitar problemas de codificación en la URL. Mantenga `DEMO=true` y
`COOKIE_SEGURA=false` exclusivamente para esta prueba local por HTTP.
No hay usuario ni contraseña predefinidos en el proyecto.

```bash
docker compose up -d postgres
uv run python -m scripts.migrar
uv run python -m scripts.crear_usuario --correo admin@suempresa.co --nombre Administrador --rol admin
uv run python -m scripts.sembrar_demo
uv run uvicorn app.main:crear_app --factory --host 127.0.0.1 --port 8000 --reload --no-access-log
```

El comando de creación pide la contraseña de forma oculta y exige al menos 12
caracteres y confirmación. No sobrescribe usuarios existentes. Para crear un gestor:

```bash
uv run python -m scripts.crear_usuario --correo gestor@suempresa.co --nombre Gestor --rol gestor_anuncios
```

Arranque el frontend en otra terminal, desde su carpeta:

```bash
npm ci
cp .env.example .env
npm run dev
```

Abra **http://localhost:5173/panel/login** e ingrese con el usuario creado.
Use `localhost`, como indica `CORS_ORIGINS`. Vite reenvía `/api` al backend sin
exponer tokens al código JavaScript. La API se comprueba en
**http://127.0.0.1:8000/api/health** y su documentación está en `/docs`.

Si ya dispone de PostgreSQL, configure su URL en `.env` y omita el comando de
Docker para la base. Las migraciones se ejecutan explícitamente; el servidor no
modifica el esquema al arrancar.

## Backend completamente en Docker

Después de configurar `.env`:

```bash
docker compose up -d postgres
docker compose build api
docker compose run --rm api uv run --no-sync python -m scripts.migrar
docker compose run --rm api uv run --no-sync python -m scripts.crear_usuario --correo admin@suempresa.co --nombre Administrador --rol admin
docker compose run --rm api uv run --no-sync python -m scripts.sembrar_demo
docker compose up -d api
```

El frontend se ejecuta con los comandos anteriores. `docker compose down` detiene
los servicios y conserva el volumen de datos; no use `--volumes` si desea conservarlo.

## Worker

El servicio separado `worker` está reservado bajo el perfil `fase4`. Todavía no hay
cola, programador ni ejecutores. No se inicia con `docker compose up -d`.

```bash
uv run python -m app.tareas.worker
```

Este comando termina con una explicación de que corresponde a la fase 4; **no es
un worker operativo**. No active su perfil antes de implementar esa fase.

## Probar

Pruebas unitarias (no necesitan PostgreSQL):

```bash
uv run pytest -q -m "not integracion"
uv run ruff check .
uv run ruff format --check .
```

Pruebas de integración con una **base exclusiva de pruebas**, cuyo nombre debe
terminar en `_test`. Las pruebas eliminan las filas de esa base; no use la base de
trabajo. Para crearla con el PostgreSQL de Compose, una sola vez:

```bash
docker compose exec postgres createdb -U nexus nexus_test
```

Configure `TEST_DATABASE_URL` en su `.env` con la contraseña elegida y la base
`nexus_test`; después ejecute:

```bash
uv run pytest -q
```

Si no define `TEST_DATABASE_URL`, las nueve pruebas de integración se marcan como
omitidas. La base principal `DATABASE_URL` no se utiliza para estas pruebas.

En el frontend:

```bash
npm test
npm run build
```

Validación de esta entrega: **12 pruebas backend aprobadas** (3 unitarias y 9 de
integración contra PostgreSQL 18.6) con Python 3.14.9; **6 pruebas frontend aprobadas**
y compilación TypeScript/Vite correcta. Se revisaron visualmente el login y la
pantalla 01, además de filtros y búsqueda, con datos ficticios en un montaje de
prueba aislado. La autenticación y las consultas reales se verificaron por pruebas
HTTP de integración; no se realizó un inicio de sesión completo en el navegador.
Docker Compose se entrega configurado, pero no se ejecutó Docker en este entorno.

Las pruebas cubren: hash Argon2 y token opaco, cierre y expiración de sesión,
usuarios desactivados, permisos, intentos concurrentes, protección CSRF, CORS,
contrato de errores, migraciones y semilla idempotentes, filtros, paginación,
búsqueda y separación entre demostración y datos reales.

## Modo demostración

```bash
uv run python -m scripts.sembrar_demo
```

Con `DEMO=true`, prepara para la fecha actual en **America/Bogota** los indicadores
37 / 12 / 9 / 14 / 2, los tres planes pendientes (solo contador), la serie de 14 días
y las ocho empresas del mockup. Puede repetirse sin duplicar filas. Repítalo al
cambiar de día para que el filtro «Hoy» siga mostrando la muestra.

Los indicadores reproducen los totales de referencia; las ocho filas son una
**muestra**, no 37 solicitudes completas. La pantalla identifica la muestra y la
barra lateral muestra «Datos de demostración». Las temperaturas copiadas del
mockup son datos visuales, no el resultado del futuro motor de calificación.
Con `DEMO=false` se excluyen estas filas y agregados; la entrada real de eventos
se implementará en la fase 2.

## API disponible

| Método | Ruta | Acceso |
|---|---|---|
| POST | `/api/auth/login` | Público; límite por correo e IP |
| POST | `/api/auth/logout` | Sesión activa |
| GET | `/api/auth/me` | Sesión activa |
| GET | `/api/solicitudes` | Admin y gestor; fecha, tipo, origen, estado, pagina, tamano |
| GET | `/api/solicitudes/resumen` | Admin y gestor; indicadores y serie |
| GET | `/api/solicitudes/opciones` | Admin y gestor; opciones de filtros |
| GET | `/api/buscar?q=` | Admin y gestor; empresas/solicitudes, máximo 10 coincidencias |
| GET | `/api/pendientes` | Admin y gestor; contador demo o cero en modo real |
| GET | `/api/health` | Público; conexión a PostgreSQL |

Los errores tienen la forma `{"codigo": "...", "mensaje": "..."}`.
El login recibe `{"correo":"...","contrasena":"..."}`. Las escrituras de
autenticación requieren `X-Nexus-Request: 1` y un `Origin` permitido, si existe.
La cookie `nexus_sesion` es HttpOnly, SameSite=Strict y limitada a `/api`.
La base almacena únicamente SHA-256 del token aleatorio, nunca el token en claro.
No hay tokens en localStorage ni credenciales predeterminadas.

## Configuración

| Variable | Uso / valor inicial |
|---|---|
| `DATABASE_URL` | Obligatoria; conexión PostgreSQL |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL para Compose |
| `DEMO` | `false` por defecto; `.env.example` activa demostración |
| `CORS_ORIGINS` | Lista JSON de orígenes exactos; inicialmente localhost:5173 |
| `COOKIE_SEGURA` | `true` por defecto; `false` solo en HTTP local |
| `SESION_HORAS` | 8; rango permitido 1–168 |
| `LOGIN_MAX_INTENTOS` | 5 fallos por ventana, por correo e IP |
| `LOGIN_VENTANA_MINUTOS` | 15 |
| `NOMBRE_PRODUCTO` | Nombre interno reservado en backend |
| `TEST_DATABASE_URL` | Base exclusiva de integración, terminada en `_test` |
| `IA_PROVEEDOR`, `GEMINI_MODELO`, `GEMINI_API_KEY` | Reservadas para fase 3; todavía no se usa IA |
| `EVENTOS_TOKEN` | Reservada para fase 2 |
| `LISTMONK_URL`, `LISTMONK_USUARIO`, `LISTMONK_TOKEN` | Reservadas para fase 4 |

Las variables futuras no habilitan integraciones en esta entrega. Los demás
adaptadores documentarán sus credenciales en la fase en que se implementen.
En un despliegue real se necesita HTTPS, `COOKIE_SEGURA=true`, CORS del dominio
real y un proxy que sirva frontend y `/api` bajo el mismo origen. Configure la
confianza en cabeceras de proxy solo para su proxy conocido; el límite por IP no
confía por defecto en direcciones arbitrarias enviadas por clientes.

## Decisiones y archivos nuevos

- Se respetó la estructura entregada. `001_esquema.sql` contiene usuarios, roles,
  sesiones e intentos; `003_solicitudes.sql` contiene las solicitudes y agregados
  ficticios de la pantalla 01. Las demás migraciones están reservadas y **no se
  registran como aplicadas** hasta contener SQL. El rol se restringe por CHECK.
- Se añadió `scripts/migrar.py` para ejecutar migraciones con bloqueo PostgreSQL y
  registro de aplicación, y `scripts/crear_usuario.py` para el primer acceso seguro
  sin inventar un flujo de invitaciones antes de la fase 5.
- `scripts/sembrar_demo.py` implementa la semilla solicitada. Los `__init__.py`
  añadidos permiten ejecutar scripts y pruebas como módulos.
- `Dockerfile` y `.dockerignore` permiten construir el contenedor sin incluir
  secretos. `.python-version` fija la rama 3.14 y `uv.lock` fija las dependencias.
- `tests/test_security.py` y `tests/test_base_integracion.py` verifican la fase 1;
  los archivos vacíos de pruebas futuras se conservan, sin fingir cobertura.
- Se añadió `/solicitudes/opciones` para poblar filtros desde la API.
- Se usó la variante de sesión con cookie HttpOnly y cabecera contra CSRF. El
  gestor puede consultar solicitudes; el guard reutilizable deniega agentes y
  reglas, y también se prueba del lado servidor.
- No se añadieron ORM, Redis, proveedores externos ni servicios de analítica.
- La fuente Inter se distribuye con el frontend y no se descarga desde Google.

## Pendiente por fase

2. Eventos idempotentes de NEXUS 360°, contactos, calificación y solicitudes reales.
3. Estratega, Gemini/simulado, planes, versiones, bandeja y editor React Flow.
4. Cola PostgreSQL, worker, cumplimiento, presupuesto y correo Listmonk.
5. Agentes, gráficas, reglas, equipo e invitaciones.
6. Página pública, seguimiento, WhatsApp, calendario y demás canales.

La entrega se detiene al final de la fase 1, como exige el encargo.
