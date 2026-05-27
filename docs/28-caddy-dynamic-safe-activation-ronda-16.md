# 28 - Caddy dynamic safe activation - Ronda 16

## Resumen ejecutivo

Ronda 16 corrige la activacion dinamica de Caddy para que un bridge no reemplace la configuracion productiva base. La nueva estrategia lee la configuracion viva desde Caddy Admin API, preserva la configuracion existente, elimina solo rutas dinamicas previas de bridges e inserta las rutas activas antes del catch-all del frontend.

Tambien se agrega lifecycle minimo en frontend:

```text
DRAFT -> Validar -> READY -> Activar -> ACTIVE
```

No se hizo commit, push, GHCR, rsync, deploy, cambios DNS, Cloudflare API, ACME ni cambios en VPS.

## Problema de Ronda 15

Infra confirmo que:

- Infra publica: GO.
- TLS wildcard base: GO.
- Backend auth/API base: GO.
- Frontend creacion DRAFT: GO.
- Docker IPv6 productivo: GO.
- Backend container puede alcanzar servicios IPv6 destino: GO.
- Validacion TCP IPv6: GO.
- DRAFT -> READY: GO.
- Activacion API respondia 200 y backend podia reportar ACTIVE: parcial.
- Activacion dinamica Caddy: NO-GO.
- Frontend lifecycle validate/activate: NO-GO.

El fallo critico fue que despues de `POST /_v4nex/bridges/{bridge_id}/activate`, `v4nex.com:443` dejaba de responder correctamente. Al restaurar manualmente el Caddyfile productivo base, `v4nex.com`, `/health` y `/_v4nex/health` volvian a funcionar.

## Causa raiz

La causa raiz fue confirmada en codigo:

- `apps/backend/app/services/caddy_config.py` generaba una configuracion Caddy completa desde cero.
- Esa configuracion usaba `listen [":8080"]`.
- Esa configuracion establecia `automatic_https: {"disable": True}`.
- Esa configuracion apuntaba el frontend a `frontend:5173`.
- Al cargarla con `/load`, reemplazaba la configuracion productiva viva y removia la base TLS/rutas de plataforma.

## Decision tecnica

Se elimino el uso operativo de generacion completa desde cero.

La nueva estrategia:

1. Leer configuracion actual con `GET /config/`.
2. Hacer `deepcopy` de esa configuracion.
3. Detectar de forma segura el servidor HTTP publico existente.
4. Preservar `admin`, `listen`, `automatic_https`, TLS, rutas base y rutas de plataforma.
5. Remover solo rutas dinamicas anteriores de bridges.
6. Insertar rutas nuevas de bridges antes del catch-all frontend.
7. Cargar la configuracion completa preservada con `/load`.
8. Si falla `/load`, intentar rollback a `previous_config`.
9. Si la forma de la config no es soportada, fallar seguro sin llamar `/load`.

## Cambios backend

Archivos:

- `apps/backend/app/services/caddy_config.py`
- `apps/backend/app/services/caddy_activation.py`
- `apps/backend/tests/test_caddy_activation.py`

Funciones agregadas o cambiadas:

- `build_bridge_route(route: CaddyBridgeRoute) -> dict`
- `is_v4nex_dynamic_bridge_route(route: dict, public_domain: str) -> bool`
- `inject_bridge_routes(current_config: dict, routes: list[CaddyBridgeRoute]) -> dict`
- `CaddyConfigShapeError`
- `CADDY_CONFIG_SHAPE_UNSUPPORTED`

Reglas preservadas:

- No generar config productiva desde cero.
- No crear listener `:8080`.
- No establecer `automatic_https disable true`.
- No apuntar frontend productivo a `frontend:5173`.
- No eliminar `v4nex.com`.
- No eliminar `/health`.
- No eliminar `/_v4nex/*`.
- No eliminar TLS/wildcard/apex.
- No modificar Caddy Admin API.
- No asumir que el server se llama siempre `srv0`.
- No llamar `/load` si no se identifica exactamente un server publico seguro.

## Cambios frontend

Archivo:

- `apps/frontend/src/App.tsx`
- `apps/frontend/src/index.css`

Lifecycle agregado:

- Si `status = DRAFT`, mostrar boton `Validar`.
- `Validar` llama `POST /_v4nex/bridges/{bridge_id}/validate`.
- Si `status = READY`, mostrar boton `Activar`.
- `Activar` llama `POST /_v4nex/bridges/{bridge_id}/activate`.
- Si `status = ACTIVE`, mostrar `public_url` como enlace.
- Si `status = ERROR`, mostrar mensaje claro.
- Preview local puede simular `DRAFT -> READY -> ACTIVE`.

No se implemento:

- Disable desde UI.
- Metricas.
- Billing.
- Estetica final.

## Tests agregados

La suite Caddy cubre:

- `inject_bridge_routes` preserva `admin`.
- `inject_bridge_routes` preserva `listen`.
- `inject_bridge_routes` no crea `:8080`.
- `inject_bridge_routes` no establece `automatic_https disable true`.
- `inject_bridge_routes` preserva ruta de dominio base.
- `inject_bridge_routes` preserva `/health` y `/_v4nex/*`.
- `inject_bridge_routes` inserta bridge antes del catch-all frontend.
- `inject_bridge_routes` reemplaza rutas dinamicas previas sin duplicarlas.
- `inject_bridge_routes` falla seguro sin HTTP servers.
- `activate_bridge_routes` no llama `load_config` si la inyeccion falla.
- `activate_bridge_routes` hace rollback si `load_config` falla.
- Lock local de Caddy sigue activo.

La suite existente ya cubria que endpoint `activate` deja el bridge en `ERROR`, no `ACTIVE`, cuando Caddy activation falla.

## Validaciones ejecutadas

Backend:

```bash
cd apps/backend
python -m pytest -p no:cacheprovider
```

Resultado:

```text
114 passed, 1 warning in 9.34s
```

Frontend:

```bash
cd apps/frontend
npm install
npm run build
```

Resultado `npm install`:

```text
up to date, audited 136 packages
2 moderate severity vulnerabilities
```

Resultado `npm run build`:

```text
vite v5.4.21 building for production...
31 modules transformed.
dist/index.html                 0.41 kB
dist/assets/index-B74tGkMD.css  6.89 kB
dist/assets/index-jvCaDWwu.js   151.64 kB
built in 1.93s
```

Checks estaticos:

- No `Frontend Skeleton`.
- No `Escenario 0`.
- No `backend:8000` hardcodeado en frontend.
- No `latest` en compose productivo.
- No `MVP` en UI productiva.
- No `demo visual`.
- `docker-compose.prod.yml` no fue modificado.
- `caddy_config.py` ya no genera config productiva con listener `:8080`.
- No se establece `automatic_https: {"disable": True}` en la config dinamica.
- No se genera frontend productivo hacia `frontend:5173`.

## Riesgos

- La deteccion del server publico exige encontrar exactamente un servidor HTTP con ruta de `public_domain`. Si Caddy cambia la forma JSON futura, la activacion fallara seguro sin llamar `/load`.
- El frontend aun no implementa disable.
- Las vulnerabilidades moderadas de npm quedan como deuda no bloqueante.
- La validacion real de que `v4nex.com` sigue respondiendo antes/despues de activate debe hacerse en infra con VPS.

## Restricciones

- No DNS.
- No Cloudflare API.
- No ACME.
- No secretos reales.
- No `.env.production`.
- No CI/CD.
- No VPS.
- No rsync.
- No GHCR.
- No deploy.
- No tocar Caddyfile productivo base.

## Docker IPv6 productivo

Se preserva el commit:

```text
9b118fa infra: enable IPv6 Docker networks for production
```

`docker-compose.prod.yml` no fue modificado. No se revirtio `enable_ipv6`, `ipam`, subnets IPv6 ni la configuracion productiva de redes validada por infra.

## SYNC app -> infra - Ronda 16

### Que cambio en backend

- Activacion dinamica de Caddy ahora inyecta rutas sobre la configuracion viva.
- Se preserva configuracion base productiva.
- Si la forma de config no es reconocida, falla seguro y no llama `/load`.
- Si `/load` falla, intenta rollback a `previous_config`.
- No debe marcar `ACTIVE` si Caddy activation falla.

### Que cambio en frontend

- La UI minima ahora permite:
  - `DRAFT -> Validar`
  - `READY -> Activar`
  - `ACTIVE -> public_url como enlace`
- Preview local simula el lifecycle sin backend.
- No se agrego disable en UI.

### Imagenes GHCR

Esta ronda requiere nuevas imagenes GHCR cuando sea aprobada.

Tags sugeridos:

```text
backend: scenario-28-caddy-safe-activation
frontend: scenario-28-bridge-lifecycle-ui
```

### Variables

No cambian variables productivas.

Mantener:

```env
ALLOWED_TARGET_PORTS=80,8080
```

### Rsync

No se hizo rsync. Si infra necesita inspeccionar artefactos antes de imagenes, coordinar explicitamente. La ruta preferida sigue siendo publicar imagenes GHCR y hacer pull controlado.

### Instrucciones de infra cuando app autorice

1. Pull de nuevas imagenes backend/frontend.
2. Actualizar tags backend/frontend en `.env.production`.
3. Recrear solo backend/frontend.
4. No tocar Caddy.
5. No repetir ACME.
6. No modificar DNS.
7. No borrar volumenes.
8. No ejecutar `down -v`.
9. No publicar `2019`, `5432`, `8000` ni `5173`.
10. No tocar Caddyfile base salvo autorizacion explicita.

### Pruebas esperadas

Antes y despues de `activate`:

- `https://v4nex.com` sigue OK.
- `https://v4nex.com/health` sigue OK.
- `https://v4nex.com/_v4nex/health` sigue OK.
- Bridge puede recorrer `DRAFT -> READY -> ACTIVE`.
- `public_url` del bridge responde.
- Caddy Admin API sigue interna.
- Docker IPv6 productivo sigue funcionando.

### Restricciones activas

- No DNS.
- No ACME.
- No borrar volumenes.
- No `down -v`.
- No publicar `2019/5432/8000/5173`.
- No tocar Caddyfile base salvo autorizacion explicita.

### Supuesto de identificación de rutas dinámicas

La limpieza de rutas dinámicas asume el contrato actual del producto:

- La plataforma vive en `v4nex.com`.
- Los bridges de clientes viven bajo `*.v4nex.com`.
- Una ruta dinámica de bridge se identifica por host subdominio de `v4nex.com` y upstream IPv6 bracketed, por ejemplo `[IPv6]:80`.

Este supuesto es válido para el MVP. Si en el futuro la plataforma usa subdominios propios como `status.v4nex.com`, `api.v4nex.com` o `panel.v4nex.com` con upstream IPv6, se debe cambiar la detección por un marcador explícito de ownership o una lista de subdominios reservados.
