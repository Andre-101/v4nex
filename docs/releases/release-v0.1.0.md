# Release v0.1.0 — Contrato formal de entrega

## Resumen

Release `v0.1.0` define una entrega funcional controlada para producción. El objetivo es permitir que Infra revise, apruebe y ejecute una actualización acotada del backend para validar el ciclo de bridges con precedencia correcta de rutas dinámicas en Caddy.

Estado del contrato:

- Release ID: `v4nex-v0.1.0`
- Ambiente: `production`
- Tipo: `functional-controlled`
- Estado: `pending-infra-approval`
- Aprobado por App: `true`
- Aprobado por Infra: `false`

Infra no debe ejecutar deploy, rsync, scripts, cambios en VPS, DNS, ACME, Caddyfile base, `.env.production` ni volúmenes hasta aprobar este contrato.

## Alcance

Incluido:

- Validar y usar una nueva imagen backend.
- Mantener la imagen frontend actual.
- Mantener la imagen Caddy custom actual.
- Ejecutar preflight, smoke mínimo, smoke extendido y drift checks.
- Validar que `public_url` de un bridge activo responda el servicio IPv6 destino y no el frontend base.
- Mantener la plataforma temporalmente cerrada.

Fuera de alcance:

- Cambios DNS.
- Repetición manual de ACME.
- Cambios en Caddyfile base.
- Recreación de DB.
- Borrado de volúmenes.
- Publicación de puertos internos.
- Sobrescritura de `.env.production`.
- CI/CD.
- Cambios de imágenes no declaradas en este contrato.

## Componentes

### Backend

```text
image: ghcr.io/andre-101/v4nex-backend
tag: scenario-30-caddy-route-precedence
digest: sha256:836621299ab130898582ef68de06be29ce036f833538036a52209f94758b5d40
required: true
requires_recreate: true
recreate_policy: recreate
```

### Frontend

```text
image: ghcr.io/andre-101/v4nex-frontend
tag: scenario-28-bridge-lifecycle-ui
digest: sha256:cda53670de09627d80e98c65f2eff3428f551314ec9c8c28f7039b501cb3c175
required: true
requires_recreate: false
recreate_policy: validate_only
```

### Caddy

```text
image: ghcr.io/andre-101/v4nex-caddy-cloudflare
tag: scenario-21-scratch-clean
digest: sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6
required: true
requires_recreate: false
recreate_policy: no_recreate_unless_drift_or_manual_approval
```

## Variables

Variables no secretas esperadas:

```text
BACKEND_IMAGE_TAG: scenario-30-caddy-route-precedence
FRONTEND_IMAGE_TAG: scenario-28-bridge-lifecycle-ui
CADDY_IMAGE_TAG: scenario-21-scratch-clean
ALLOWED_TARGET_PORTS: 80,8080
```

Variables sensibles requeridas solo por nombre:

- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- `CLOUDFLARE_API_TOKEN`
- `CADDY_ACME_EMAIL`

El contrato no contiene valores reales para variables sensibles.

## Migraciones

```text
alembic_required: false
alembic_command: null
migration_risk: low
rollback_requires_db_restore: false
```

No se requiere ejecutar Alembic para este release.

## Plataforma

La plataforma debe permanecer temporalmente cerrada:

```text
platform_mode: closed_temporarily
```

El release no declara apertura pública general ni producción final.

## Bridge Smoke

Smoke extendido habilitado:

```text
enabled: true
test_subdomain_prefix: smoke
target_ipv6: null
target_port: 8080
expected_body_markers: []
cleanup_policy: keep_or_delete_explicit
```

`target_ipv6` debe definirse operativamente fuera del manifest, en inventario o procedimiento controlado por Infra.

## Cleanup

Política de cleanup:

```text
delete_smoke_bridge_after_success: false
restore_caddy_base_after_success: false
keep_dynamic_route_after_success: true
```

No se restaura Caddy base automáticamente tras éxito. La ruta dinámica puede mantenerse para inspección posterior, salvo decisión explícita de Infra.

## Deployment Policy

Servicios a recrear:

- `backend`

Servicios que no deben recrearse:

- `db`

Servicios solo a validar:

- `caddy`
- `frontend`

Requieren aprobación manual:

- `caddy`
- `db`

No debe recrearse frontend salvo que Infra detecte drift real o exista aprobación explícita.

## Recursos protegidos

No modificar ni sobrescribir:

- `.env.production`
- `app_postgres_data`
- `app_caddy_data`
- `app_caddy_config`
- `docker-compose.prod.yml`
- `infra/caddy/Caddyfile.prod`

## Restricciones

Restricciones obligatorias:

- No usar tags `latest`.
- No ejecutar `down -v`.
- No cambiar DNS.
- No repetir ACME manualmente.
- No cambiar Caddyfile base.
- No publicar puertos internos.
- No sobrescribir `.env.production`.

## Reportes

Rutas esperadas:

```text
preflight_report_path: /opt/v4nex/runtime/preflight-v0.1.0-<timestamp>.txt
deploy_report_path: /opt/v4nex/runtime/deploy-v0.1.0-<timestamp>.txt
smoke_report_path: /opt/v4nex/runtime/smoke-v0.1.0-<timestamp>.txt
rollback_report_path: /opt/v4nex/runtime/rollback-v0.1.0-<timestamp>.txt
release_current_path: /opt/v4nex/runtime/release-current.json
runtime_artifacts_path: /opt/v4nex/runtime
```

## Preflight

Checks requeridos:

- `app_base_path_exists`
- `env_file_exists`
- `env_file_permissions_600`
- `docker_available`
- `compose_config_valid`
- `required_env_keys_present`
- `ghcr_pull_available`
- `digests_match`
- `docker_ipv6_networks_enabled`
- `app_control_ipv6_enabled`
- `app_edge_ipv6_enabled`
- `caddyfile_base_exists`
- `protected_ports_not_published`
- `caddy_admin_not_public`
- `caddy_healthy`
- `backend_healthy`
- `frontend_healthy`
- `db_healthy`
- `critical_volumes_exist`

## Smoke Minimal

Checks requeridos:

- `compose_config_valid`
- `services_healthy`
- `health_ok`
- `v4nex_health_ok`
- `protected_ports_not_published`
- `platform_mode_behavior_ok`

## Smoke Extended

Checks requeridos:

- `login_ok`
- `bridge_create_draft_ok`
- `bridge_validate_ok`
- `bridge_ready_confirmed`
- `bridge_activate_ok`
- `bridge_active_confirmed`
- `bridge_public_url_ok`
- `bridge_public_url_not_frontend`
- `platform_still_ok_after_activate`
- `internal_ports_not_published`

## Drift Checks

Checks requeridos:

- `docker_compose_prod_ipv6`
- `caddyfile_base_hash_or_presence`
- `env_file_permissions`
- `caddy_admin_not_public`
- `internal_ports_not_public`
- `running_image_tags_match_manifest`

## Rollback

Backend anterior:

```text
previous_backend_tag: scenario-28-caddy-safe-activation
previous_backend_digest: sha256:c34aaf21abff116195fad2c348e28472cf50e36c896a5c5745f7224a5e32e2c9
```

Frontend anterior:

```text
previous_frontend_tag: scenario-28-bridge-lifecycle-ui
previous_frontend_digest: sha256:cda53670de09627d80e98c65f2eff3428f551314ec9c8c28f7039b501cb3c175
```

Caddy anterior:

```text
previous_caddy_tag: scenario-21-scratch-clean
previous_caddy_digest: sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6
```

Rollback services:

- `backend`

Rollback env keys:

- `BACKEND_IMAGE_TAG`

Políticas:

- `rollback_requires_db_restore: false`
- `rollback_requires_caddy_restore: false`
- `rollback_max_time_minutes: 10`
- `frontend_rollback_policy: no_rollback_unless_manual_approval`
- `caddy_rollback_policy: no_rollback_unless_manual_approval`
- `db_rollback_policy: no_rollback_without_backup_restore_plan`

Validación de rollback:

- `health_ok`
- `v4nex_health_ok`
- `caddy_healthy`
- `backend_healthy`
- `db_healthy`
- `internal_ports_not_published`

## GO Criteria

Un GO requiere:

- `release_manifest_valid`
- `no_latest_image_tags`
- `no_secrets_in_manifest`
- `required_digests_present`
- `docker_compose_config_valid`
- `env_file_protected`
- `backend_digest_matches`
- `docker_ipv6_networks_enabled`
- `internal_ports_not_published`
- `platform_health_ok`
- `bridge_lifecycle_ok`
- `public_url_returns_ipv6_target`
- `public_url_not_frontend_base`

## NO-GO Criteria

Debe declararse NO-GO si ocurre cualquiera de estos casos:

- `manifest_invalid`
- `latest_image_tag_detected`
- `secret_value_detected`
- `missing_required_digest`
- `docker_compose_config_failed`
- `env_file_missing_or_unprotected`
- `backend_digest_mismatch`
- `docker_ipv6_networks_missing`
- `internal_port_published`
- `platform_health_failed`
- `bridge_lifecycle_failed`
- `public_url_returns_frontend_base`
- `manual_dns_or_acme_required`
- `volume_deletion_required`

## Entrega a Infra

Archivos de contrato:

- `releases/v0.1.0.json`
- `docs/releases/release-v0.1.0.md`

Infra debe revisar el manifest, validar preflight y aprobar explícitamente antes de cualquier acción operativa.

