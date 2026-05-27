# Escenario 28 — Publicación GHCR backend/frontend después de Ronda 16

## Resumen ejecutivo

Después del merge de PR #27, se construyeron, validaron, publicaron y verificaron nuevas imágenes GHCR para backend y frontend.

La publicación incorpora:

- Backend con activación dinámica segura de Caddy:
  - lee la configuración viva de Caddy;
  - preserva rutas base productivas;
  - inyecta solo rutas dinámicas de bridges;
  - ejecuta rollback si `/load` falla.
- Frontend con lifecycle mínimo:
  - `DRAFT -> Validar -> READY -> Activar -> ACTIVE`.

No se hizo deploy, no se hizo rsync, no se tocó VPS, no se tocó Caddyfile base, no se modificó DNS, no se repitió ACME y no se llamó Cloudflare API.

## Contexto PR #27

PR #27 fue mergeada a `main`:

```text
e474b36 Merge pull request #27 from Andre-101/feat/caddy-dynamic-safe-activation
```

También se confirmó que `main` conserva el commit de IPv6 productivo:

```text
9b118fa infra: enable IPv6 Docker networks for production
```

`docker-compose.prod.yml` fue preservado. Se verificó que mantiene:

- `enable_ipv6: true`
- `ipam`
- subnets IPv6 productivas:
  - `fd42:4e58:1501::/64`
  - `fd42:4e58:1502::/64`

## Imágenes publicadas

### Backend

```text
ghcr.io/andre-101/v4nex-backend:scenario-28-caddy-safe-activation
```

Digest:

```text
v4nex-backend@sha256:c34aaf21abff116195fad2c348e28472cf50e36c896a5c5745f7224a5e32e2c9
```

### Frontend

```text
ghcr.io/andre-101/v4nex-frontend:scenario-28-bridge-lifecycle-ui
```

Digest:

```text
v4nex-frontend@sha256:cda53670de09627d80e98c65f2eff3428f551314ec9c8c28f7039b501cb3c175
```

## Validaciones ejecutadas

### Git / main

```text
git checkout main
git pull
git status --short
git log --oneline -5
```

Resultado:

- `main` actualizado.
- Worktree limpio antes de generar esta documentación.
- PR #27 presente en el log.
- Commit `9b118fa` presente en el log.

### Backend tests

Comando:

```text
cd apps/backend
python -m pytest -p no:cacheprovider
```

Resultado:

```text
114 passed, 1 warning in 8.73s
```

Warning observado:

```text
PendingDeprecationWarning: Please use import python_multipart instead.
```

### Frontend build

Comandos:

```text
cd apps/frontend
npm install
npm run build
```

Resultado:

```text
vite v5.4.21 building for production...
31 modules transformed.
dist/index.html                 0.41 kB
dist/assets/index-B74tGkMD.css  6.89 kB
dist/assets/index-jvCaDWwu.js   151.64 kB
built in 1.86s
```

`npm install` reportó:

```text
2 moderate severity vulnerabilities
```

Se documentan como deuda no bloqueante para esta ronda.

### Checks estáticos

No se encontraron coincidencias para:

- `Frontend Skeleton`
- `Escenario 0`
- `backend:8000`
- `MVP`
- `demo visual`
- `latest` en compose productivo

Checks Caddy dinámico:

- `caddy_config.py` ya no genera configuración completa nueva.
- `build_caddy_config` está deshabilitado y obliga a inyectar rutas en la configuración viva.
- No se encontró `frontend:5173` en servicios Caddy dinámicos.
- No se encontró `":8080"` en servicios Caddy dinámicos.
- No se encontró `automatic_https` modificado en servicios Caddy dinámicos.
- No se encontró `"disable": true` en servicios Caddy dinámicos.

### Build local de imágenes

Backend:

```text
docker build -f apps/backend/Dockerfile.prod -t v4nex-backend:scenario-28-caddy-safe-activation apps/backend
```

Resultado:

```text
naming to docker.io/library/v4nex-backend:scenario-28-caddy-safe-activation done
```

Frontend:

```text
docker build -f apps/frontend/Dockerfile.prod -t v4nex-frontend:scenario-28-bridge-lifecycle-ui apps/frontend
```

Resultado:

```text
naming to docker.io/library/v4nex-frontend:scenario-28-bridge-lifecycle-ui done
```

### Runtime local mínimo

Backend:

```text
docker run --rm v4nex-backend:scenario-28-caddy-safe-activation python -c "import fastapi, sqlalchemy, alembic; print('backend runtime imports ok')"
```

Resultado:

```text
backend runtime imports ok
```

Frontend:

```text
docker run -d --rm --name v4nex-frontend-r28-check -p 18080:80 v4nex-frontend:scenario-28-bridge-lifecycle-ui
curl.exe -I http://127.0.0.1:18080/
docker rm -f v4nex-frontend-r28-check
```

Resultado:

```text
HTTP/1.1 200 OK
Server: nginx/1.29.3
```

## Push GHCR

Backend:

```text
docker push ghcr.io/andre-101/v4nex-backend:scenario-28-caddy-safe-activation
```

Resultado:

```text
scenario-28-caddy-safe-activation: digest: sha256:c34aaf21abff116195fad2c348e28472cf50e36c896a5c5745f7224a5e32e2c9 size: 856
```

Frontend:

```text
docker push ghcr.io/andre-101/v4nex-frontend:scenario-28-bridge-lifecycle-ui
```

Resultado:

```text
scenario-28-bridge-lifecycle-ui: digest: sha256:cda53670de09627d80e98c65f2eff3428f551314ec9c8c28f7039b501cb3c175 size: 856
```

## Pull/check GHCR

Backend:

```text
docker pull ghcr.io/andre-101/v4nex-backend:scenario-28-caddy-safe-activation
```

Resultado:

```text
Digest: sha256:c34aaf21abff116195fad2c348e28472cf50e36c896a5c5745f7224a5e32e2c9
Status: Image is up to date
```

Frontend:

```text
docker pull ghcr.io/andre-101/v4nex-frontend:scenario-28-bridge-lifecycle-ui
```

Resultado:

```text
Digest: sha256:cda53670de09627d80e98c65f2eff3428f551314ec9c8c28f7039b501cb3c175
Status: Image is up to date
```

## Docker Scout

### Backend

Imagen:

```text
ghcr.io/andre-101/v4nex-backend:scenario-28-caddy-safe-activation
```

Resultado general:

```text
0C 0H 2M 22L 3?
size: 86 MB
packages: 171
```

Resultado critical/high:

```text
0C 0H 0M 0L
No vulnerable packages detected
```

Deuda no bloqueante:

- `tar`: 1 medium, 1 low.
- `starlette`: 1 medium.
- Vulnerabilidades low/unspecified en paquetes base Debian.

### Frontend

Imagen:

```text
ghcr.io/andre-101/v4nex-frontend:scenario-28-bridge-lifecycle-ui
```

Resultado general:

```text
0C 0H 5M 0L
size: 27 MB
packages: 78
```

Resultado critical/high:

```text
0C 0H 0M 0L
No vulnerable packages detected
```

Deuda no bloqueante:

- `libxml2`: 1 medium.
- `freetype`: 1 medium.
- `busybox`: 1 medium.
- `util-linux`: 1 medium.
- `fontconfig`: 1 medium.

## Decisión

GO técnico para que infra valide pull y actualización controlada de backend/frontend en la siguiente ronda.

No se declara producción final. La validación de activación segura debe ejecutarse en infraestructura controlada confirmando que la plataforma base no se rompe antes/después de activar bridges.

## Restricciones respetadas

- No se usó `latest`.
- No se hizo rsync.
- No se hizo deploy.
- No se tocó VPS.
- No se ejecutó `docker compose up` en VPS.
- No se tocó Caddyfile base.
- No se modificó DNS.
- No se repitió ACME.
- No se llamó Cloudflare API.
- No se borraron volúmenes.
- No se tocó `.env.production`.
- No se cambió `docker-compose.prod.yml`.
- No se creó CI/CD.

## SYNC app → infra — Ronda 17

### Imágenes nuevas

Backend:

```text
BACKEND_IMAGE_TAG=scenario-28-caddy-safe-activation
ghcr.io/andre-101/v4nex-backend:scenario-28-caddy-safe-activation
v4nex-backend@sha256:c34aaf21abff116195fad2c348e28472cf50e36c896a5c5745f7224a5e32e2c9
```

Frontend:

```text
FRONTEND_IMAGE_TAG=scenario-28-bridge-lifecycle-ui
ghcr.io/andre-101/v4nex-frontend:scenario-28-bridge-lifecycle-ui
v4nex-frontend@sha256:cda53670de09627d80e98c65f2eff3428f551314ec9c8c28f7039b501cb3c175
```

### Variables

Nuevas variables:

```text
ninguna
```

Mantener:

```text
ALLOWED_TARGET_PORTS=80,8080
```

### Instrucciones para infra

Actualizar manualmente `.env.production` en VPS:

```text
BACKEND_IMAGE_TAG=scenario-28-caddy-safe-activation
FRONTEND_IMAGE_TAG=scenario-28-bridge-lifecycle-ui
ALLOWED_TARGET_PORTS=80,8080
```

Pull controlado:

```text
docker compose pull backend frontend
```

Recrear solo servicios app:

```text
docker compose up -d backend frontend
```

No tocar:

- Caddyfile base.
- DNS.
- ACME.
- Volúmenes.
- DB.
- Caddy Admin API pública.
- Puertos publicados.

Validaciones esperadas:

- `v4nex.com` sigue OK antes de activar bridge.
- `/health` sigue OK antes de activar bridge.
- `/_v4nex/health` sigue OK antes de activar bridge.
- Crear bridge `DRAFT`.
- Ejecutar `validate` y confirmar `READY`.
- Ejecutar `activate` y confirmar `ACTIVE`.
- Confirmar que `v4nex.com` sigue OK después de activar bridge.
- Confirmar que `/health` sigue OK después de activar bridge.
- Confirmar que `/_v4nex/health` sigue OK después de activar bridge.
- Confirmar que `public_url` del bridge responde.

### Restricciones activas

- No tocar DNS.
- No repetir ACME.
- No borrar volúmenes.
- No ejecutar `down -v`.
- No publicar `2019`, `5432`, `8000` ni `5173`.
- No tocar Caddyfile base salvo autorización explícita.
- No declarar producción final hasta validar la activación dinámica en vivo.

