# 27 - App GHCR publish after Ronda 13A

## Resumen ejecutivo

Escenario 27 publica las nuevas imagenes de backend y frontend posteriores a Ronda 13A en GHCR con tags fijos, sin `latest`, sin deploy, sin rsync y sin tocar VPS.

La publicacion cubre:

- Backend con allowlist configurable de puertos destino.
- Frontend con UI minima funcional.
- Registro/login.
- Vista previa local.
- Listado de bridges.
- Creacion basica de bridges.
- Proxy local Vite solo para desarrollo.

No se ejecuto deploy, no se hizo rsync, no se toco VPS, no se llamo Cloudflare API, no se modifico DNS, no se repitio ACME y no se toco `.env.production`.

## Contexto de PR #26

PR #26 fue mergeada a `main` e integro:

- UI minima funcional.
- Registro/login.
- Session storage.
- Vista previa local.
- `GET /_v4nex/bridges`.
- `POST /_v4nex/bridges`.
- Selector de puerto `80 / 8080`.
- Allowlist configurable `ALLOWED_TARGET_PORTS=80,8080`.
- Proxy local Vite para desarrollo.

## Imagenes publicadas

Backend:

```text
ghcr.io/andre-101/v4nex-backend:scenario-26-port-allowlist
```

Digest:

```text
sha256:7a4f5f41f58358797aaeb511983ced9b106cef5217d976eb12891e61513c073e
```

Frontend:

```text
ghcr.io/andre-101/v4nex-frontend:scenario-26-functional-ui
```

Digest:

```text
sha256:cadff5fd8c763c260b064d36ad2d3b1a6d70a6e9e6bd89f012f80dff772db0fe
```

## Validaciones backend

Comando:

```bash
cd apps/backend
python -m pytest -p no:cacheprovider
```

Resultado:

```text
105 passed, 1 warning in 8.08s
```

Runtime image check:

```bash
docker run --rm v4nex-backend:scenario-26-port-allowlist python -c "import fastapi, sqlalchemy, alembic; print('backend runtime imports ok')"
```

Resultado:

```text
backend runtime imports ok
```

## Validaciones frontend

Comandos:

```bash
cd apps/frontend
npm install
npm run build
```

Resultado `npm install`:

```text
up to date, audited 136 packages
2 moderate severity vulnerabilities
```

Resultado `npm run build`:

```text
vite v5.4.21 building for production...
31 modules transformed.
dist/index.html                 0.41 kB
dist/assets/index-D-Tna77c.css  6.83 kB
dist/assets/index-DDPY9jAz.js   150.21 kB
built in 1.64s
```

Runtime frontend local:

```bash
docker run -d --rm --name v4nex-frontend-check -p 18080:80 v4nex-frontend:scenario-26-functional-ui
curl -I http://127.0.0.1:18080/
docker rm -f v4nex-frontend-check
```

Resultado:

```text
HTTP/1.1 200 OK
Server: nginx/1.29.3
```

## Checks estaticos

No se encontraron coincidencias para:

- `Frontend Skeleton`
- `Escenario 0`
- `backend:8000`
- `MVP`
- `demo visual`
- `latest` en compose productivo

Rutas relativas confirmadas en frontend:

```text
/_v4nex/auth/register
/_v4nex/auth/login
/_v4nex/bridges
```

## Build local

Backend:

```bash
docker build -f apps/backend/Dockerfile.prod -t v4nex-backend:scenario-26-port-allowlist apps/backend
```

Resultado:

```text
naming to docker.io/library/v4nex-backend:scenario-26-port-allowlist done
manifest list sha256:7a4f5f41f58358797aaeb511983ced9b106cef5217d976eb12891e61513c073e
```

Frontend:

```bash
docker build -f apps/frontend/Dockerfile.prod -t v4nex-frontend:scenario-26-functional-ui apps/frontend
```

Resultado:

```text
naming to docker.io/library/v4nex-frontend:scenario-26-functional-ui done
manifest list sha256:cadff5fd8c763c260b064d36ad2d3b1a6d70a6e9e6bd89f012f80dff772db0fe
```

## Push GHCR

Backend:

```bash
docker tag v4nex-backend:scenario-26-port-allowlist ghcr.io/andre-101/v4nex-backend:scenario-26-port-allowlist
docker push ghcr.io/andre-101/v4nex-backend:scenario-26-port-allowlist
```

Resultado:

```text
scenario-26-port-allowlist: digest: sha256:7a4f5f41f58358797aaeb511983ced9b106cef5217d976eb12891e61513c073e size: 856
```

Frontend:

```bash
docker tag v4nex-frontend:scenario-26-functional-ui ghcr.io/andre-101/v4nex-frontend:scenario-26-functional-ui
docker push ghcr.io/andre-101/v4nex-frontend:scenario-26-functional-ui
```

Resultado:

```text
scenario-26-functional-ui: digest: sha256:cadff5fd8c763c260b064d36ad2d3b1a6d70a6e9e6bd89f012f80dff772db0fe size: 856
```

## Pull/check GHCR

Backend:

```bash
docker pull ghcr.io/andre-101/v4nex-backend:scenario-26-port-allowlist
docker image inspect ghcr.io/andre-101/v4nex-backend:scenario-26-port-allowlist --format '{{index .RepoDigests 0}}'
```

Resultado:

```text
Digest: sha256:7a4f5f41f58358797aaeb511983ced9b106cef5217d976eb12891e61513c073e
v4nex-backend@sha256:7a4f5f41f58358797aaeb511983ced9b106cef5217d976eb12891e61513c073e
```

Frontend:

```bash
docker pull ghcr.io/andre-101/v4nex-frontend:scenario-26-functional-ui
docker image inspect ghcr.io/andre-101/v4nex-frontend:scenario-26-functional-ui --format '{{index .RepoDigests 0}}'
```

Resultado:

```text
Digest: sha256:cadff5fd8c763c260b064d36ad2d3b1a6d70a6e9e6bd89f012f80dff772db0fe
v4nex-frontend@sha256:cadff5fd8c763c260b064d36ad2d3b1a6d70a6e9e6bd89f012f80dff772db0fe
```

## Docker Scout

Backend scan completo:

```text
0C 0H 1M 22L 4?
size: 86 MB
packages: 171
```

Backend critical/high:

```text
0C 0H 0M 0L
No vulnerable packages detected
```

Frontend scan completo:

```text
0C 0H 5M 0L
size: 27 MB
packages: 78
```

Frontend critical/high:

```text
0C 0H 0M 0L
No vulnerable packages detected
```

Deuda documentada:

- Backend: 1 medium, 22 low, 4 unspecified.
- Frontend: 5 medium.
- `npm install`: 2 moderate severity vulnerabilities.

No bloquea Ronda 14 porque el criterio definido fue `0 Critical / 0 High`.

## Restricciones respetadas

- No se uso `latest`.
- No se hizo rsync.
- No se hizo deploy.
- No se toco VPS.
- No se ejecuto `docker compose up` en VPS.
- No se toco Caddy.
- No se repitio ACME.
- No se llamo Cloudflare API.
- No se modifico DNS.
- No se toco `.env.production`.
- No se modifico `docker-compose.prod.yml`.
- No se creo CI/CD.

## Pendientes

- Infra debe validar `docker pull` desde VPS.
- Infra debe actualizar `.env.production` manualmente con tags nuevos y `ALLOWED_TARGET_PORTS=80,8080`.
- Infra debe recrear solo backend/frontend cuando se autorice.
- Mantener Caddy, DNS y ACME intactos.
- Revisar deuda medium/moderate en una ronda posterior.

## SYNC app -> infra - Ronda 14

### Imagenes nuevas

Backend tag:

```text
BACKEND_IMAGE_TAG=scenario-26-port-allowlist
```

Backend digest:

```text
ghcr.io/andre-101/v4nex-backend@sha256:7a4f5f41f58358797aaeb511983ced9b106cef5217d976eb12891e61513c073e
```

Frontend tag:

```text
FRONTEND_IMAGE_TAG=scenario-26-functional-ui
```

Frontend digest:

```text
ghcr.io/andre-101/v4nex-frontend@sha256:cadff5fd8c763c260b064d36ad2d3b1a6d70a6e9e6bd89f012f80dff772db0fe
```

Variable requerida en VPS:

```env
ALLOWED_TARGET_PORTS=80,8080
```

### Instrucciones para infra

Actualizar manualmente `/opt/v4nex/app/.env.production`:

```env
BACKEND_IMAGE_TAG=scenario-26-port-allowlist
FRONTEND_IMAGE_TAG=scenario-26-functional-ui
ALLOWED_TARGET_PORTS=80,8080
```

Luego, cuando app autorice la recreacion:

```bash
docker compose pull backend frontend
docker compose up -d backend frontend
```

### Restricciones activas

- No tocar Caddy.
- No repetir ACME.
- No modificar DNS.
- No borrar volumenes.
- No recrear `db`.
- No publicar puertos internos.
- No cambiar `.env.production` fuera de las variables aprobadas.
- No usar `latest`.
- No ejecutar cambios de Cloudflare API.
