# 23 - App images, compose productivo propuesto y SYNC Ronda 2

## Resumen ejecutivo

Este escenario prepara los artefactos que infra necesita para la Ronda 2 de sincronizacion app -> infra:

- Dockerfiles productivos separados para backend y frontend.
- Imagenes backend/frontend construidas y taggeadas localmente con tag fijo.
- `docker-compose.prod.yml` propuesto, sin `build` y sin `latest`.
- `.env.production.example` alineado a variables productivas finales.
- Caddy productivo apuntando a frontend interno en puerto `80`.
- Scripts seguros para build/check/tag/push/check GHCR de app images.

No se hizo deploy, no se ejecuto `docker compose up`, no se emitio TLS, no se ejecuto ACME, no se llamo Cloudflare API, no se modifico DNS publico y no se construyo nada en la VPS.

## Decisiones tomadas

- Backend:
  - Imagen esperada: `ghcr.io/andre-101/v4nex-backend:scenario-23-app-images`
  - Runtime interno: FastAPI/Uvicorn en puerto `8000`.
  - Dockerfile productivo separado: `apps/backend/Dockerfile.prod`.
  - No usa `--reload`.
  - Healthcheck: `GET /health`.

- Frontend:
  - Imagen esperada: `ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images`
  - Se descarta Vite dev server para produccion.
  - Se usa `npm run build` y Nginx interno.
  - Puerto interno: `80`.
  - Dockerfile productivo separado: `apps/frontend/Dockerfile.prod`.
  - Healthcheck: HTTP interno a `/`.

- Caddy:
  - Imagen validada: `ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean`
  - Digest validado desde VPS: `sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6`
  - Publica solo `80` y `443`.
  - Admin API `2019` queda solo expuesta dentro de Docker, no al host.

## Servicios internos

- `caddy`: unico servicio publico HTTP/HTTPS.
- `frontend`: servicio estatico interno, no publica puerto al host.
- `backend`: API interna, no publica puerto al host.
- `db`: PostgreSQL interno, no publica puerto al host.

## Puertos

Publicos al host:

- `80:80`
- `443:443`

Privados/internos:

- Caddy Admin API: `2019`, solo red Docker.
- Backend: `8000`, solo red Docker.
- Frontend: `80`, solo red Docker.
- Postgres: `5432`, solo red Docker.

No se publica `2019`, `5432`, `8000` ni `5173`.

## Imagenes GHCR

- Caddy: `ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean`
- Backend: `ghcr.io/andre-101/v4nex-backend:scenario-23-app-images`
- Frontend: `ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images`

Estado:

- Caddy: publicada y validada desde VPS.
- Backend/frontend: construidas y taggeadas localmente; push GHCR no ejecutado en este escenario.

## Variables requeridas

Interfaz productiva esperada en `.env.production`, creado manualmente en VPS y no versionado:

```env
APP_ENV=production
DOMAIN=v4nex.com
CADDY_DOMAIN=v4nex.com
CADDY_IMAGE_TAG=scenario-21-scratch-clean
BACKEND_IMAGE_TAG=scenario-23-app-images
FRONTEND_IMAGE_TAG=scenario-23-app-images
POSTGRES_DB=v4nex
POSTGRES_USER=v4nex
POSTGRES_PASSWORD=<real-secret>
JWT_SECRET=<real-secret>
CLOUDFLARE_API_TOKEN=<real-secret>
CADDY_ACME_EMAIL=<real-email>
BACKEND_PORT=8000
```

Mapeo interno en compose:

- `JWT_SECRET` -> `JWT_SECRET_KEY`
- `DOMAIN` -> `PUBLIC_DOMAIN`
- `POSTGRES_*` -> `DATABASE_URL`

## Volumenes persistentes

- `postgres_data`: datos de Postgres.
- `caddy_data`: datos runtime de Caddy.
- `caddy_config`: configuracion runtime de Caddy.

## Redes Docker

- `edge`: Caddy, frontend y backend.
- `control`: Caddy, backend y db. Marcada como `internal: true`.

## Healthchecks

- `db`: `pg_isready`.
- `backend`: `python -c` contra `http://127.0.0.1:8000/health`.
- `frontend`: `wget -qO- http://127.0.0.1/`.
- `caddy`: `caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile`.

## Necesidades Caddy

- `infra/caddy/Caddyfile.prod.example` usa plataforma en `{$DOMAIN}`.
- Rutas API/control plane:
  - `/_v4nex/*` -> `backend:{$BACKEND_PORT}`
  - `/health` -> `backend:{$BACKEND_PORT}`
- Frontend:
  - resto del trafico -> `frontend:80`
- Clientes:
  - `*.v4nex.com` queda para rutas dinamicas posteriores via Caddy Admin API.
- No usar `panel.v4nex.com`, `api.v4nex.com` ni `status.v4nex.com`.

## Estrategia rsync propuesta

La VPS ya tiene `.env.production` manual. No debe copiarse ni sobrescribirse desde local.

Ruta base esperada:

```text
/opt/v4nex/app
```

Exclusiones rsync recomendadas:

```text
.git/
.env
.env.production
.env.local
.env.development
.env.*.local
!.env.example
!.env.production.example
node_modules/
dist/
.venv/
__pycache__/
.pytest_cache/
*.pyc
*.log
```

## Comandos preflight propuestos para infra

Sin levantar servicios:

```bash
cd /opt/v4nex/app
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker pull ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
docker run --rm ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean caddy version
docker run --rm ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean caddy list-modules
```

Pendiente hasta Escenario 24, solo despues de que app confirme publicacion GHCR de backend/frontend:

```bash
docker pull ghcr.io/andre-101/v4nex-backend:scenario-23-app-images
docker pull ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images
docker run --rm ghcr.io/andre-101/v4nex-backend:scenario-23-app-images python -c "import fastapi, sqlalchemy, alembic; print('backend dependencies ok')"
docker run --rm ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images nginx -v
```

Infra no debe intentar `docker pull` de backend/frontend hasta que app confirme que esas imagenes fueron publicadas en GHCR. El unico pull GHCR ya validado desde VPS es Caddy custom.

No ejecutar:

```bash
docker compose up
docker compose up -d
docker compose up -d --build
```

## Validaciones locales ejecutadas

Backend:

```text
99 passed, 1 warning in 7.59s
```

Frontend:

```text
npm install: OK, 2 moderate severity vulnerabilities reported by npm audit
npm run build: OK
```

Docker app images:

```text
bash -n scripts/build-app-images-local.sh: OK
bash -n scripts/check-app-images-local.sh: OK
bash -n scripts/tag-app-ghcr.sh: OK
bash -n scripts/push-app-ghcr.sh: OK
bash -n scripts/check-app-ghcr-images.sh: OK
bash scripts/build-app-images-local.sh: OK
bash scripts/check-app-images-local.sh: OK
APP_IMAGE_TAG=scenario-23-app-images bash scripts/tag-app-ghcr.sh: OK, no push
```

Compose:

```text
docker compose --env-file .env.production.example -f docker-compose.prod.yml config: OK
docker compose --env-file .env.production.example -f docker-compose.prod.example.yml config: OK
```

Static checks:

- `docker-compose.prod.yml` no contiene `build:`.
- `docker-compose.prod.yml` no contiene `latest`.
- `docker-compose.prod.yml` no publica `2019`, `5432`, `8000` ni `5173`.
- Publica solo `80:80` y `443:443`.

## Riesgos

- Backend/frontend aun no fueron publicados en GHCR en este escenario.
- `npm install` reporto 2 vulnerabilidades moderadas en dependencias frontend.
- `docker-compose.prod.yml` es propuesta revisable, no declaracion de produccion lista.
- TLS/ACME/Cloudflare API siguen pendientes.
- Admin API de Caddy debe permanecer privada; exponer `2019` seria critico.
- `.env.production` real no debe entrar al repo ni al rsync desde local.

## Siguiente paso recomendado

Infra debe revisar el bloque SYNC, confirmar si acepta la estructura propuesta, y pedir a app publicar backend/frontend en GHCR con confirmacion explicita si la ronda queda aprobada.

No declarar produccion lista todavia.

## SYNC app -> infra — Ronda 2

### Estructura real del repo para rsync

```text
apps/backend/
  Dockerfile.prod
  app/
  alembic/
  alembic.ini
  requirements.txt

apps/frontend/
  Dockerfile.prod
  nginx.conf
  package.json
  package-lock.json
  src/
  vite.config.ts

infra/caddy/
  Caddyfile.prod.example
  Dockerfile.prod.example

docker-compose.prod.yml
docker-compose.prod.example.yml
.env.production.example
scripts/
docs/
```

### Exclusiones rsync

```text
.git/
.env
.env.production
.env.local
.env.development
.env.*.local
!.env.example
!.env.production.example
node_modules/
dist/
.venv/
__pycache__/
.pytest_cache/
*.pyc
*.log
```

### docker-compose.prod.yml propuesto

- Usa imagenes, no `build`.
- Caddy publica solo `80` y `443`.
- No publica `2019`, `5432`, `8000` ni `5173`.
- Usa volumenes `postgres_data`, `caddy_data`, `caddy_config`.
- Usa redes `edge` y `control`.
- `control` es interna.

### Imagenes GHCR esperadas

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
ghcr.io/andre-101/v4nex-backend:scenario-23-app-images
ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images
```

Estado real:

- Caddy custom ya fue publicada y validada desde VPS.
- Backend/frontend fueron construidas y taggeadas localmente.
- Backend/frontend push GHCR queda pendiente.
- Infra no debe intentar `docker pull` de backend/frontend hasta que app confirme publicacion GHCR.

### Variables productivas finales

```env
APP_ENV=production
DOMAIN=v4nex.com
CADDY_DOMAIN=v4nex.com
CADDY_IMAGE_TAG=scenario-21-scratch-clean
BACKEND_IMAGE_TAG=scenario-23-app-images
FRONTEND_IMAGE_TAG=scenario-23-app-images
POSTGRES_DB=v4nex
POSTGRES_USER=v4nex
POSTGRES_PASSWORD=<real-secret>
JWT_SECRET=<real-secret>
CLOUDFLARE_API_TOKEN=<real-secret>
CADDY_ACME_EMAIL=<real-email>
BACKEND_PORT=8000
```

### Volumenes

```text
postgres_data
caddy_data
caddy_config
```

### Healthchecks

```text
db: pg_isready
backend: GET /health
frontend: GET /
caddy: caddy validate
```

### Puertos publicos/privados

Publicos:

```text
80
443
```

Privados:

```text
2019 Caddy Admin API
5432 Postgres
8000 backend
80 frontend interno
```

### Redes Docker

```text
edge: caddy, frontend, backend
control: caddy, backend, db; internal: true
```

### Necesidades Caddy

- Plataforma apex en `v4nex.com`.
- API interna bajo `/_v4nex/*`.
- `/health` hacia backend.
- Frontend hacia `frontend:80`.
- Caddy Admin API solo dentro de Docker.
- TLS DNS-01 pendiente, no ejecutar todavia.

### Comandos de preflight

```bash
cd /opt/v4nex/app
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker pull ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
```

Pendiente hasta Escenario 24, solo con confirmacion de app:

```bash
docker pull ghcr.io/andre-101/v4nex-backend:scenario-23-app-images
docker pull ghcr.io/andre-101/v4nex-frontend:scenario-23-app-images
```

### Riesgos

- Backend/frontend pendientes de push GHCR.
- `.env.production` existe solo en VPS y no debe sobrescribirse.
- No ejecutar compose hasta que infra apruebe preflight.
- TLS/ACME/Cloudflare API siguen fuera de alcance.

### Pendientes

- Confirmar aceptacion del compose propuesto.
- Publicar backend/frontend con push controlado si infra aprueba.
- Validar pull de backend/frontend desde VPS.
- Ejecutar preflight en VPS sin levantar servicios.

### Siguiente paso recomendado

Infra debe revisar esta Ronda 2 y responder si:

1. Acepta `docker-compose.prod.yml` propuesto.
2. Acepta frontend interno en `80` con Nginx.
3. Autoriza push GHCR backend/frontend con tag fijo.
4. Autoriza validacion pull desde VPS, sin `docker compose up`.
