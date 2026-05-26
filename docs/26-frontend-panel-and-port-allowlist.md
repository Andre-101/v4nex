# 26 - Frontend panel and port allowlist

## Resumen ejecutivo

Ronda 13A implementa una primera version visual realista del frontend publico de v4nex y cambia la validacion backend de `target_port` desde un unico puerto fijo hacia una allowlist configurable. El objetivo es permitir bridges web/lab hacia `80` y `8080` sin abrir puertos sensibles ni modificar infraestructura.

No se hizo push Git, no se publico GHCR, no se hizo rsync, no se toco la VPS, no se ejecuto deploy, no se repitio ACME, no se llamo Cloudflare API y no se modifico DNS.

## Problema detectado

- El frontend publicado seguia mostrando el skeleton inicial.
- El backend aceptaba solamente `target_port=80`.
- Un bridge hacia `8080` fue rechazado por `validate_port()`.
- El mensaje de fallo TCP hablaba explicitamente de puerto `80`, aunque el puerto debe depender de la configuracion del bridge.

## Decisiones tomadas

- Frontend:
  - Implementar una UI SaaS/infraestructura edge con identidad visual aprobada.
  - Usar fondo `#07111F`, cyan `#22D3EE`, violeta `#7C3AED`, texto claro `#E5E7EB` y texto secundario `#94A3B8`.
  - Usar solo rutas relativas bajo `/_v4nex`.
  - Guardar token en `sessionStorage`.
  - No mostrar token ni password.
  - No ejecutar validate/activate/disable desde UI todavia.

- Backend:
  - Crear `DEFAULT_ALLOWED_TARGET_PORTS = frozenset({80, 8080})`.
  - Leer `ALLOWED_TARGET_PORTS` desde settings si existe.
  - Mantener `80,8080` como allowlist inicial.
  - Bloquear puertos fuera de rango y puertos sensibles no permitidos.
  - Actualizar el mensaje de fallo TCP para usar "configured port" y devolver `target_port` en `details`.

## Funciones implementadas

Frontend Visual V1:

- Landing publica con logo, propuesta de valor y cards de infraestructura.
- Vista previa local del panel disponible solo en desarrollo mediante `import.meta.env.DEV`.
- Auth con registro y login usando:
  - `/_v4nex/auth/register`
  - `/_v4nex/auth/login`
- Dashboard basico autenticado:
  - estado de sesion
  - estado operacional simple
  - resumen de bridges
- Bridges:
  - `GET /_v4nex/bridges`
  - lista con `subdomain`, `public_url`, `target_ipv6`, `target_port`, `status` y `last_tcp_validation_result`.
  - empty state profesional.
- Crear bridge:
  - `POST /_v4nex/bridges`
  - `subdomain`
  - `target_ipv6`
- `target_port`
- selector limitado a puertos permitidos.

Preview local:

- Boton discreto `Vista previa del panel` visible solo cuando Vite corre en modo desarrollo.
- Crea una sesion visual marcada como preview, sin llamar al backend y sin guardar token real de produccion.
- Permite revisar las ventanas `Resumen`, `Bridges` y `Nuevo bridge` con estado local.
- Logout limpia la sesion preview.

Proxy local Vite:

- `/_v4nex/*` se proxya a `http://127.0.0.1:8000` solo en desarrollo.
- `/health` se proxya a `http://127.0.0.1:8000` solo en desarrollo.
- En produccion se mantienen rutas relativas detras de Caddy.

Backend:

- `validate_port(80)` acepta.
- `validate_port(8080)` acepta.
- `validate_port(22)`, `validate_port(0)` y `validate_port(65536)` rechazan.
- El error `INVALID_PORT` incluye:
  - `target_port`
  - `allowed_ports`
- Creacion de bridge con `target_port=8080` devuelve `201`.
- Creacion de bridge con `target_port=22` devuelve `INVALID_PORT`.

## Funciones no implementadas todavia

- Activar bridges desde la UI.
- Validar TCP desde la UI.
- Desactivar bridges desde la UI.
- Metricas avanzadas.
- Billing.
- OAuth.
- 2FA.
- Alertas operativas.
- Cambios de Caddy.
- Cambios DNS.
- Cloudflare API.
- Deploy.

## Allowlist de puertos

Puertos permitidos iniciales:

```text
80
8080
```

Variable opcional:

```env
ALLOWED_TARGET_PORTS=80,8080
```

Puertos bloqueados por no estar en allowlist:

```text
22
25
53
110
143
2019
3306
5432
6379
27017
```

No se habilitan rangos arbitrarios.

## Riesgos mitigados

- Se evita abrir puertos sensibles como SSH, Postgres, Caddy Admin API o bases de datos comunes.
- Se permite `8080` para servicios web/lab sin pasar a una politica permisiva.
- La validacion TCP sigue siendo requisito antes de activar un bridge.
- El frontend no hardcodea endpoints internos ni usa `localhost`/`backend:8000`.
- La UI no muestra capacidades no disponibles.

## Validaciones ejecutadas

Backend:

```bash
cd apps/backend
python -m pytest -p no:cacheprovider
```

Resultado:

```text
105 passed, 1 warning in 8.58s
```

Frontend:

```bash
cd apps/frontend
npm run build
```

Resultado:

```text
vite v5.4.21 building for production...
31 modules transformed
dist/index.html 0.41 kB
dist/assets/index-8_45pZl3.css 13.75 kB
dist/assets/index-DB6VICLy.js 155.96 kB
built in 1.80s
```

Verificaciones estaticas:

- No aparece `Frontend Skeleton` en frontend productivo.
- No aparece `Escenario 0` en frontend productivo.
- No aparece `localhost` en frontend productivo.
- No aparece `backend:8000` en frontend.
- No aparece `MVP` en UI final.
- El frontend usa rutas relativas bajo `/_v4nex`.

Docker frontend local:

```bash
docker build -f apps/frontend/Dockerfile.prod -t v4nex-frontend:scenario-24-frontend-panel apps/frontend
```

Estado:

```text
Build local exitoso.
Imagen: v4nex-frontend:scenario-24-frontend-panel
Manifest list: sha256:e3eab431e2303194a6fdcdfcc41da918e84131acf7dcd9f85ce4ee200d2dcd26
```

## Pendientes

- Construir imagen frontend local `v4nex-frontend:scenario-24-frontend-panel`.
- Revisar UI en navegador contra build final si se requiere aprobacion visual antes de publicar.
- Publicar nuevas imagenes backend/frontend solo con aprobacion explicita.
- Validar pull desde VPS solo despues de publicar imagenes.
- Coordinar con infra recreacion de backend/frontend, sin tocar Caddy.

## SYNC app -> infra - Ronda 13A

### Estado

- Frontend visual implementado localmente.
- Backend allowlist implementado localmente.
- Puertos permitidos: `80`, `8080`.
- Nueva variable documental: `ALLOWED_TARGET_PORTS=80,8080`.
- Nueva imagen GHCR: pendiente.
- Tag/digest GHCR: pendiente hasta aprobacion.

### Instrucciones para infra cuando app apruebe publicacion

Despues de que app confirme imagenes GHCR nuevas:

1. Actualizar backend image tag si backend cambia.
2. Actualizar frontend image tag.
3. Hacer `docker pull` de backend/frontend.
4. Recrear backend/frontend segun aplique.
5. No tocar Caddy.
6. No repetir ACME.
7. No modificar DNS.
8. No tocar `.env.production` salvo variables aprobadas.

Si se aprueba `ALLOWED_TARGET_PORTS`, agregar en `.env.production`:

```env
ALLOWED_TARGET_PORTS=80,8080
```

### Restricciones activas

- No hacer git push sin aprobacion.
- No publicar GHCR sin aprobacion.
- No hacer rsync.
- No tocar VPS.
- No ejecutar `docker compose up` en VPS.
- No repetir ACME.
- No llamar Cloudflare API.
- No modificar DNS.
- No tocar secretos reales.
