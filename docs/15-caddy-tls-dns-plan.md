# 15 - Caddy productivo draft y plan TLS/DNS

## Resumen ejecutivo

Este escenario agrega un `Caddyfile` productivo de ejemplo y validaciones estáticas para preparar TLS/DNS reales sin emitir certificados, sin llamar APIs DNS y sin desplegar.

El objetivo es dejar un plan ejecutable y revisable para una VPS futura. No se activa TLS real, no se usa Cloudflare API y no se abre tráfico público.

## Qué se creó

- `infra/caddy/Caddyfile.prod.example`
- `scripts/check-caddy-prod-config.sh`
- Actualización de `docker-compose.prod.example.yml` para montar el Caddyfile productivo example.
- Actualización de `.env.production.example` con `TLS_MODE=dns-01-wildcard`.
- Actualización de `scripts/prod-preflight.sh` para llamar la validación Caddy.

## Fuera de alcance

- TLS real emitido.
- ACME real ejecutado.
- Cloudflare API real.
- DNS público real.
- Deploy.
- CI/CD.
- Secrets reales.
- VPS real.
- Billing.
- Redis, Celery o Kubernetes.

## Caddy dev vs Caddy prod example

| Aspecto | Caddy dev | Caddy prod example |
| --- | --- | --- |
| Archivo | `infra/caddy/Caddyfile` | `infra/caddy/Caddyfile.prod.example` |
| Puertos | `:8080` | hosts reales en `80/443` vía compose |
| TLS | desactivado | preparado para TLS público futuro |
| Admin API | Docker dev | red interna Docker, nunca host público |
| Plataforma | frontend/backend local | `PUBLIC_DOMAIN`, `panel.PUBLIC_DOMAIN`, `api.PUBLIC_DOMAIN` |
| Bridges dinámicos | Admin API dev | Admin API interna futura |

## Arquitectura Caddy productiva propuesta

```text
Internet
-> DNS A / wildcard A
-> VPS IPv4 pública
-> Caddy :80/:443
-> frontend:5173 para plataforma
-> backend:8000 para /_v4nex y api.PUBLIC_DOMAIN
-> rutas bridge dinámicas por Host header
```

El `Caddyfile.prod.example` define la plataforma y API base. Las rutas dinámicas de bridges siguen perteneciendo al backend mediante Caddy Admin API.

## Estrategia TLS recomendada

Recomendación: DNS-01 wildcard para `*.v4nex.com`.

Motivos:

- Evita emitir o renovar certificados por cada subdominio dinámico.
- Funciona mejor con muchos bridges.
- Permite cubrir subdominios creados después sin challenge HTTP por host.

HTTP-01 puede ser útil para pocos hosts estáticos, pero se complica con muchos subdominios dinámicos porque cada hostname necesita validación alcanzable por HTTP.

Cloudflare Origin Cert tiene sentido si Cloudflare proxy está siempre delante del edge. Es menos portable porque el certificado sirve para el tramo Cloudflare -> origin, no como TLS público general fuera de Cloudflare.

## Imagen Caddy con plugin DNS

Caddy OSS base no incluye todos los plugins DNS. Para DNS-01 con Cloudflare normalmente se necesita una imagen custom de Caddy con plugin DNS Cloudflare.

Este escenario no crea esa imagen. El ejemplo deja el bloque DNS-01 como comentario operativo para evitar depender de plugins que no están instalados.

## Variables TLS/DNS requeridas

- `PUBLIC_DOMAIN`
- `ACME_EMAIL`
- `DNS_PROVIDER`
- `DNS_PROVIDER_API_TOKEN`
- `TLS_MODE`
- `CADDY_ADMIN_URL`

Reglas:

- No guardar tokens DNS en repo.
- No imprimir tokens en scripts.
- Usar permisos mínimos del token DNS.
- Rotar tokens.
- Mantener `CADDY_ADMIN_URL=http://caddy:2019` o equivalente interno.

## Exposición de puertos

| Puerto | Exposición | Uso |
| --- | --- | --- |
| 80 | Público | HTTP / ACME futuro / redirects |
| 443 | Público | HTTPS futuro |
| 2019 | Interno Docker | Caddy Admin API |
| 8000 | Interno Docker | Backend |
| 5173 | Interno Docker | Frontend actual |
| 5432 | Interno Docker | PostgreSQL |

Nunca publicar `2019` al host ni a internet.

## Seguridad de Caddy Admin API

La Admin API debe quedar solo en la red interna Docker. El compose example usa `expose: 2019`, no `ports`.

Antes de producción real:

- Validar firewall.
- Confirmar que `:2019` no responde desde internet.
- Mantener el backend como único actor que aplica rutas dinámicas.
- Auditar llamadas admin.

## Cómo correr check-caddy-prod-config.sh

Validar el example:

```bash
bash scripts/check-caddy-prod-config.sh .env.production.example --allow-placeholders
```

Modo estricto futuro:

```bash
bash scripts/check-caddy-prod-config.sh /ruta/segura/.env.production
```

El script valida variables sin imprimir secretos. Si Docker está disponible, ejecuta:

```bash
caddy validate
```

Esto no ejecuta ACME, no emite certificados y no llama Cloudflare.

## Cómo corre prod-preflight.sh

```bash
bash scripts/prod-preflight.sh .env.production.example --allow-placeholders
```

El preflight ejecuta:

1. `check-prod-env.sh`
2. `check-caddy-prod-config.sh`
3. verificación de Docker
4. verificación de Docker Compose
5. `docker compose config`

No levanta servicios.

## Runbook futuro para activar TLS real

No ejecutar en este escenario:

1. Configurar dominio real.
2. Configurar DNS A y wildcard A hacia la VPS.
3. Crear token DNS con permisos mínimos.
4. Guardar token fuera del repo.
5. Construir imagen Caddy con plugin DNS necesario.
6. Activar bloque DNS-01 real en Caddyfile productivo definitivo.
7. Ejecutar preflight estricto.
8. Levantar servicios en ventana controlada.
9. Verificar emisión de certificado.
10. Ejecutar smoke test.
11. Verificar que Caddy Admin API no esté expuesta.
12. Documentar rollback.

## Riesgos y pendientes

- Caddyfile productivo definitivo pendiente.
- Imagen Caddy custom con plugin DNS pendiente.
- DNS real pendiente.
- TLS wildcard real pendiente.
- Secret manager pendiente.
- Firewall real pendiente.
- Smoke VPS pendiente.
- Rollback real pendiente.

## Decisión final

No emitir certificados todavía y no hacer deploy.

El siguiente paso debe ser preparar la imagen Caddy con plugin DNS y un Caddyfile productivo definitivo, o continuar con validaciones de seguridad antes de tocar infraestructura pública.
