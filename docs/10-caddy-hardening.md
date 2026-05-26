# 10 - Hardening operativo local de Caddy dinámico

## Resumen ejecutivo

Este escenario endurece la operación local/dev de Caddy dinámico. Agrega serialización de operaciones que modifican Caddy, reconciliación DB -> Caddy y diagnóstico local autenticado sin exponer secretos.

La base de datos sigue siendo la fuente de verdad. Caddy se trata como estado derivado que puede regenerarse desde los bridges `ACTIVE`.

## Qué se implementó

- Lock local en proceso para operaciones Caddy:
  - `activate`
  - `disable`
  - `reconcile`
- Servicio `caddy_reconciler.py`.
- Endpoint autenticado:
  - `POST /_v4nex/admin/reconcile-caddy`
- Endpoint autenticado:
  - `GET /_v4nex/admin/diagnostics`
- Diagnóstico local sin secretos.
- Mejoras al script E2E:
  - mensaje claro si Docker IPv6 falla
  - validación de conectividad TCP desde backend hacia `demo-ipv6`

## Fuera de alcance

- TLS real.
- ACME.
- Cloudflare.
- DNS público real.
- VPS/deploy.
- CI/CD.
- Frontend funcional.
- Billing.
- Heartbeat real.
- Rate limiting real de producción.
- Métricas avanzadas de producción.
- Roles/admin complejos.
- Redis, Celery, Kubernetes o colas externas.

## Lock local

El lock vive en el servicio de aplicación de configuración Caddy. Serializa llamadas a:

- `activate_bridge_routes`
- `disable_bridge_routes`
- `apply_bridge_routes`
- reconciliación DB -> Caddy

Es suficiente para el MVP local de un solo proceso backend. No protege múltiples réplicas ni múltiples procesos. Antes de producción se necesita un lock distribuido o una arquitectura de reconciliación distinta.

## Reconciliación DB -> Caddy

Endpoint:

```http
POST /_v4nex/admin/reconcile-caddy
Authorization: Bearer TOKEN
```

Comportamiento:

1. Lee bridges `ACTIVE` desde PostgreSQL.
2. Genera configuración Caddy con esas rutas.
3. Aplica configuración usando el servicio Caddy existente.
4. Usa rollback si Caddy rechaza la configuración.
5. No cambia estados de bridges.

Respuesta:

```json
{
  "ok": true,
  "active_routes_count": 2,
  "error_code": "CADDY_OK",
  "message": "Caddy config loaded successfully.",
  "rollback_attempted": false,
  "rollback_ok": null
}
```

En este escenario basta con Bearer token de usuario existente. Producción debe hacerlo admin-only.

## Diagnóstico local

Endpoint:

```http
GET /_v4nex/admin/diagnostics
Authorization: Bearer TOKEN
```

Devuelve datos no sensibles:

- `app_env`
- `public_domain`
- `caddy_admin_url`
- `database_url_driver`
- `caddy_admin_reachable`
- `active_bridges_count`

No devuelve:

- `JWT_SECRET_KEY`
- contraseñas
- hashes de contraseña
- `DATABASE_URL` completo con credenciales

## Cómo correr tests

Desde `apps/backend`:

```bash
python -m pytest -p no:cacheprovider
```

## Cómo ejecutar E2E

Desde la raíz del repo:

```bash
bash scripts/e2e-local-ipv6-caddy.sh
```

El script valida Docker IPv6 antes de llamar al endpoint `validate`. Si Docker no puede crear o usar la red IPv6 dev, el script falla con un mensaje operativo claro.

## Recuperación manual DB/Caddy inconsistente

Si la DB indica bridges `ACTIVE`, pero Caddy perdió configuración dinámica:

1. Hacer login.
2. Llamar:

```bash
curl -X POST http://localhost:8000/_v4nex/admin/reconcile-caddy \
  -H "Authorization: Bearer TOKEN"
```

3. Revisar:

```bash
curl http://localhost:8000/_v4nex/admin/diagnostics \
  -H "Authorization: Bearer TOKEN"
docker compose logs backend
docker compose logs caddy
```

La reconciliación aplica DB -> Caddy. No muta estados de bridges.

## Riesgos pendientes antes de producción

- Reemplazar lock local por mecanismo seguro para múltiples procesos.
- Implementar roles/admin reales para endpoints internos.
- Diseñar reconciliación periódica o worker operacional.
- Agregar auditoría global de operaciones admin.
- Diseñar TLS/DNS reales.
- Definir rate limiting real.
- Agregar métricas operativas de producción.
