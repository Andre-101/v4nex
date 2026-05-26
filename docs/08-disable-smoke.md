# 08 - Disable controlado y smoke Caddy dev

## Resumen ejecutivo

Este escenario agrega desactivación controlada de bridges activos. La operación actualiza Caddy dev para remover la ruta dinámica del bridge, mantiene las rutas de otros bridges `ACTIVE` y aplica rollback si Caddy rechaza la configuración.

No se implementa TLS real, ACME, Cloudflare, DNS público, deploy, CI/CD ni frontend funcional.

## Qué se implementó

- Endpoint autenticado:
  - `POST /_v4nex/bridges/{bridge_id}/disable`
- Reutilización de la arquitectura Caddy del Escenario 7.
- Aplicación de rutas Caddy con todos los bridges `ACTIVE` excepto el bridge desactivado.
- Rollback a configuración previa si falla la carga de Caddy.
- Código estándar `CADDY_DISABLE_FAILED`.
- Eventos de desactivación.
- Tests con monkeypatch/mock, sin dependencia de Caddy real en pytest.

## Fuera de alcance

- TLS real.
- ACME.
- Cloudflare.
- DNS público real.
- Deploy.
- CI/CD.
- Frontend funcional.
- Billing.
- Heartbeat real.
- Rate limiting real.
- Métricas avanzadas.

## Flujo ACTIVE -> DISABLED / ERROR

1. El usuario autenticado solicita `POST /_v4nex/bridges/{bridge_id}/disable`.
2. El backend valida ownership.
3. El backend exige estado `ACTIVE`.
4. Se crea evento `CADDY_DISABLE_STARTED`.
5. Se genera una nueva configuración Caddy con todos los bridges `ACTIVE` excepto el bridge actual.
6. Se intenta cargar la configuración en Caddy Admin API.
7. Si Caddy acepta:
   - `status = DISABLED`
   - `disabled_at = now`
   - evento `CADDY_DISABLE_PASSED`
8. Si Caddy falla:
   - intenta rollback a configuración previa
   - `status = ERROR`
   - evento `CADDY_DISABLE_FAILED`
   - respuesta estándar `CADDY_DISABLE_FAILED`

Transiciones usadas:

- `ACTIVE -> DISABLED`
- `ACTIVE -> ERROR`

No se permite desactivar desde `DRAFT`, `READY`, `ERROR` ni `DISABLED`.

## Eventos generados

- `CADDY_DISABLE_STARTED`
- `CADDY_DISABLE_PASSED`
- `CADDY_DISABLE_FAILED`

Metadata permitida:

- `subdomain`
- `public_url`
- `target_ipv6`
- `target_port`
- `error_code`
- `rollback_attempted`
- `rollback_ok`

No se guardan secretos en metadata.

## Rollback

La desactivación usa el mismo patrón de rollback que activación:

1. Leer configuración actual de Caddy.
2. Intentar cargar configuración nueva sin el bridge desactivado.
3. Si falla, intentar restaurar la configuración previa.

El error incluye:

```json
{
  "error_code": "CADDY_CONFIG_REJECTED",
  "message": "Human readable message",
  "rollback_attempted": true,
  "rollback_ok": true
}
```

## Cómo correr tests

Desde `apps/backend`:

```bash
python -m pytest -p no:cacheprovider
```

Los tests de disable no dependen de Caddy real. El endpoint usa monkeypatch del servicio Caddy y el servicio se prueba con cliente simulado.

## Smoke manual Docker/Caddy dev

Desde la raíz del repo:

```bash
docker compose up -d db caddy
docker compose run --rm backend alembic upgrade head
docker compose up -d backend frontend
```

Flujo manual:

1. Registrar usuario.
2. Hacer login.
3. Crear bridge.
4. Validar bridge hasta `READY`.
5. Activar bridge hasta `ACTIVE`.
6. Desactivar bridge hasta `DISABLED`.
7. Revisar logs:

```bash
docker compose logs backend
docker compose logs caddy
```

Si no hay DNS/hosts local para el subdominio, validar por estado API y logs. Opcionalmente se puede probar con Host header:

```bash
curl -H "Host: demo.v4nex.com" http://localhost:8080/
```

Limitación: sin DNS local o entrada en hosts, el navegador no resolverá `demo.v4nex.com` hacia el Caddy dev local.

Si el entorno no tiene un servicio IPv6 escuchando en puerto `80`, el smoke completo de validación TCP puede no llegar a `READY`. Para aislar solo Caddy dev en un entorno controlado, se puede crear el bridge, marcarlo `READY` en PostgreSQL de desarrollo y probar `activate`/`disable`. Ese atajo no reemplaza la validación TCP real; solo sirve para comprobar que Caddy Admin API acepta la activación y la desactivación dinámicas.

## Riesgos y pendientes

- Probar smoke real completo con hosts local controlado.
- Agregar protección contra operaciones concurrentes `activate/disable`.
- Definir estrategia de reconciliación entre DB y configuración Caddy.
- Preparar TLS/DNS reales en escenarios posteriores.
- Agregar observabilidad mínima de cambios de configuración.
