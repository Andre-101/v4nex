# 07 - Caddy dinámico controlado con rollback

## Resumen ejecutivo

Este escenario agrega activación controlada de bridges `READY` contra Caddy Admin API en desarrollo. La activación genera una configuración dinámica HTTP/dev, la carga en Caddy y marca el bridge como `ACTIVE` solo si Caddy acepta la configuración.

No se implementa TLS real, ACME, Cloudflare, DNS público, deploy ni frontend funcional.

## Qué se implementó

- Endpoint autenticado:
  - `POST /_v4nex/bridges/{bridge_id}/activate`
- Servicios internos:
  - `caddy_config.py`: renderiza configuración Caddy controlada.
  - `caddy_client.py`: encapsula Caddy Admin API.
  - `caddy_activation.py`: orquesta lectura de config actual, carga de nueva config y rollback.
- Habilitación explícita de Caddy Admin API para desarrollo.
- Variables de entorno dev para Caddy Admin API.
- Eventos de activación.
- Tests con monkeypatch/mock sin depender de Caddy real.

## Fuera de alcance

- TLS real.
- Certificados ACME.
- Cloudflare.
- DNS real.
- Wildcard real.
- Deploy.
- CI/CD.
- Frontend funcional.
- Billing.
- Heartbeat real.
- Rate limiting real.
- Métricas avanzadas.
- Endpoint `disable`.

## Variables de entorno

```env
CADDY_ADMIN_URL=http://caddy:2019
CADDY_ADMIN_TIMEOUT_SECONDS=3
```

Estas variables son para desarrollo Docker. El puerto `2019` no se expone al host en `docker-compose.yml`; el backend accede a Caddy por la red interna de Compose.

## Flujo READY -> ACTIVE / ERROR

1. El usuario autenticado solicita `POST /_v4nex/bridges/{bridge_id}/activate`.
2. El backend valida ownership.
3. El backend exige estado `READY`.
4. Se crea evento `CADDY_ACTIVATION_STARTED`.
5. El servicio de activación obtiene la configuración actual de Caddy.
6. Se genera nueva configuración con bridges activos y el bridge candidato.
7. Se carga la nueva configuración en Caddy.
8. Si Caddy acepta:
   - `status = ACTIVE`
   - `activated_at = now`
   - evento `CADDY_ACTIVATION_PASSED`
9. Si Caddy falla:
   - intenta rollback a la configuración previa
   - `status = ERROR`
   - evento `CADDY_ACTIVATION_FAILED`
   - respuesta estándar `CADDY_ACTIVATION_FAILED`

Transiciones usadas:

- `READY -> ACTIVE`
- `READY -> ERROR`

No se permite activar desde `DRAFT`, `ERROR`, `DISABLED` ni `ACTIVE`.

## Eventos generados

- `CADDY_ACTIVATION_STARTED`
- `CADDY_ACTIVATION_PASSED`
- `CADDY_ACTIVATION_FAILED`

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

El servicio de activación:

1. Lee la configuración actual con Caddy Admin API.
2. Intenta cargar la nueva configuración.
3. Si la carga falla, intenta restaurar la configuración previa.

El error de activación incluye:

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

Los tests no dependen de Caddy real. El servicio Caddy se prueba con clientes simulados y el endpoint se prueba con monkeypatch del orquestador.

## Smoke manual opcional

Desde la raíz del repo:

```bash
docker compose up -d db caddy
docker compose run --rm backend alembic upgrade head
docker compose up -d backend
```

Flujo manual:

1. Registrar usuario.
2. Hacer login.
3. Crear bridge.
4. Validar bridge hasta `READY`.
5. Activar bridge.
6. Confirmar `status=ACTIVE`.
7. Revisar logs:

```bash
docker compose logs backend
docker compose logs caddy
```

Limitación: este escenario no configura DNS local ni wildcard real, por lo que confirmar tráfico de usuario final por subdominio puede requerir hosts locales o tooling adicional. La activación comprueba que Caddy acepta la configuración dinámica.

## Riesgos y pendientes

- Diseñar endpoint `disable` con rollback y eliminación segura de rutas.
- Definir estrategia para TLS real y certificados.
- Definir DNS/wildcard real antes de producción.
- Agregar pruebas de concurrencia para activaciones simultáneas.
- Evaluar si la generación de configuración debe migrar a JSON más granular por ruta en lugar de reemplazar config completa.
