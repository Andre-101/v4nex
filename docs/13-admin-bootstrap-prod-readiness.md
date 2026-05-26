# 13 - Bootstrap admin y readiness productivo controlado

## Resumen ejecutivo

Este escenario agrega un mecanismo interno para crear o promover el primer usuario `ADMIN` sin exponer un endpoint publico. Tambien agrega validaciones testeables de configuracion no-dev para detectar secretos inseguros y configuraciones sensibles antes de pensar en produccion.

No se ejecuta deploy, no se emiten certificados TLS reales, no se integra Cloudflare y no se crea `docker-compose.prod.yml`.

## Que se implemento

- Script operador:
  - `scripts/bootstrap-admin.sh`
- Modulo interno:
  - `app.cli.bootstrap_admin`
- Bootstrap admin con dos modos:
  - promover usuario existente a `ADMIN`
  - crear usuario `ADMIN` si no existe
- Reutilizacion de `hash_password`.
- Validacion de variables requeridas:
  - `ADMIN_EMAIL`
  - `DATABASE_URL`
- `ADMIN_PASSWORD` requerido solo cuando el usuario no existe.
- Checks no-dev testeables:
  - JWT dev default bloqueable fuera de dev/test
  - SQLite fuera de dev/test
  - Caddy Admin URL publica
  - `PUBLIC_DOMAIN` no configurado explicitamente
  - rate limit apagado
- Settings ahora lee `PUBLIC_DOMAIN`.

## Fuera de alcance

- Endpoint API para crear admins.
- Usuario admin hardcodeado.
- TLS real.
- ACME.
- Cloudflare API.
- DNS publico.
- Deploy.
- CI/CD.
- Frontend funcional.
- Billing.
- Redis, Celery o Kubernetes.
- Secret manager real.

## Crear o promover el primer admin

El bootstrap debe ejecutarse manualmente por un operador en entorno controlado, con acceso a la base de datos y variables de entorno correctas.

Promover usuario existente:

```bash
export DATABASE_URL="postgresql+psycopg://..."
export ADMIN_EMAIL="operator@example.com"
bash scripts/bootstrap-admin.sh
```

Crear usuario admin si no existe:

```bash
export DATABASE_URL="postgresql+psycopg://..."
export ADMIN_EMAIL="operator@example.com"
export ADMIN_PASSWORD="use-a-strong-secret"
bash scripts/bootstrap-admin.sh
```

El script no imprime `ADMIN_PASSWORD` y no guarda secretos.

## Variables requeridas

- `DATABASE_URL`: obligatoria para conectar a la DB objetivo.
- `ADMIN_EMAIL`: obligatoria.
- `ADMIN_PASSWORD`: opcional si el usuario ya existe; obligatoria si se debe crear.

Variables relacionadas con readiness no-dev:

- `APP_ENV`
- `JWT_SECRET_KEY`
- `PUBLIC_DOMAIN`
- `CADDY_ADMIN_URL`
- `RATE_LIMIT_ENABLED`

## Advertencias de seguridad

- Ejecutar solo desde una terminal de operador confiable.
- No commitear `.env.production`.
- No copiar `ADMIN_PASSWORD` a logs, tickets o historial compartido.
- Preferir password temporal y rotacion posterior cuando exista UI/flujo seguro.
- No exponer este flujo como endpoint HTTP.
- En produccion futura, idealmente reemplazar por un procedimiento de bootstrap auditado y con secret manager.

## Startup checks no-dev

Modulo:

```python
from app.core.startup_checks import collect_startup_check_issues
```

Los checks no bloquean desarrollo ni tests. Para `APP_ENV` distinto de `development` / `test`, detectan:

- `JWT_SECRET_KEY=dev-only-change-me`
- `DATABASE_URL` SQLite
- `CADDY_ADMIN_URL` con host publico
- `PUBLIC_DOMAIN` no configurado explicitamente por entorno
- `RATE_LIMIT_ENABLED=false`

Todavia no se ejecutan automaticamente al arrancar la app para evitar romper entornos locales. Deben integrarse al proceso productivo futuro antes de abrir trafico publico.

## Checklist pre-produccion

- Primer admin creado/promovido por operador.
- `JWT_SECRET_KEY` real y rotado.
- `DATABASE_URL` apunta a Postgres real/controlado.
- `PUBLIC_DOMAIN` definido explicitamente.
- `CADDY_ADMIN_URL` interno, no publico.
- `RATE_LIMIT_ENABLED=true`.
- Endpoints admin verificados como admin-only.
- No existe endpoint publico de bootstrap admin.
- Logs revisados para evitar secretos.
- Backups y restore documentados.
- Firewall listo.

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

El E2E normal no depende de endpoints admin ni del bootstrap.

## Pendientes para Escenario 14

- Decidir si se integra `assert_startup_checks()` al arranque en modo no-dev.
- Preparar compose productivo sin desplegar.
- Definir secret management real.
- Agregar procedimiento de rotacion de admin/password.
- Diseñar auditoria exportable.
- Definir rate limiting productivo.
- Preparar smoke controlado de VPS sin abrir trafico publico.
