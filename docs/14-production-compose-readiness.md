# 14 - Compose productivo draft y runbooks sin deploy

## Resumen ejecutivo

Este escenario prepara una propuesta productiva revisable para VPS sin ejecutar despliegue real. Se agregan archivos example, validaciones de entorno y runbooks para revisar secretos/configuracion antes de avanzar.

No se emiten certificados TLS reales, no se configura DNS publico, no se llama a Cloudflare, no se crea CI/CD y no se levanta infraestructura productiva.

## Que se creo

- `docker-compose.prod.example.yml`
- `.env.production.example`
- `scripts/check-prod-env.sh`
- `scripts/prod-preflight.sh`
- `docs/14-production-compose-readiness.md`

Estos archivos son de readiness. `docker-compose.prod.example.yml` no es el compose final definitivo.

## Fuera de alcance

- Deploy real.
- TLS real emitido.
- ACME ejecutado.
- Cloudflare API.
- DNS publico real.
- CI/CD.
- Secrets reales.
- VPS real.
- Billing.
- Redis, Celery o Kubernetes.
- `docker-compose.prod.yml` real.

## Arquitectura productiva propuesta

```text
Internet
-> VPS public IPv4
-> Caddy :80/:443
-> frontend/backend internos
-> Postgres interno
-> Caddy Admin API solo red interna
```

Separacion esperada:

- Data plane: cliente publico -> Caddy -> bridge IPv6 target.
- Control plane: backend, DB, Caddy Admin API.
- Admin plane: operador por SSH/VPS.

## Servicios del compose example

| Servicio | Proposito | Exposicion |
| --- | --- | --- |
| `caddy` | Reverse proxy publico | Solo `80:80` y `443:443` al host |
| `backend` | API/control plane | Interno con `expose: 8000` |
| `frontend` | UI actual del repo | Interno con `expose: 5173` |
| `db` | PostgreSQL | Interno, sin puerto host |

Notas:

- Postgres no se expone al host.
- Caddy Admin API usa `expose: 2019`; no se publica al host.
- Backend queda interno. Si se expone en un futuro, debe ser detras de Caddy, auth y controles admin.
- El Caddyfile actual sigue siendo dev; la configuracion productiva definitiva queda para un escenario posterior.

## Puertos publicos y privados

| Puerto | Alcance | Uso |
| --- | --- | --- |
| 80 | Publico | HTTP, redirect o ACME futuro |
| 443 | Publico | HTTPS futuro |
| 2019 | Interno | Caddy Admin API, nunca publico |
| 5432 | Interno | PostgreSQL, nunca publico |
| 8000 | Interno | Backend |
| 5173 | Interno | Frontend actual |

## Variables obligatorias

El archivo `.env.production.example` documenta:

- `APP_ENV`
- `PUBLIC_DOMAIN`
- `DATABASE_URL`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `CADDY_ADMIN_URL`
- `CADDY_ADMIN_TIMEOUT_SECONDS`
- `MAX_BRIDGES_PER_USER`
- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_WINDOW_SECONDS`
- `RATE_LIMIT_MAX_REQUESTS`
- `RATE_LIMIT_STRICT_MAX_REQUESTS`
- `ACME_EMAIL`
- `DNS_PROVIDER`
- `DNS_PROVIDER_API_TOKEN`

## Manejo de secrets

Reglas:

- No crear `.env.production` dentro del repo.
- No commitear secretos reales.
- Reemplazar todos los `change-me`.
- Reemplazar `example.com` por el dominio real solo fuera del repo.
- Guardar el env real en la VPS con permisos restringidos.
- Usar `chmod 600` o mecanismo equivalente.
- No imprimir valores secretos en scripts o logs.
- No subir backups sin cifrado que contengan env real.

## Uso de check-prod-env.sh

Modo estricto futuro:

```bash
bash scripts/check-prod-env.sh /ruta/segura/.env.production
```

Validacion del archivo example con placeholders permitidos:

```bash
bash scripts/check-prod-env.sh .env.production.example --allow-placeholders
```

El script:

- verifica variables obligatorias
- falla si `APP_ENV` no es `production`
- falla si `RATE_LIMIT_ENABLED` no es `true`
- falla si secretos siguen en placeholder, salvo con `--allow-placeholders`
- no imprime valores secretos
- no se conecta a servicios

## Uso de prod-preflight.sh

Validacion del example:

```bash
bash scripts/prod-preflight.sh .env.production.example --allow-placeholders
```

El script:

1. Ejecuta `check-prod-env.sh`.
2. Verifica `docker`.
3. Verifica `docker compose`.
4. Verifica que exista `docker-compose.prod.example.yml`.
5. Ejecuta `docker compose config`.

No levanta servicios, no hace deploy, no llama a Cloudflare y no emite certificados.

## Preparar VPS en el futuro

Runbook futuro, no ejecutar en este escenario:

1. Crear VPS.
2. Configurar firewall:
   - abrir 80/443
   - restringir 22
   - bloquear 2019, 5432, 8000 y 5173 publicos
3. Instalar Docker y Docker Compose plugin.
4. Preparar env real fuera del repo.
5. Ejecutar `check-prod-env.sh` en modo estricto.
6. Ejecutar `prod-preflight.sh` en modo estricto.
7. Revisar `docker compose config`.
8. Preparar Caddy productivo real.
9. Ejecutar migraciones.
10. Ejecutar bootstrap admin.
11. Correr smoke tests.
12. Documentar rollback.

## Migraciones futuras

Comando esperado, cuando exista compose productivo real:

```bash
docker compose --env-file /ruta/segura/.env.production \
  -f docker-compose.prod.yml \
  run --rm backend alembic upgrade head
```

En este escenario no se crea `docker-compose.prod.yml`.

## Bootstrap admin futuro

Comando esperado:

```bash
export DATABASE_URL="postgresql+psycopg://..."
export ADMIN_EMAIL="operator@example.com"
export ADMIN_PASSWORD="secret-value"
bash scripts/bootstrap-admin.sh
```

No usar password real dentro del repo.

## Rollback manual futuro

Runbook conceptual:

1. Guardar compose/env previo.
2. Detener despliegue nuevo si falla smoke.
3. Restaurar compose/env anterior.
4. Restaurar Caddy config anterior.
5. Ejecutar reconciliacion DB -> Caddy si corresponde.
6. Revisar logs backend/Caddy.
7. Documentar incidente.

## Checklist predeploy

- Env real fuera del repo.
- `check-prod-env.sh` pasa en modo estricto.
- `prod-preflight.sh` pasa en modo estricto.
- Firewall revisado.
- Caddy Admin API no publico.
- Postgres no publico.
- Secrets rotados.
- Backups definidos.
- Migraciones probadas.
- Bootstrap admin probado.
- TLS/DNS reales definidos.
- Smoke test documentado.
- Rollback probado.

## Riesgos y pendientes

- `docker-compose.prod.example.yml` no es definitivo.
- Caddyfile productivo real pendiente.
- TLS real pendiente.
- DNS wildcard real pendiente.
- Secret manager real pendiente.
- Rate limiting productivo pendiente.
- Backups y monitoreo pendientes.
- No ejecutar deploy publico todavia.
