# Runbook de despliegue productivo v4nex v0.1.0

## Objetivo

Operar despliegues controlados a partir de `releases/v0.1.0.json`, reduciendo comandos manuales.

## Flujo aprobado

1. `scripts/prod/v4nex-preflight.sh`
2. `V4NEX_DRY_RUN=1 scripts/prod/v4nex-deploy.sh`
3. `scripts/prod/v4nex-deploy.sh` solo con aprobación explícita.
4. `scripts/prod/v4nex-smoke.sh minimal`
5. `TARGET_IPV6=<IPv6> scripts/prod/v4nex-smoke.sh extended`
6. `scripts/prod/v4nex-rollback.sh` si hay NO-GO.

## Smoke extendido

Requiere:
- `TARGET_IPV6`
- `TARGET_PORT` opcional
- `V4NEX_EMAIL` opcional
- `V4NEX_PASSWORD` opcional
- `BASE_URL` opcional

## Reglas de seguridad

No ejecutar `down -v`, no borrar volúmenes, no tocar DNS/ACME, no modificar Caddyfile base, no publicar 2019/5432/8000/5173.
