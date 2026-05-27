# Ronda 18 — Precedencia de rutas dinámicas Caddy para bridges

## Resumen ejecutivo

Ronda 17 cerró como NO-GO parcial porque la activación dinámica ya no rompía la plataforma base, pero la `public_url` del bridge activo devolvía el frontend de v4nex en lugar del servicio IPv6 destino.

Esta ronda corrige la precedencia de rutas dinámicas en Caddy: las rutas de bridges activos ahora se insertan antes de cualquier fallback frontend que pueda capturar subdominios, incluyendo rutas wildcard como `*.v4nex.com` y catch-all sin matcher.

No se tocó frontend, DNS, Cloudflare, ACME, VPS, GHCR, rsync, `.env.production`, Caddyfile base ni `docker-compose.prod.yml`.

## Resultado de Ronda 17

GO:

- Backend actualizado correctamente.
- Frontend actualizado correctamente.
- Caddyfile base no fue tocado.
- DNS no fue tocado.
- ACME no fue repetido manualmente.
- DB no fue recreada.
- Volúmenes no fueron borrados.
- Docker IPv6 productivo siguió funcionando.
- `v4nex.com`, `/health` y `/_v4nex/health` siguieron respondiendo antes/después de `activate`.
- Bridge pasó `DRAFT -> READY -> ACTIVE`.

NO-GO:

- La `public_url` del bridge respondió HTTP 200, pero devolvió el frontend base de v4nex.

## Causa raíz

La inyección dinámica anterior solo insertaba rutas de bridge antes del primer catch-all sin `match`.

Eso no cubría este caso productivo:

```text
[
  health/api route,
  apex frontend route,
  wildcard frontend route (*.v4nex.com -> frontend:80),
  catch-all frontend route
]
```

Si el wildcard frontend quedaba antes de `demo.v4nex.com`, Caddy evaluaba primero el fallback `*.v4nex.com` y enviaba el tráfico al frontend, aunque el bridge estuviera en `ACTIVE`.

## Corrección aplicada

Se ajustó `apps/backend/app/services/caddy_config.py`.

La estrategia nueva:

1. Lee y conserva la configuración viva de Caddy.
2. Elimina solo rutas dinámicas previas de bridges.
3. Construye rutas activas de bridges.
4. Calcula el índice correcto de inserción antes de cualquier fallback frontend que pueda capturar hosts de bridge.
5. Preserva rutas base, health/API, listen, TLS, admin config y `automatic_https`.

Funciones agregadas:

- `_bridge_route_insert_index(routes, public_domain)`
- `_route_can_capture_bridge_host(route, public_domain)`
- `_route_proxies_to_frontend(route)`

Casos de fallback frontend detectados:

- Ruta sin `match` que proxy a `frontend`.
- Ruta con host wildcard `*.v4nex.com` que proxy a `frontend`.
- Ruta con host bajo `*.v4nex.com` que proxy a `frontend`.
- Ruta con `subroute` que finalmente proxy a `frontend`.

No se mueven delante de:

- Rutas protegidas `/health`.
- Rutas protegidas `/_v4nex/*`.
- Ruta apex/base `v4nex.com`.
- Rutas que no proxy a frontend.

Orden esperado después de inyectar `demo.v4nex.com`:

```text
[
  health/api route,
  apex frontend route,
  demo.v4nex.com bridge route,
  wildcard frontend route,
  catch-all frontend route
]
```

## Tests agregados

Se actualizaron tests en `apps/backend/tests/test_caddy_activation.py`.

Nuevos casos relevantes:

- Bridge se inserta antes de fallback wildcard frontend.
- Bridge se inserta antes de fallback wildcard frontend dentro de `subroute`.
- Bridge conserva el orden obligatorio:
  - health/API
  - apex frontend
  - bridge específico
  - wildcard frontend
  - catch-all frontend
- Se mantiene la validación de inserción antes del catch-all.
- Se mantiene reemplazo de rutas dinámicas previas sin duplicados.
- Se mantiene falla segura si no hay HTTP servers.

## Validaciones ejecutadas

Tests focalizados:

```text
cd apps/backend
python -m pytest tests/test_caddy_activation.py -p no:cacheprovider
```

Resultado:

```text
19 passed, 1 warning in 0.20s
```

Suite backend completa:

```text
cd apps/backend
python -m pytest -p no:cacheprovider
```

Resultado:

```text
117 passed, 1 warning in 8.13s
```

Warning observado:

```text
PendingDeprecationWarning: Please use `import python_multipart` instead.
```

Checks estáticos:

- No `Frontend Skeleton`.
- No `Escenario 0`.
- No `backend:8000` hardcodeado en frontend.
- No `latest` en compose productivo.
- No `MVP` en UI productiva.
- No `demo visual`.
- No `frontend:5173` en `caddy_config.py`.
- No `":8080"` productivo en `caddy_config.py`.
- No `automatic_https disable true` en `caddy_config.py`.

`docker-compose.prod.yml`:

- `git diff -- docker-compose.prod.yml` no mostró cambios.
- Se confirmó que conserva:
  - `enable_ipv6: true`
  - `ipam`
  - `fd42:4e58:1501::/64`
  - `fd42:4e58:1502::/64`

## Frontend

Frontend no fue modificado en esta ronda.

Se mantiene:

```text
frontend: scenario-28-bridge-lifecycle-ui
```

## Riesgos

- La corrección depende de que rutas fallback frontend apunten a `frontend` o `frontend:<port>`.
- Si en el futuro aparecen subdominios de plataforma bajo `*.v4nex.com`, se debe añadir ownership explícito o lista reservada antes de permitir rutas dinámicas sobre esos hosts.
- La validación final debe hacerse en producción controlada confirmando que `public_url` ya no devuelve el frontend base.

## Restricciones respetadas

- No commit.
- No push.
- No GHCR.
- No rsync.
- No deploy.
- No VPS.
- No DNS.
- No Cloudflare.
- No ACME.
- No `.env.production`.
- No secretos reales.
- No CI/CD.
- No Caddyfile base.
- No `docker-compose.prod.yml`.

## SYNC app → infra — Ronda 18

### Qué cambió

Backend:

- Corrección en la inyección dinámica de rutas Caddy.
- Las rutas de bridges activos ahora se insertan antes de wildcard/catch-all frontend que puedan capturar subdominios.
- Se preserva la configuración viva de Caddy.
- Se preservan rutas base `v4nex.com`, `/health`, `/_v4nex/*`.
- Se preservan TLS/wildcard/apex, listen existente, admin config y `automatic_https`.

Frontend:

- Sin cambios.

Compose/infra:

- Sin cambios.
- `docker-compose.prod.yml` conserva IPv6 productivo.

### Tags sugeridos

Backend:

```text
scenario-30-caddy-route-precedence
```

Frontend:

```text
scenario-28-bridge-lifecycle-ui
```

### Variables

Nuevas variables:

```text
ninguna
```

Mantener:

```text
ALLOWED_TARGET_PORTS=80,8080
```

### Instrucciones para infra cuando app publique imagen backend

Actualizar solo backend:

```text
BACKEND_IMAGE_TAG=scenario-30-caddy-route-precedence
FRONTEND_IMAGE_TAG=scenario-28-bridge-lifecycle-ui
ALLOWED_TARGET_PORTS=80,8080
```

Pull/recreate controlado:

```text
docker compose pull backend
docker compose up -d backend
```

No tocar:

- Caddyfile base.
- DNS.
- ACME.
- Cloudflare.
- Volúmenes.
- DB.
- Caddy service.
- Redes IPv6.

### Pruebas esperadas

Antes de activar:

- `v4nex.com` responde.
- `/health` responde.
- `/_v4nex/health` responde.

Flujo bridge:

- Crear bridge `DRAFT`.
- Ejecutar `validate`.
- Confirmar `READY`.
- Ejecutar `activate`.
- Confirmar `ACTIVE`.
- Confirmar que `public_url` responde con el servicio IPv6 destino, no con el frontend base.

Después de activar:

- `v4nex.com` sigue respondiendo.
- `/health` sigue respondiendo.
- `/_v4nex/health` sigue respondiendo.
- No se publica `2019`, `5432`, `8000` ni `5173`.

### Decisión

GO local para preparar publicación de backend con:

```text
scenario-30-caddy-route-precedence
```

Producción final sigue no declarada hasta que infra confirme que `public_url` del bridge activo enruta al upstream IPv6 correcto.

