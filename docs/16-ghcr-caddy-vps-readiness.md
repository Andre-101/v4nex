# 16 - GHCR Caddy custom y readiness VPS

## Resumen ejecutivo

Este escenario alinea los artefactos productivos de ejemplo con la linea base real de infraestructura: dominio `v4nex.com`, DNS Cloudflare en modo DNS only, VPS Hetzner, Caddy custom con modulo Cloudflare y preflight local sin levantar servicios.

No se hace deploy, no se ejecuta `docker compose up`, no se emiten certificados, no se llama la API de Cloudflare y no se crean secrets reales.

## Linea base real

- Dominio: `v4nex.com`
- DNS: Cloudflare, zona active
- Modo Cloudflare: DNS only
- Wildcard DNS configurado conceptualmente:
  - `v4nex.com` -> IPv4 de VPS definida en inventario privado de despliegue
  - `*.v4nex.com` -> IPv4 de VPS definida en inventario privado de despliegue
- IPv4 VPS: definida en inventario privado de despliegue
- IPv6 VPS: definida en inventario privado de despliegue
- Proveedor VPS: Hetzner Cloud
- SO: Ubuntu 24.04.4 LTS
- SSH administrativo: puerto definido en inventario privado, usuario `deploy`
- Ruta base servidor: `/opt/v4nex/app`
- Directorios esperados:
  - `/opt/v4nex/app`
  - `/opt/v4nex/backups`
  - `/opt/v4nex/logs`
  - `/opt/v4nex/runtime`
  - `/opt/v4nex/scripts`

## Que se implemento

- `infra/caddy/Dockerfile.prod.example` para construir Caddy con:
  - `github.com/caddy-dns/cloudflare`
- `docker-compose.prod.example.yml` alineado a imagen GHCR:
  - `ghcr.io/andre-101/v4nex-caddy-cloudflare:${IMAGE_TAG}`
- `.env.production.example` alineado a variables reales.
- `infra/caddy/Caddyfile.prod.example` alineado a plataforma en `{$DOMAIN}`.
- Scripts productivos alineados:
  - `scripts/check-prod-env.sh`
  - `scripts/check-caddy-prod-config.sh`
- `scripts/prod-preflight.sh`
- `scripts/vps-readiness-static.sh`

Ejemplo local del inventario VPS sin valores reales:

```bash
EXPECTED_IPV4="x.x.x.x" \
EXPECTED_IPV6="xxxx:xxxx::x" \
EXPECTED_SSH_PORT="change-me" \
bash scripts/vps-readiness-static.sh
```

Los valores reales deben vivir fuera del repo, por ejemplo en inventario privado de despliegue o gestor de secretos.

## Fuera de alcance

- Deploy real.
- `docker compose up -d`.
- `docker compose up -d --build`.
- TLS real emitido.
- ACME real ejecutado.
- Cloudflare API real.
- DNS publico modificado.
- CI/CD.
- Secrets reales.
- Comandos remotos por SSH.
- Billing.
- Redis, Celery o Kubernetes.

## Variables finales .env.production

Interfaz principal requerida:

```env
APP_ENV=production
DOMAIN=v4nex.com
CADDY_DOMAIN=v4nex.com
IMAGE_TAG=change-me
POSTGRES_DB=v4nex
POSTGRES_USER=v4nex
POSTGRES_PASSWORD=change-me
JWT_SECRET=change-me
CLOUDFLARE_API_TOKEN=change-me
CADDY_ACME_EMAIL=admin@example.com
BACKEND_PORT=8000
```

No crear `.env.production` en el repo. El archivo real debe vivir en la VPS con permisos restringidos.

## Mapeo a variables internas

El backend aun espera algunos nombres internos. El compose example mapea:

- `DOMAIN` -> `PUBLIC_DOMAIN`
- `JWT_SECRET` -> `JWT_SECRET_KEY`
- `CADDY_ADMIN_URL` queda fijo como `http://caddy:2019`
- `DATABASE_URL` se deriva de `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB`

No se toca backend en este escenario.

## GHCR image pendiente

Imagen esperada:

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare:${IMAGE_TAG}
```

Reglas:

- No usar `latest`.
- Usar tag inmutable para demo final.
- Construir desde `infra/caddy/Dockerfile.prod.example` o su version definitiva.
- Publicar en GHCR solo cuando exista proceso aprobado.

## Dockerfile Caddy custom example

`infra/caddy/Dockerfile.prod.example` usa `xcaddy` e incluye:

```text
github.com/caddy-dns/cloudflare
```

No contiene tokens ni secrets.

## Validacion pull GHCR futura

No ejecutar en este escenario. Futuro:

```bash
docker pull ghcr.io/andre-101/v4nex-caddy-cloudflare:<tag>
```

Debe hacerse con un tag fijo, no `latest`.

## Validacion Caddy custom futura

No ejecutar contra infraestructura real todavia. Futuro:

```bash
docker run --rm ghcr.io/andre-101/v4nex-caddy-cloudflare:<tag> caddy list-modules
```

Debe confirmar que el modulo Cloudflare DNS esta presente.

## Validacion TLS wildcard futura

No emitir certificados en este escenario. Futuro:

1. Cargar `.env.production` real fuera del repo.
2. Confirmar token Cloudflare con permisos minimos.
3. Activar bloque DNS-01 real en Caddyfile definitivo.
4. Ejecutar preflight estricto.
5. Levantar en ventana controlada.
6. Verificar certificado wildcard.

## Caddy Admin API privada

El compose example:

- publica solo `80:80` y `443:443`
- no publica `2019`
- no publica `5432`
- no publica `8000`
- no publica `5173`

Caddy Admin API debe quedar solo dentro de la red Docker. Exponerla publicamente es critico.

## Validacion curl al IPv6 real del cliente

No se ejecuta en este escenario. Futuro, para un target IPv6 de cliente:

```bash
curl -g -6 http://[IPv6_DEL_CLIENTE]:80/
```

El backend ya valida TCP, pero una prueba manual ayuda a diagnosticar firewall/rutas IPv6.

## Runbook futuro sin ejecutar

1. Crear tag GHCR fijo para Caddy custom.
2. Cargar `.env.production` real en `/opt/v4nex/app`.
3. Ejecutar `check-prod-env.sh` en modo estricto.
4. Ejecutar `check-caddy-prod-config.sh` en modo estricto.
5. Ejecutar `prod-preflight.sh` en modo estricto.
6. Verificar firewall VPS.
7. Verificar que `2019`, `5432`, `8000` y `5173` no esten publicos.
8. Ejecutar migraciones.
9. Ejecutar bootstrap admin.
10. Solo despues, planificar ventana controlada para levantar servicios.

## Riesgos

| Riesgo | Impacto | Mitigacion |
| --- | --- | --- |
| Sin Caddy custom no hay wildcard TLS DNS-01 | Alto | Construir y validar imagen GHCR con plugin Cloudflare |
| Caddy Admin API expuesta | Critico | No publicar 2019, firewall, preflight estatico |
| Token Cloudflare filtrado | Critico | Secret fuera del repo, permisos minimos, rotacion |
| Usar latest | Alto | `IMAGE_TAG` obligatorio y no latest |
| DNS only mal validado | Medio | Smoke controlado despues, sin cambiar DNS desde scripts |

## Decision final

No deploy todavia. No TLS real todavia. No llamada a Cloudflare todavia.

El siguiente paso debe preparar y validar la imagen GHCR de Caddy custom con tag fijo, sin levantar servicios productivos.
