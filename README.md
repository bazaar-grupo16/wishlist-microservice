# Wishlist Microservice

Microservicio de wishlist para la plataforma Bazaar. Permite a los usuarios guardar productos favoritos y consultar su lista enriquecida con datos del catálogo en tiempo real. Construido con FastAPI y PostgreSQL.

## Tabla de contenidos

- [Stack](#stack)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Endpoints](#endpoints)
  - [Health](#health)
  - [Wishlist](#wishlist)
  - [Autenticación](#autenticación)
- [Arquitectura en capas](#arquitectura-en-capas)
- [Integración con catalog-microservice](#integración-con-catalog-microservice)
- [Variables de entorno](#variables-de-entorno)
- [Tests](#tests)
- [CI/CD](#cicd)

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy |
| Base de datos | PostgreSQL (configurable por env vars) |
| Contenedor | Docker (multi-stage, non-root) |
| Orquestación | Kubernetes (DigitalOcean) |
| CI/CD | GitHub Actions → GHCR → DOKS |

## Estructura del proyecto

```
├── src/
│   ├── api/
│   │   ├── routers/
│   │   │   └── wishlist.py      # POST, DELETE, GET list, GET check
│   │   └── health.py            # /livez y /readyz
│   ├── core/
│   │   ├── catalog_client.py    # Cliente HTTP del catalog-service (degraded mode)
│   │   ├── config.py            # Configuración desde variables de entorno
│   │   ├── database.py          # Engine, sesión, base declarativa y retry de conexión
│   │   ├── dependencies.py      # DbSession, UserID, get_catalog_client
│   │   ├── logging.py           # Logging estructurado JSON
│   │   └── utils.py             # utc_now()
│   ├── exceptions/
│   │   └── __init__.py          # WishlistItemNotFoundError, WishlistItemAlreadyExistsError
│   ├── models/
│   │   ├── __init__.py          # Re-export de modelos
│   │   └── wishlist.py          # WishlistItem ORM (tabla wishlist_items)
│   ├── repositories/
│   │   ├── __init__.py          # Re-export de repositorios
│   │   └── wishlist.py          # WishlistRepository: add, remove, list_by_user, exists
│   ├── schemas/
│   │   ├── __init__.py          # Re-export de schemas públicos
│   │   └── wishlist.py          # Pydantic schemas de request y response
│   ├── services/
│   │   ├── __init__.py          # Re-export de servicios
│   │   └── wishlist.py          # WishlistService: orquesta repo + catalog client
│   └── main.py                  # Punto de entrada, registro de routers
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── test_wishlist.py         # 20 tests de integración contra PostgreSQL real
├── scripts/
│   ├── run_tests.sh             # Wrapper para correr tests (Linux/macOS)
│   └── run_tests.ps1            # Wrapper para correr tests (Windows)
├── k8s/
│   ├── app-deployment.yaml
│   ├── app-service.yaml
│   ├── db-deployment.yaml
│   ├── db-service.yaml
│   ├── db-pvc.yaml
│   ├── ingress.yaml
│   └── secret.yaml              # ⚠️ Template — NO commitear valores reales
├── .github/workflows/
│   ├── ci-dev.yml               # Pipeline CI en rama dev
│   └── deploy.yml               # Pipeline de deploy a DOKS
├── Dockerfile
├── Dockerfile.test
├── docker-compose.test.yml
├── requirements.txt
└── .env.example
```

## Endpoints

### Health

| Método | Path | Descripción | Respuesta exitosa |
|--------|------|-------------|-------------------|
| `GET` | `/livez` | Liveness probe — proceso vivo | `200 {"status": "alive"}` |
| `GET` | `/readyz` | Readiness probe — BD alcanzable | `200 {"status": "ready"}` / `503 {"status": "unavailable"}` |

---

### Wishlist

El Ingress publica estos endpoints bajo el prefijo `/wishlist` y reescribe la request hacia FastAPI sin ese prefijo. Por ejemplo, `GET /wishlist/items` llega internamente como `GET /items`.

Todos los endpoints requieren el header interno `X-User-ID: <uuid>` (ver [Autenticación](#autenticación)). El frontend envía `Authorization: Bearer <token>` y el gateway/auth debe propagar `X-User-ID` al microservicio.

#### `POST /wishlist/items` — Agregar producto a la wishlist

**Body JSON:**
```json
{ "product_id": "b3d1a2c4-1234-5678-abcd-000000000001" }
```

**Respuesta `201`:**
```json
{
  "id": "a1b2c3d4-0000-0000-0000-000000000001",
  "user_id": "u1u1u1u1-0000-0000-0000-000000000001",
  "product_id": "b3d1a2c4-1234-5678-abcd-000000000001",
  "added_at": "2024-01-01T12:00:00Z"
}
```

| Código | Motivo |
|--------|--------|
| `201` | Item agregado correctamente |
| `401` | Header `X-User-ID` ausente o no es un UUID válido |
| `409` | El producto ya está en la wishlist del usuario |

---

#### `DELETE /wishlist/items/{product_id}` — Quitar producto de la wishlist

**Respuesta `204`:** sin contenido.

| Código | Motivo |
|--------|--------|
| `204` | Item eliminado correctamente |
| `401` | Header `X-User-ID` ausente o inválido |
| `404` | El producto no está en la wishlist del usuario |

---

#### `GET /wishlist/items` — Listar wishlist del usuario

Devuelve los items de la wishlist enriquecidos con datos del catálogo. Si el catálogo no está disponible, los items igual se devuelven en modo degradado (ver [Integración con catalog-microservice](#integración-con-catalog-microservice)).

**Respuesta `200`:**
```json
{
  "items": [
    {
      "id": "a1b2c3d4-0000-0000-0000-000000000001",
      "user_id": "u1u1u1u1-0000-0000-0000-000000000001",
      "product_id": "b3d1a2c4-1234-5678-abcd-000000000001",
      "added_at": "2024-01-01T12:00:00Z",
      "name": "Campera de cuero",
      "price": 150.0,
      "image_url": "https://cdn.example.com/img.jpg",
      "in_stock": true,
      "is_available": true,
      "catalog_available": true
    }
  ],
  "total": 1
}
```

| Código | Motivo |
|--------|--------|
| `200` | Lista devuelta (puede estar vacía) |
| `401` | Header `X-User-ID` ausente o inválido |

---

#### `GET /wishlist/items/{product_id}/check` — Verificar si un producto está en la wishlist

**Respuesta `200`:**
```json
{ "in_wishlist": true }
```

| Código | Motivo |
|--------|--------|
| `200` | Verificación exitosa (`in_wishlist: true/false`) |
| `401` | Header `X-User-ID` ausente o inválido |

---

### Autenticación

El API Gateway valida el JWT recibido como `Authorization: Bearer <token>` y propaga el ID del usuario autenticado como header interno `X-User-ID: <uuid>`. Este microservicio únicamente verifica que el header esté presente y sea un UUID válido — no procesa JWTs directamente.

| Caso | Código | Detalle |
|------|--------|---------|
| Header ausente | `401` | `Missing X-User-ID header` |
| Valor no-UUID | `401` | `Invalid X-User-ID header` |

## Arquitectura en capas

```
HTTP Request
    ↓
Router          → valida X-User-ID, delega al service
    ↓
Service         → orquesta repo + catalog client; lanza excepciones de dominio
    ├──→ Repository      → único lugar que construye queries SQL
    │        └──→ PostgreSQL (tabla wishlist_items)
    └──→ CatalogClient   → GET /products/{id} al catalog-microservice
```

**Regla de dependencias:** cada capa solo conoce a la inmediatamente inferior. El service no importa nada de FastAPI. El router no tiene lógica de negocio ni acceso directo a la base de datos.

**Excepciones de dominio:** el repositorio lanza `WishlistItemNotFoundError` y `WishlistItemAlreadyExistsError`. El router las captura y las convierte a 404 y 409 respectivamente.

## Integración con catalog-microservice

`CatalogClient` (`src/core/catalog_client.py`) realiza `GET /products/{product_id}` al catalog-service para enriquecer cada item con nombre, precio, imagen y disponibilidad.

**Degraded mode:** si el catálogo falla por cualquier motivo (timeout de 3s, error HTTP, caída del servicio), el cliente nunca propaga la excepción. Registra un warning y el service devuelve el item con:

```json
{
  "catalog_available": false,
  "name": null,
  "price": null,
  "image_url": null,
  "in_stock": null,
  "is_available": null
}
```

El usuario siempre recibe su lista completa, incluso cuando el catálogo no está disponible.

## Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DB_HOST` | Host de PostgreSQL | — (requerido) |
| `DB_PORT` | Puerto de PostgreSQL | `5432` |
| `DB_USER` | Usuario de la base de datos | — (requerido) |
| `DB_PASSWORD` | Contraseña de la base de datos | — (requerido) |
| `DB_NAME` | Nombre de la base de datos | — (requerido) |
| `CATALOG_SERVICE_URL` | URL base del catalog-microservice | `http://catalog-service` |
| `LOG_LEVEL` | Nivel de logging | `info` |
| `APP_NAME` | Nombre de la aplicación | `wishlist-service` |

Copiar `.env.example` a `.env` para desarrollo local.

## Tests

Los tests corren contra una **base de datos PostgreSQL real** usando Docker Compose. No se usa mocking de base de datos. El degraded mode se prueba sobreescribiendo la dependencia `get_catalog_client` con una URL inaccesible.

El archivo `docker-compose.test.yml` levanta:
1. Un contenedor **PostgreSQL 16** como base de datos.
2. Un contenedor **test-runner** que ejecuta `pytest` contra esa base de datos.

### Correr los tests

```bash
# Linux / macOS
./scripts/run_tests.sh

# Windows (PowerShell)
.\scripts\run_tests.ps1

# O directamente con Docker Compose v2, si está instalado
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner

# Limpiar contenedores
docker compose -f docker-compose.test.yml down -v

# Si tu entorno todavía usa Docker Compose v1
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner
docker-compose -f docker-compose.test.yml down -v
```

## CI/CD

### `ci-dev.yml` — Pipeline de CI en rama `dev`

Se ejecuta en cada push o PR a `dev` cuando cambian archivos en `src/`, `tests/` o archivos de build.

| Job | Descripción |
|-----|-------------|
| `lint` | Ruff sobre `src/` y `tests/` |
| `sast` | Bandit (análisis estático de seguridad) sobre `src/` |
| `test` | Tests contra PostgreSQL real vía Docker Compose |

### `deploy.yml` — Pipeline de deploy a DOKS en rama `main`

| Job | Se ejecuta cuando cambia... |
|-----|----------------------------|
| `lint` | `src/`, `tests/`, archivos de build |
| `test` | `src/`, `tests/`, archivos de build |
| `build` | `src/`, `tests/`, archivos de build (solo push a main) |
| `deploy` | `src/` **o** `k8s/` (solo push a main) |

### Variables de entorno requeridas (GitHub Secrets)

| Secret | Descripción |
|--------|-------------|
| `DIGITALOCEAN_ACCESS_TOKEN` | Personal Access Token de DigitalOcean |
| `DOKS_CLUSTER_NAME` | Nombre del cluster DOKS |
| `DB_USER` | Usuario de la base de datos |
| `DB_PASSWORD` | Contraseña de la base de datos |
| `DB_NAME` | Nombre de la base de datos |

`DB_HOST` y `DB_PORT` están fijos en `k8s/secret.yaml` (`wishlist-db:5432`) ya que la BD corre dentro del cluster.

## Conexión a la base de datos

Al iniciar, la aplicación espera a que la base de datos esté disponible usando **backoff exponencial** (1s → 2s → 4s → … hasta 30s por intento, máximo 5 minutos en total) antes de crear las tablas y aceptar tráfico. Esto evita crasheos durante el arranque del pod cuando la BD aún está inicializándose.
