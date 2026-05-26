# 12 - Hardening local del control plane

## Resumen ejecutivo

Este escenario agrega controles minimos al control plane local/dev de v4nex: roles `USER` / `ADMIN`, proteccion admin real para endpoints internos, cuota basica de bridges por usuario, rate limiting en memoria para operaciones sensibles y auditoria admin minima.

El objetivo es reducir abuso accidental o evidente antes de pensar en despliegue real. Sigue siendo una implementacion local/dev: no hay Redis, no hay rate limiting distribuido, no hay roles complejos y no hay deploy productivo.

## Que se implemento

- Columna `role` en `users`.
- Rol por defecto `USER` para registros nuevos.
- Dependencia `require_admin_user()`.
- Error estandar `FORBIDDEN`.
- Proteccion admin para:
  - `POST /_v4nex/admin/reconcile-caddy`
  - `GET /_v4nex/admin/diagnostics`
- Cuota local:
  - `MAX_BRIDGES_PER_USER=5`
- Error estandar:
  - `BRIDGE_QUOTA_EXCEEDED`
- Rate limiting local/in-memory.
- Error estandar:
  - `RATE_LIMIT_EXCEEDED`
- Modelo `AdminAuditEvent`.
- Auditoria para:
  - `ADMIN_RECONCILE_CADDY_STARTED`
  - `ADMIN_RECONCILE_CADDY_FINISHED`
  - `ADMIN_DIAGNOSTICS_VIEWED`
- Diagnostics extendido con:
  - `rate_limit_enabled`
  - `max_bridges_per_user`
  - `admin_endpoints_protected`

## Fuera de alcance

- TLS real.
- ACME.
- Cloudflare.
- DNS publico.
- Compose productivo.
- VPS/deploy.
- CI/CD.
- Frontend funcional.
- Redis, Celery o Kubernetes.
- Rate limiting distribuido.
- Billing.
- Roles complejos o panel admin.
- Bootstrap productivo de usuario admin.

## Roles USER/ADMIN

Roles oficiales:

- `USER`: rol normal para usuarios registrados por API.
- `ADMIN`: rol operacional para endpoints internos.

Reglas:

- `POST /_v4nex/auth/register` siempre crea usuarios `USER`.
- No existe endpoint publico para convertirse en `ADMIN`.
- No existe usuario admin hardcodeado.
- En tests se puede elevar un usuario directamente desde la DB.
- El bootstrap admin productivo queda pendiente.

## Proteccion de endpoints admin

Los endpoints admin requieren:

1. Bearer token valido.
2. Usuario existente.
3. `role == ADMIN`.

Si no hay token:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Bearer token is required.",
    "details": {}
  }
}
```

Si el usuario no es admin:

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Admin privileges are required.",
    "details": {}
  }
}
```

## Cuota de bridges por usuario

Configuracion:

```env
MAX_BRIDGES_PER_USER=5
```

Reglas MVP:

- La cuota cuenta todos los bridges del usuario, sin importar estado.
- La cuota es por usuario, no global.
- Si el usuario alcanza el limite, `POST /_v4nex/bridges` responde:

```json
{
  "error": {
    "code": "BRIDGE_QUOTA_EXCEEDED",
    "message": "Bridge quota exceeded for this user.",
    "details": {
      "max_bridges_per_user": 5
    }
  }
}
```

Cuotas por plan comercial quedan fuera de alcance.

## Rate limiting local/in-memory

Configuracion:

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MAX_REQUESTS=30
RATE_LIMIT_STRICT_MAX_REQUESTS=10
```

Operaciones protegidas:

- `POST /_v4nex/auth/register`
- `POST /_v4nex/auth/login`
- `POST /_v4nex/bridges/{bridge_id}/validate`
- `POST /_v4nex/bridges/{bridge_id}/activate`
- `POST /_v4nex/bridges/{bridge_id}/disable`
- `POST /_v4nex/admin/reconcile-caddy`

Este rate limiting vive en memoria del proceso backend. Es suficiente para desarrollo local y tests, pero no protege multiples procesos ni multiples replicas.

Produccion requiere Redis, rate limiting en reverse proxy o mecanismo equivalente.

## Auditoria admin minima

Modelo:

- `AdminAuditEvent`

Campos:

- `id`
- `actor_user_id`
- `action`
- `message`
- `metadata`
- `created_at`

Eventos registrados:

- `ADMIN_RECONCILE_CADDY_STARTED`
- `ADMIN_RECONCILE_CADDY_FINISHED`
- `ADMIN_DIAGNOSTICS_VIEWED`

La metadata no debe contener secretos, passwords, tokens ni `DATABASE_URL` completa.

## Como correr tests

Desde `apps/backend`:

```bash
python -m pytest -p no:cacheprovider
```

## Como correr E2E

Desde la raiz del repo:

```bash
bash scripts/e2e-local-ipv6-caddy.sh
```

El E2E normal registra usuarios `USER` y no depende de endpoints admin.

## Limitaciones antes de produccion

- Falta bootstrap admin seguro.
- Falta rate limiting distribuido.
- Falta lock distribuido si hay multiples procesos backend.
- Falta politica de cuotas por usuario/plan.
- Falta auditoria operacional completa.
- Falta monitoreo y alertas de abuso.
- Falta firewall y secrets productivos.

## Pendientes para Escenario 13

- Definir bootstrap admin seguro para entorno no local.
- Preparar compose productivo o seguir endureciendo control plane.
- Agregar rate limiting productivo.
- Agregar politicas de abuso y suspension.
- Evaluar logs/auditoria exportables.
- Preparar smoke de VPS sin abrir deploy productivo todavia.
