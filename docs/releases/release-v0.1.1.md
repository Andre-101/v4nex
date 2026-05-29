# Release v0.1.1 — Bridge Management

## Resumen ejecutivo

Release `v0.1.1` prepara la entrega funcional controlada de la administración de bridges integrada en PR #37.

La entrega actualiza backend y frontend para permitir administración funcional desde el panel, incluyendo detalle, edición, validación, activación, desactivación y eliminación de bridges. No declara migraciones, no declara variables nuevas y no modifica infraestructura.

Estado:

- Release ID: `v4nex-v0.1.1`
- Parent release: `v0.1.0`
- Source merge commit: `662cce859233d19860dc0832f23226f443260ec1`
- Ambiente: `production`
- Estado: `pending-infra-approval`
- Aprobado por App: `true`
- Aprobado por Infra: `false`

Infra debe revisar y aprobar este contrato antes de ejecutar cualquier acción operativa.

## Compatibilidad operativa

El manifest `releases/v0.1.1.json` conserva compatibilidad estricta con el schema operativo validado en `v0.1.0`.

Campos operativos canónicos para scripts:

- `variables`
- `variables.non_secret`
- `variables.sensitive_names_only`
- `variables.new_variables`
- `variables.changed_variables`
- `deployment.recreate`
- `deployment.do_not_recreate`
- `deployment.validate_only`
- `deployment.requires_manual_approval`

Si existen `env`, `deployment.services_to_recreate` o `deployment.services_not_to_recreate`, deben tratarse como alias informativos o de compatibilidad documental. No sustituyen a los campos operativos anteriores.

## Cambios funcionales

Backend:

- Agrega `PATCH /_v4nex/bridges/{bridge_id}`.
- Agrega `DELETE /_v4nex/bridges/{bridge_id}`.
- Mantiene ownership por usuario.
- Mantiene reglas de estado para edición y eliminación.
- Mantiene allowlist de puertos existente.

Frontend:

- Agrega administración funcional de bridges desde el panel.
- Permite listar bridges.
- Permite ver detalle de bridge.
- Permite crear bridge.
- Permite editar bridge.
- Permite validar bridge.
- Permite activar bridge.
- Permite desactivar bridge.
- Permite eliminar bridge.
- Refresca estado después de cada acción.
- Muestra mensajes claros de error.

## Componentes actualizados

### Backend

```text
image: ghcr.io/andre-101/v4nex-backend
tag: scenario-37-bridge-management-api-r2
digest: sha256:15f02fe0857545a01299d0590b40e91ed4fed5de90130579ecd33be15b415f08
```

### Frontend

```text
image: ghcr.io/andre-101/v4nex-frontend
tag: scenario-37-bridge-management-ui
digest: sha256:49582abd3db4e132f887acd380cd6300cf6b6b5a8cf9a8eab5c6dc2c6bdff204
```

## Componentes no modificados

### Caddy

```text
image: ghcr.io/andre-101/v4nex-caddy-cloudflare
tag: scenario-21-scratch-clean
digest: sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6
```

Caddy no debe recrearse para este release salvo drift o aprobación manual explícita.

### Base de datos

No se recrea.

### Infraestructura

No se modifican:

- `docker-compose.prod.yml`
- `infra/caddy/Caddyfile.prod`
- DNS
- ACME
- Volúmenes
- `.env.production`

## Migraciones

```text
migrations.required: false
alembic_required: false
alembic_command: null
```

No hay migraciones declaradas para `v0.1.1`.

## Variables

El bloque operativo usado por scripts es `variables`. El bloque `env`, si está presente, es informativo y mantiene los mismos valores para compatibilidad documental.

Variables nuevas:

```text
[]
```

Variables modificadas:

```text
[]
```

Variables no secretas esperadas:

```text
BACKEND_IMAGE_TAG=scenario-37-bridge-management-api-r2
FRONTEND_IMAGE_TAG=scenario-37-bridge-management-ui
CADDY_IMAGE_TAG=scenario-21-scratch-clean
ALLOWED_TARGET_PORTS=80,8080
```

Variables sensibles solo por nombre:

- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- `CLOUDFLARE_API_TOKEN`
- `CADDY_ACME_EMAIL`

El contrato no contiene valores secretos reales.

## Servicios a recrear

Los campos operativos usados por scripts son `deployment.recreate` y `deployment.do_not_recreate`.

Recrear:

- `backend`
- `frontend`

No recrear:

- `db`
- `caddy`

Servicios protegidos:

- `db`
- `caddy`

Los campos `deployment.services_to_recreate` y `deployment.services_not_to_recreate`, si están presentes, son alias informativos. No reemplazan a `deployment.recreate` ni a `deployment.do_not_recreate`.

## Smoke esperado

### Smoke mínimo

Requerido:

- `compose_config_valid`
- `services_healthy`
- `health_ok`
- `v4nex_health_ok`
- `protected_ports_not_published`
- `platform_mode_behavior_ok`
- `bridge_list_ok`

### Smoke extendido

No autorizado por defecto. Requiere aprobación operativa explícita.

Checks posibles:

- `login_ok`
- `bridge_create_draft_ok`
- `bridge_detail_ok`
- `bridge_edit_ok`
- `bridge_validate_ok`
- `bridge_ready_confirmed`
- `bridge_activate_ok`
- `bridge_active_confirmed`
- `bridge_disable_ok`
- `bridge_delete_ok`
- `platform_still_ok_after_actions`
- `internal_ports_not_published`

## Rollback esperado

Rollback de backend:

```text
previous_backend_tag=scenario-30-caddy-route-precedence
previous_backend_digest=sha256:836621299ab130898582ef68de06be29ce036f833538036a52209f94758b5d40
```

Rollback de frontend:

```text
previous_frontend_tag=scenario-28-bridge-lifecycle-ui
previous_frontend_digest=sha256:cda53670de09627d80e98c65f2eff3428f551314ec9c8c28f7039b501cb3c175
```

Caddy permanece:

```text
previous_caddy_tag=scenario-21-scratch-clean
previous_caddy_digest=sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6
```

Rollback services:

- `backend`
- `frontend`

Rollback env keys:

- `BACKEND_IMAGE_TAG`
- `FRONTEND_IMAGE_TAG`

No requiere restore de DB.

No requiere restore de Caddy.

## Riesgos conocidos

La primera imagen backend `scenario-37-bridge-management-api` reportó `1 Critical` y `3 High` por `perl 5.40.1-6` proveniente de la base Debian slim.

Remediación aplicada:

```text
runtime base: python:3.11-alpine
apt/perl: eliminado del runtime
backend tag: scenario-37-bridge-management-api-r2
```

Docker Scout sobre backend `scenario-37-bridge-management-api-r2` reportó:

```text
0 Critical
0 High
2 Medium
0 Low
```

Hallazgos restantes:

```text
starlette 0.49.1: 1 Medium
busybox 1.37.0-r30: 1 Medium
```

No quedan hallazgos critical/high en backend.

Docker Scout sobre frontend reportó:

```text
0 Critical
0 High
5 Medium
0 Low
```

Decisión operativa recomendada:

- Infra debe tratar `v0.1.1` como `pending-infra-approval`.
- La imagen backend remediada queda apta para revisión operativa porque critical/high está en cero.

## Restricciones operativas

Obligatorias:

- No DNS.
- No ACME.
- No `down -v`.
- No borrar volúmenes.
- No cambiar Caddyfile base.
- No sobrescribir `.env.production`.
- No publicar puertos internos.
- No usar tags `latest`.
- No ejecutar workflows productivos.
- No rsync.
- No tocar VPS fuera del procedimiento aprobado.

## Recursos protegidos

- `.env.production`
- `docker-compose.prod.yml`
- `infra/caddy/Caddyfile.prod`
- `app_postgres_data`
- `app_caddy_data`
- `app_caddy_config`

## GO / NO-GO

GO requiere:

- Manifest válido.
- Tags no `latest`.
- Digests presentes.
- Sin secretos reales en manifest.
- Compose válido.
- `.env.production` protegido.
- Puertos internos no publicados.
- Health checks OK.
- Backend y frontend recreados correctamente.
- Smoke mínimo OK.
- Backend sin hallazgos critical/high.

NO-GO si ocurre:

- Manifest inválido.
- Tag `latest`.
- Secreto real detectado.
- Digest faltante.
- Compose inválido.
- `.env.production` ausente o desprotegido.
- Puerto interno publicado.
- Health check falla.
- Recreate de backend/frontend falla.
- Smoke mínimo falla.
- Hallazgo critical/high backend detectado.
- Se requiere DNS o ACME manual.
- Se requiere borrar volúmenes.
