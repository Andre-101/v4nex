# Release v0.1.2 - Admin Quota Controls

## Resumen ejecutivo

Release `v0.1.2` prepara una entrega funcional controlada para administrar usuarios, cuotas y estado de cuenta desde el backend y el panel. Tambien incorpora auditoria de acciones administrativas y endurece la respuesta publica para subdominios sin bridge activo.

Estado:

- Release ID: `v4nex-v0.1.2`
- Parent release: `v0.1.1`
- Source branch: `feat/v0.1.2-admin-quota`
- Ambiente: `production`
- Estado: `pending-infra-approval`
- Aprobado por App: `true`
- Aprobado por Infra: `false`

Infra debe revisar y aprobar este contrato antes de ejecutar cualquier accion operativa.

## Compatibilidad operativa

El manifest `releases/v0.1.2.json` conserva compatibilidad con el schema operativo usado en `v0.1.0` y `v0.1.1`.

Campos operativos canonicos para scripts:

- `variables`
- `variables.non_secret`
- `variables.sensitive_names_only`
- `variables.new_variables`
- `variables.changed_variables`
- `deployment.recreate`
- `deployment.do_not_recreate`
- `deployment.validate_only`
- `deployment.requires_manual_approval`
- `platform.platform_mode`

Si existen `env`, `deployment.services_to_recreate` o `deployment.services_not_to_recreate`, deben tratarse como alias informativos. No sustituyen a los campos operativos anteriores.

## Cambios funcionales

Backend:

- Agrega `GET /_v4nex/auth/me`.
- Agrega estado de usuario `is_active`.
- Agrega cuota por usuario `bridge_limit`.
- Nuevos registros por API quedan como `USER`, activos y con `bridge_limit=1`.
- Usuarios inactivos no pueden iniciar sesion ni operar endpoints autenticados.
- Agrega endpoints admin para listar, consultar, suspender, reactivar y eliminar usuarios.
- Agrega endpoints admin para listar bridges globales, listar bridges por usuario, desactivar bridge y eliminar bridge.
- Agrega auditoria administrativa con actor, usuario objetivo y bridge objetivo cuando aplica.
- Agrega CLI por email para promover admin, ajustar cuota, suspender y reactivar.
- Refuerza subdominios reservados y longitud minima de subdominio.
- Mantiene ownership por usuario y reglas de estado existentes para bridges.

Frontend:

- Muestra sesion actual desde `/auth/me`.
- Muestra cuota usada y limite de bridges.
- Bloquea creacion visual cuando la cuota esta agotada.
- Agrega vista admin para usuarios y bridges globales.
- Permite cambiar cuota, suspender/reactivar y eliminar usuarios desde panel admin.
- Permite desactivar o eliminar bridges globales desde panel admin segun estado.
- Agrega respuesta publica para subdominios sin bridge activo sin llamar APIs privadas.

## Componentes actualizados

### Backend

```text
image: ghcr.io/andre-101/v4nex-backend
tag: v0.1.2-admin-quota-r1
digest: sha256:c95841cdb83ce33a01f348b86f6c137cc107ac65f2c00430f28e0d71c5e98448
```

### Frontend

```text
image: ghcr.io/andre-101/v4nex-frontend
tag: v0.1.2-admin-quota-r1
digest: sha256:84124e25bb4f57fc70446eaeddbe523cba384b7aa6251e84ca3898d0b0844d3a
```

## Componentes no modificados

### Caddy

```text
image: ghcr.io/andre-101/v4nex-caddy-cloudflare
tag: scenario-21-scratch-clean
digest: sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6
```

Caddy no debe recrearse para este release salvo drift o aprobacion manual explicita.

### Infraestructura

No se modifican:

- `docker-compose.prod.yml`
- `infra/caddy/Caddyfile.prod`
- DNS
- ACME
- Volumenes
- `.env.production`

## Migraciones

Este release requiere Alembic.

```text
alembic_required=true
alembic_command=alembic upgrade head
revision=202606170001
down_revision=202605260002
file=apps/backend/alembic/versions/202606170001_user_quota_admin_audit.py
```

Cambios:

- Agrega `users.bridge_limit`, con usuarios existentes inicializados en `1`.
- Agrega `users.is_active`, con usuarios existentes inicializados en `true`.
- Permite `admin_audit_events.actor_user_id` nullable.
- Agrega `admin_audit_events.target_user_id`.
- Agrega `admin_audit_events.bridge_id`.
- Agrega indices y foreign keys para los nuevos targets de auditoria.

Riesgo de migracion: `low`.

No hay eliminacion de datos en `upgrade`.

Rollback DB:

- El downgrade existe.
- El downgrade elimina columnas de auditoria target y columnas de cuota/estado.
- Si se requiere preservar exactamente auditoria producida por v0.1.2, se recomienda restore de backup en lugar de downgrade destructivo de columnas.

## Variables

El bloque operativo usado por scripts es `variables`.

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
BACKEND_IMAGE_TAG=v0.1.2-admin-quota-r1
FRONTEND_IMAGE_TAG=v0.1.2-admin-quota-r1
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

Recrear:

- `backend`
- `frontend`

No recrear:

- `db`
- `caddy`

Validar solamente:

- `caddy`

Requieren aprobacion manual para recreacion:

- `db`
- `caddy`

## Smoke esperado

### Smoke minimo

Requerido:

- `compose_config_valid`
- `services_healthy`
- `health_ok`
- `v4nex_health_ok`
- `protected_ports_not_published`
- `platform_mode_behavior_ok`
- `auth_me_ok`
- `bridge_list_ok`
- `admin_requires_admin_ok`

### Smoke extendido

No autorizado por defecto. Requiere aprobacion operativa explicita.

Checks posibles:

- `login_ok`
- `admin_user_list_ok`
- `admin_user_bridge_limit_update_ok`
- `user_quota_enforced_ok`
- `admin_user_suspend_ok`
- `inactive_user_blocked_ok`
- `admin_user_unsuspend_ok`
- `bridge_create_draft_ok`
- `bridge_detail_ok`
- `bridge_validate_ok`
- `bridge_ready_confirmed`
- `bridge_activate_ok`
- `bridge_active_confirmed`
- `admin_bridge_disable_ok`
- `bridge_public_url_ok`
- `platform_still_ok_after_actions`
- `internal_ports_not_published`

## Scans y riesgos conocidos

Docker Scout sobre las imagenes publicadas en GHCR reporto:

Backend:

```text
0 Critical
0 High
0 Medium
0 Low
packages: 93
size: 50 MB
```

Frontend:

```text
0 Critical
0 High
0 Medium
0 Low
packages: 1
size: 813 kB
```

`npm audit` local del frontend reporta 1 vulnerabilidad moderada en una dependencia de build/dev de Vite. La imagen runtime publicada no incluye Node, Vite ni el arbol de dependencias npm, y Scout sobre la imagen final reporta 0 vulnerabilidades. Queda como deuda tecnica de tooling local hasta que el entorno pueda subir a una linea de Vite que requiera Node mas nuevo.

## Rollback esperado

Rollback de backend:

```text
previous_backend_tag=scenario-37-bridge-management-api-r2
previous_backend_digest=sha256:15f02fe0857545a01299d0590b40e91ed4fed5de90130579ecd33be15b415f08
```

Rollback de frontend:

```text
previous_frontend_tag=scenario-37-bridge-management-ui
previous_frontend_digest=sha256:49582abd3db4e132f887acd380cd6300cf6b6b5a8cf9a8eab5c6dc2c6bdff204
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

Rollback DB:

- No requiere restore de DB para rollback app-only.
- Si se decide revertir la migracion, se debe tratar como accion DB separada y aprobada.

## Restricciones operativas

Obligatorias:

- No DNS.
- No ACME.
- No `down -v`.
- No borrar volumenes.
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

- Manifest valido.
- Tags no `latest`.
- Digests presentes.
- Sin secretos reales en manifest.
- Compose valido.
- `.env.production` protegido.
- Alembic upgrade exitoso.
- Redes IPv6 Docker preservadas.
- Puertos internos no publicados.
- Health checks OK.
- Backend y frontend recreados correctamente.
- Smoke minimo OK.
- Backend y frontend sin hallazgos critical/high.

NO-GO si ocurre:

- Manifest invalido.
- Tag `latest`.
- Secreto real detectado.
- Digest faltante.
- Compose invalido.
- `.env.production` ausente o desprotegido.
- Alembic upgrade falla.
- Redes IPv6 Docker ausentes.
- Puerto interno publicado.
- Health check falla.
- Recreate de backend/frontend falla.
- Smoke minimo falla.
- Hallazgo critical/high en backend o frontend.
- Se requiere DNS o ACME manual.
- Se requiere borrar volumenes.

## APP_RELEASE_HANDOFF_V0_1_2

- Release: `v4nex-v0.1.2`
- Status: `pending-infra-approval`
- Backend: `ghcr.io/andre-101/v4nex-backend:v0.1.2-admin-quota-r1@sha256:c95841cdb83ce33a01f348b86f6c137cc107ac65f2c00430f28e0d71c5e98448`
- Frontend: `ghcr.io/andre-101/v4nex-frontend:v0.1.2-admin-quota-r1@sha256:84124e25bb4f57fc70446eaeddbe523cba384b7aa6251e84ca3898d0b0844d3a`
- Caddy: unchanged, `scenario-21-scratch-clean`
- Migration: required, `alembic upgrade head`, revision `202606170001`
- Env updates: `BACKEND_IMAGE_TAG`, `FRONTEND_IMAGE_TAG`; keep `ALLOWED_TARGET_PORTS=80,8080`
- Recreate: `backend`, `frontend`
- Do not recreate: `db`, `caddy`
- Do not touch: DNS, ACME, Caddyfile base, volumes, `.env.production` except approved tag values
- Expected Infra next step: review manifest and approve or reject operational execution plan
