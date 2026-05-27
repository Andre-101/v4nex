# Escenario 30 — Publicación GHCR backend route precedence

## Resumen ejecutivo

Después del merge de PR #28, se publicó únicamente una nueva imagen backend en GHCR con tag fijo para incorporar la corrección de precedencia de rutas dinámicas de Caddy.

La corrección de PR #28 asegura que las rutas de bridges activos se inserten antes de:

- wildcard frontend fallback;
- catch-all frontend fallback;
- subroute frontend fallback.

Frontend no cambió y no se publicó una nueva imagen frontend.

No hubo deploy, rsync, VPS, DNS, Cloudflare API, ACME, cambios en Caddyfile base, cambios en `.env.production`, cambios en `docker-compose.prod.yml` ni CI/CD.

## Contexto PR #28

`main` fue actualizado y contiene el merge de PR #28:

```text
ec5f47e Merge pull request #28 from Andre-101/fix/caddy-route-precedence-for-bridges
05d9748 fix: prioritize bridge routes over frontend fallback
```

También se confirmó que `docker-compose.prod.yml` conserva la configuración IPv6 productiva:

```text
enable_ipv6: true
ipam
fd42:4e58:1501::/64
fd42:4e58:1502::/64
```

## Imagen backend publicada

Imagen:

```text
ghcr.io/andre-101/v4nex-backend:scenario-30-caddy-route-precedence
```

Digest:

```text
v4nex-backend@sha256:836621299ab130898582ef68de06be29ce036f833538036a52209f94758b5d40
```

## Frontend

No se publicó una nueva imagen frontend.

Mantener:

```text
ghcr.io/andre-101/v4nex-frontend:scenario-28-bridge-lifecycle-ui
```

## Validaciones ejecutadas

### Git / main

Comandos:

```text
git checkout main
git pull
git status --short
git log --oneline -5
```

Resultado:

- `main` actualizado.
- Worktree limpio antes de generar esta documentación.
- Merge de PR #28 presente.

### IPv6 productivo en compose

Comando:

```text
rg -n "enable_ipv6|ipam|subnet" docker-compose.prod.yml
```

Resultado:

```text
118:    enable_ipv6: true
119:    ipam:
121:        - subnet: 172.18.0.0/16
122:        - subnet: fd42:4e58:1501::/64
125:    enable_ipv6: true
126:    ipam:
128:        - subnet: 172.19.0.0/16
129:        - subnet: fd42:4e58:1502::/64
```

`docker-compose.prod.yml` no fue modificado.

### Backend tests

Comando:

```text
cd apps/backend
python -m pytest -p no:cacheprovider
```

Resultado:

```text
117 passed, 1 warning in 8.25s
```

Warning observado:

```text
PendingDeprecationWarning: Please use `import python_multipart` instead.
```

### Checks estáticos

Resultados:

- No `latest` en compose productivo.
- No `frontend:5173` en `caddy_config.py`.
- No `":8080"` productivo en `caddy_config.py`.
- No `automatic_https disable true`.
- `git diff -- docker-compose.prod.yml` sin cambios.

## Build backend local

Comando:

```text
docker build -f apps/backend/Dockerfile.prod -t v4nex-backend:scenario-30-caddy-route-precedence apps/backend
```

Resultado:

```text
naming to docker.io/library/v4nex-backend:scenario-30-caddy-route-precedence done
```

## Runtime check backend

Comando:

```text
docker run --rm v4nex-backend:scenario-30-caddy-route-precedence python -c "import fastapi, sqlalchemy, alembic; print('backend runtime imports ok')"
```

Resultado:

```text
backend runtime imports ok
```

## Push GHCR

Tag GHCR:

```text
docker tag v4nex-backend:scenario-30-caddy-route-precedence ghcr.io/andre-101/v4nex-backend:scenario-30-caddy-route-precedence
```

Push:

```text
docker push ghcr.io/andre-101/v4nex-backend:scenario-30-caddy-route-precedence
```

Resultado:

```text
scenario-30-caddy-route-precedence: digest: sha256:836621299ab130898582ef68de06be29ce036f833538036a52209f94758b5d40 size: 856
```

## Pull/check GHCR

Comando:

```text
docker pull ghcr.io/andre-101/v4nex-backend:scenario-30-caddy-route-precedence
```

Resultado:

```text
Digest: sha256:836621299ab130898582ef68de06be29ce036f833538036a52209f94758b5d40
Status: Image is up to date
```

Inspect:

```text
docker image inspect ghcr.io/andre-101/v4nex-backend:scenario-30-caddy-route-precedence --format '{{index .RepoDigests 0}}'
```

Resultado:

```text
v4nex-backend@sha256:836621299ab130898582ef68de06be29ce036f833538036a52209f94758b5d40
```

## Docker Scout

Imagen:

```text
ghcr.io/andre-101/v4nex-backend:scenario-30-caddy-route-precedence
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

## Restricciones respetadas

- No se usó `latest`.
- No se publicó frontend.
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

## Decisión

GO técnico para que infra actualice únicamente backend y valide la corrección de precedencia en producción controlada.

Producción final sigue no declarada hasta confirmar que `public_url` responde el servicio IPv6 destino y no el frontend base.

## SYNC app → infra — Ronda 19

### Backend nuevo

```text
BACKEND_IMAGE_TAG=scenario-30-caddy-route-precedence
ghcr.io/andre-101/v4nex-backend:scenario-30-caddy-route-precedence
v4nex-backend@sha256:836621299ab130898582ef68de06be29ce036f833538036a52209f94758b5d40
```

### Frontend a mantener

```text
FRONTEND_IMAGE_TAG=scenario-28-bridge-lifecycle-ui
ghcr.io/andre-101/v4nex-frontend:scenario-28-bridge-lifecycle-ui
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

Actualizar manualmente `.env.production`:

```text
BACKEND_IMAGE_TAG=scenario-30-caddy-route-precedence
FRONTEND_IMAGE_TAG=scenario-28-bridge-lifecycle-ui
ALLOWED_TARGET_PORTS=80,8080
```

Pull backend:

```text
docker compose pull backend
```

Recrear solo backend:

```text
docker compose up -d backend
```

No tocar:

- Caddyfile base.
- DNS.
- ACME.
- Cloudflare.
- Volúmenes.
- DB.
- Frontend, salvo que Docker Compose lo recree por dependencia explícita.

Validaciones esperadas:

- `v4nex.com` antes/después de `activate`.
- `/health` antes/después de `activate`.
- `/_v4nex/health` antes/después de `activate`.
- Crear bridge `DRAFT`.
- Ejecutar `validate` y confirmar `READY`.
- Ejecutar `activate` y confirmar `ACTIVE`.
- Confirmar que `public_url` responde el servicio IPv6 destino.
- Confirmar que `public_url` no responde el frontend base.
- Confirmar que no se publica `2019`, `5432`, `8000` ni `5173`.

### Restricciones activas

- No tocar DNS.
- No repetir ACME.
- No borrar volúmenes.
- No recrear DB.
- No recrear frontend si no es necesario.
- No ejecutar `down -v`.
- No publicar `2019`, `5432`, `8000` ni `5173`.
- No tocar Caddyfile base salvo autorización explícita.

