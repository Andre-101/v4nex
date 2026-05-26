# 24 - App GHCR publish and pull/check

## Resumen ejecutivo

Este escenario publico las imagenes productivas de backend y frontend en GHCR con tag fijo, valido pull/check desde GHCR y mantuvo el alcance cerrado: no hubo deploy, no se ejecuto `docker compose up`, no se emitio TLS, no se ejecuto ACME, no se llamo Cloudflare API y no se modifico DNS publico.

Tag usado:

```text
scenario-23-app-images
```

Imagenes publicadas:

```text
ghcr.io/andre-101/v4nex-backend:scenario-23-app-images
ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images
```

## Digests

Backend:

```text
ghcr.io/andre-101/v4nex-backend@sha256:04f2523eeb8c06f487729e8ffd0998c0082ce271aa7a180e054b2bbd54698843
```

Frontend:

```text
ghcr.io/andre-101/v4nex-frontend@sha256:27f607df58f1e4134246e89873035fd70a4344f6fe2c688383351a8c9aa8d690
```

## Pruebas backend

Se ejecuto:

```bash
cd apps/backend
python -m pytest -p no:cacheprovider
```

Resultado:

```text
99 passed, 1 warning in 14.22s
```

La advertencia corresponde a `python_multipart`/Starlette y no bloqueo este escenario.

## Pruebas frontend

Se ejecuto:

```bash
cd apps/frontend
npm install
npm run build
```

Resultado:

```text
npm install: up to date, audited 136 packages; 2 moderate severity vulnerabilities
npm run build: OK, 31 modules transformed
dist/index.html 0.41 kB
dist/assets/index-D6ciBfGJ.css 5.86 kB
dist/assets/index-DEelUKdS.js 143.02 kB
```

Las vulnerabilidades npm moderadas quedan pendientes de seguimiento; no hubo reporte high/critical en npm durante este escenario.

## Remediaciones antes del push

El primer scan local bloqueo el push:

- Backend tenia HIGH en `starlette` y metadata vendorizada de `wheel`.
- Frontend tenia CRITICAL/HIGH en la base Nginx Alpine.

Cambios aplicados:

- Backend:
  - `fastapi==0.121.3`
  - `starlette==0.49.1`
  - `PyJWT==2.12.0`
  - `pytest==9.0.3`
  - `apt-get upgrade` en build productivo.
  - `pip`, `setuptools` y `wheel` se desinstalan del runtime final tras instalar dependencias.
- Frontend:
  - Runtime actualizado a `nginx:1.29.3-alpine`.
  - `apk upgrade --no-cache`.
  - `curl` eliminado del runtime final.

## Build/check/tag local

Se ejecuto:

```bash
bash -n scripts/build-app-images-local.sh
bash -n scripts/check-app-images-local.sh
bash -n scripts/tag-app-ghcr.sh
bash -n scripts/push-app-ghcr.sh
bash -n scripts/check-app-ghcr-images.sh

APP_IMAGE_TAG=scenario-23-app-images bash scripts/build-app-images-local.sh
APP_IMAGE_TAG=scenario-23-app-images bash scripts/check-app-images-local.sh
APP_IMAGE_TAG=scenario-23-app-images bash scripts/tag-app-ghcr.sh
```

Resultado:

```text
Local app images built successfully.
OK backend /health
OK frontend static root
GHCR tags created locally.
No push was performed during tag.
```

## Scan local

Docker Scout local despues de remediacion:

Backend CRITICAL/HIGH:

```text
Target: ghcr.io/andre-101/v4nex-backend:scenario-23-app-images
digest: 04f2523eeb8c
vulnerabilities: 0C 0H 0M 0L
No vulnerable packages detected
```

Frontend CRITICAL/HIGH:

```text
Target: ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images
digest: 27f607df58f1
vulnerabilities: 0C 0H 0M 0L
No vulnerable packages detected
```

## Push GHCR

Se ejecuto push real controlado con confirmacion explicita:

```bash
CONFIRM_PUSH=I_UNDERSTAND_PUSH_GHCR APP_IMAGE_TAG=scenario-23-app-images bash scripts/push-app-ghcr.sh
```

Resultado:

```text
GHCR app image push completed.
No deploy, compose up, TLS issuance, or Cloudflare API call was performed.
```

Digests publicados:

```text
backend:  sha256:04f2523eeb8c06f487729e8ffd0998c0082ce271aa7a180e054b2bbd54698843
frontend: sha256:27f607df58f1e4134246e89873035fd70a4344f6fe2c688383351a8c9aa8d690
```

## Pull/check desde GHCR

Se ejecuto:

```bash
APP_IMAGE_TAG=scenario-23-app-images bash scripts/check-app-ghcr-images.sh
```

Resultado:

```text
docker pull backend: OK
docker pull frontend: OK
backend dependencies ok
nginx version: nginx/1.29.3
GHCR app image checks passed.
No deploy, compose up, TLS issuance, or Cloudflare API call was performed.
```

## Scan GHCR

Docker Scout sobre imagenes publicadas:

Backend completo:

```text
0C 0H 1M 22L 4?
```

Backend CRITICAL/HIGH:

```text
0C 0H 0M 0L
No vulnerable packages detected
```

Frontend completo:

```text
0C 0H 5M 0L
```

Frontend CRITICAL/HIGH:

```text
0C 0H 0M 0L
No vulnerable packages detected
```

## Decision Go/No-Go

GO tecnico para validacion de pull desde VPS en el siguiente escenario.

Condiciones:

- No se uso `latest`.
- Backend/frontend estan publicados en GHCR con tag fijo.
- Pull/check desde GHCR fue exitoso.
- Docker Scout no reporta CRITICAL/HIGH en backend ni frontend.
- Vulnerabilidades medium/low/unspecified quedan como riesgo pendiente, no bloqueante para este escenario.

No es autorizacion para deploy ni para levantar compose.

## Confirmaciones de alcance

- No se ejecuto `docker compose up`.
- No se ejecuto `docker compose up -d`.
- No se hizo deploy.
- No se emitio TLS.
- No se ejecuto ACME.
- No se llamo Cloudflare API.
- No se modifico DNS publico.
- No se creo CI/CD.
- No se agregaron secretos.
- No se toco `.env.production`.

## SYNC app -> infra - Ronda 3

### Imagenes publicadas

Backend:

```text
ghcr.io/andre-101/v4nex-backend:scenario-23-app-images
ghcr.io/andre-101/v4nex-backend@sha256:04f2523eeb8c06f487729e8ffd0998c0082ce271aa7a180e054b2bbd54698843
```

Frontend:

```text
ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images
ghcr.io/andre-101/v4nex-frontend@sha256:27f607df58f1e4134246e89873035fd70a4344f6fe2c688383351a8c9aa8d690
```

Caddy ya validado previamente:

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6
```

### Estado real

- Backend image publicada: SI.
- Frontend image publicada: SI.
- Pull/check GHCR desde app: exitoso.
- Pull/check desde VPS: pendiente.

### Preflight recomendado para infra

Sin levantar servicios:

```bash
cd /opt/v4nex/app
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker pull ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
docker pull ghcr.io/andre-101/v4nex-backend:scenario-23-app-images
docker pull ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images
docker run --rm ghcr.io/andre-101/v4nex-backend:scenario-23-app-images python -c "import fastapi, sqlalchemy, alembic; print('backend dependencies ok')"
docker run --rm ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images nginx -v
```

No autorizado todavia:

```bash
docker compose up
docker compose up -d
docker compose up -d --build
```

### Advertencias

- Todavia NO se autoriza `docker compose up`.
- Todavia NO se autoriza deploy.
- Todavia NO se autoriza TLS/ACME.
- Todavia NO se autoriza Cloudflare API.
- Todavia NO se autoriza modificacion DNS publico.
- No construir imagenes en VPS.
- No usar `latest`.

### Pendientes para validacion desde VPS

- `docker pull` backend desde VPS.
- `docker pull` frontend desde VPS.
- Validar backend dependencies desde VPS.
- Validar `nginx -v` desde VPS.
- Opcional: Docker Scout desde VPS.
- Mantener el flujo sin `docker compose up`.

## Pendientes para Escenario 25

- Validar pull/check de backend y frontend desde VPS.
- Verificar digests desde VPS.
- Mantener Caddy/backend/frontend/db sin levantar servicios todavia.
- Definir siguiente autorizacion explicita antes de cualquier `docker compose up`.
