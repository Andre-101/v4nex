# Cierre de Fase 2 — v4nex v0.1.0

## Resumen ejecutivo

La Fase 2 de v4nex v0.1.0 se cierra como **flujo automatizado validado en seco**. Esto significa que el proceso operativo de despliegue, verificación mínima, despliegue simulado, rollback simulado y auditoría de estado fue validado sin ejecutar un deploy real ni modificar el runtime productivo.

Este cierre **no declara producción final lista**. La plataforma queda en una línea base operativa controlada, con el panel principal cerrado temporalmente y los endpoints de salud disponibles para operación.

## Alcance validado

Durante esta fase se validaron los siguientes elementos:

- Contrato de release versionado en `releases/v0.1.0.json`.
- Scripts operativos versionados en `scripts/prod/`.
- Runbook operativo en `docs/runbooks/despliegue-produccion.md`.
- Sincronización controlada de artefactos operativos hacia la VPS.
- Preflight versionado.
- Smoke minimal.
- Deploy dry-run.
- Rollback dry-run.
- Auditoría final readonly.

No se validaron en esta fase:

- Deploy real.
- Rollback real.
- Smoke extended.
- Reapertura del panel principal.
- Operación pública continua sin modo cerrado temporal.
- Política completa de abuso, rate limiting y soporte operativo 24/7.

## Línea base operativa aceptada

| Elemento | Estado aceptado |
|---|---|
| Release | v0.1.0 |
| Manifest | `releases/v0.1.0.json` |
| Platform mode | `closed_temporarily` |
| DB | healthy |
| Backend | healthy |
| Frontend | healthy |
| Caddy | healthy |
| Red `app_control` | IPv6 activo |
| Red `app_edge` | IPv6 activo |
| `https://v4nex.com/` | 403 esperado |
| `https://v4nex.com/health` | 200 OK |
| `https://v4nex.com/_v4nex/health` | 200 OK |
| Puertos públicos | 80/443 vía Caddy |
| Puertos internos 2019/5432/8000/5173 | No publicados al host |
| Usuarios | 2 |
| Bridges | ACTIVE:1 |

## Imágenes en operación

| Componente | Imagen/tag |
|---|---|
| Backend | `ghcr.io/andre-101/v4nex-backend:scenario-30-caddy-route-precedence` |
| Frontend | `ghcr.io/andre-101/v4nex-frontend:scenario-28-bridge-lifecycle-ui` |
| Caddy | `ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean` |
| DB | `postgres:16-alpine` |

## Matriz de evidencias

| Ronda | Validación | Resultado | Evidencia principal |
|---|---|---|---|
| R34 | Preflight controlado | GO | `preflight-ok`, digests OK, servicios healthy, `platform-health-ok` |
| R35 | Smoke minimal | GO | `smoke-minimal-ok`, `no-users-or-bridges-created-ok` |
| R36 | Deploy dry-run | GO | `DRY_RUN=1`, skip env mutation, skip compose pull, skip compose up, `deploy-ok` |
| R37 | Rollback dry-run | GO | `DRY_RUN=1`, `rollback-ok`, skip rollback de `BACKEND_IMAGE_TAG`, skip compose up |
| R38 | Audit-state readonly | GO | `audit-state-ok`, `port-security-ok`, `public-health-ok` |

## Reportes generados

| Tipo | Ruta |
|---|---|
| Preflight | `/opt/v4nex/runtime/preflight-v0.1.0-20260529_013527.txt` |
| Smoke minimal | `/opt/v4nex/runtime/smoke-v0.1.0-20260529_013852.txt` |
| Deploy dry-run | `/opt/v4nex/runtime/deploy-v0.1.0-20260529_015404.txt` |
| Rollback dry-run | `/opt/v4nex/runtime/rollback-v0.1.0-20260529_015846.txt` |
| Audit-state | `/opt/v4nex/runtime/audit-state-v0.1.0-20260529_020158.txt` |

## Decisiones tomadas

1. Cerrar Fase 2 como flujo automatizado validado en seco.
2. No ejecutar deploy real porque el runtime actual ya opera con los tags y digests esperados.
3. Mantener `v4nex.com/` cerrado temporalmente con 403 para reducir riesgo de abuso.
4. Mantener `/health` y `/_v4nex/health` disponibles para operación y verificación.
5. Preservar el bridge activo existente sin modificarlo.
6. Exigir aprobación separada para cualquier deploy real futuro.

## Recursos protegidos confirmados

- `.env.production` intacto.
- `docker-compose.prod.yml` intacto.
- `infra/caddy/Caddyfile.prod` intacto.
- `app_postgres_data` preservado.
- `app_caddy_data` preservado.
- `app_caddy_config` preservado.
- Contenedores no recreados durante validaciones dry-run.
- Caché de imágenes sin cambios durante dry-run.
- Usuarios y bridges sin cambios.

## Restricciones vigentes

Hasta una nueva aprobación explícita, siguen prohibidas las siguientes acciones:

- Deploy real.
- Rollback real.
- `docker compose up`.
- `docker compose down`.
- `docker compose pull` fuera de autorización explícita.
- Smoke extended.
- Creación de bridges.
- Validate/activate de bridges.
- Close/open platform real.
- Modificación de `.env.production`.
- Modificación de `docker-compose.prod.yml`.
- Modificación de `infra/caddy/Caddyfile.prod`.
- Cambios DNS.
- Repetición manual de ACME.
- Borrado de volúmenes.
- Publicación de puertos internos.

## Riesgos pendientes

| Riesgo | Estado |
|---|---|
| Producción final no declarada | Pendiente |
| `platform_mode` sigue en `closed_temporarily` | Pendiente |
| Smoke extended no ejecutado | Pendiente |
| Deploy real no probado | Pendiente |
| Rollback real no probado | Pendiente |
| Bridge activo real expuesto a cambios accidentales | Pendiente de control operativo |
| Backups y reportes acumulándose en `/opt/v4nex/runtime` | Pendiente de política de retención aplicada |
| Reapertura del panel principal | Pendiente de decisión de seguridad |
| Criterios de abuso y rate limiting | Pendiente |
| Operación pública continua | Pendiente |

## Criterio de no producción final

La Fase 2 no declara producción final lista porque aún faltan validaciones y decisiones operativas relevantes: smoke extended, política formal de abuso, condiciones de reapertura del panel, monitoreo continuo, retención implementada de backups runtime y autorización explícita de deploy real cuando exista una necesidad funcional.

## Condición de cierre

Fase 2 queda cerrada cuando estos documentos sean revisados y aprobados mediante PR documental. El merge del PR de cierre no autoriza ejecución operativa ni cambios en la VPS.
