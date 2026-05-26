# 18 - Publicacion controlada de Caddy custom en GHCR

## Resumen ejecutivo

Este escenario prepara el flujo manual para taggear, publicar y validar la imagen Caddy custom en GHCR con un tag fijo. No se usa `latest`, no se agrega CI/CD, no se emite TLS, no se llama Cloudflare y no se despliega.

## Que se valida

- La imagen local del Escenario 17 existe.
- La imagen local se puede taggear como GHCR.
- El push requiere confirmacion explicita.
- La imagen publicada puede descargarse y contiene:
  - `dns.providers.cloudflare`

## Fuera de alcance

- GitHub Actions.
- CI/CD.
- Tags `latest` o flotantes.
- TLS real.
- ACME real.
- Cloudflare API real.
- DNS publico.
- Deploy.
- `docker compose up`.
- Secrets reales en repo.

## Imagen GHCR

Imagen esperada:

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare:<tag-fijo>
```

Ejemplo documental:

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-18-check
```

## Por que no latest

`latest` no permite reproducir una demo ni saber que binario exacto se ejecuto. Los scripts fallan si el tag es `latest`, `change-me`, `dev`, `test`, vacio o contiene espacios.

## Prerequisitos

- Docker disponible.
- Imagen local construida desde Escenario 17.
- Login manual a GHCR si se va a publicar:

```bash
docker login ghcr.io
```

El login es manual. Los scripts no piden token y no imprimen tokens.

## Flujo manual

1. Build local.
2. Check local.
3. Tag GHCR.
4. Push GHCR con confirmacion explicita.
5. Pull/check desde GHCR.

## Comandos exactos

```bash
bash scripts/build-caddy-custom-local.sh
bash scripts/check-caddy-custom-image.sh
GHCR_TAG=scenario-18-check bash scripts/tag-caddy-ghcr.sh
CONFIRM_PUSH=I_UNDERSTAND_PUSH_GHCR GHCR_TAG=scenario-18-check bash scripts/push-caddy-ghcr.sh
GHCR_TAG=scenario-18-check bash scripts/check-caddy-ghcr-image.sh
```

Si no se desea publicar todavia, ejecutar solo:

```bash
bash -n scripts/tag-caddy-ghcr.sh
bash -n scripts/push-caddy-ghcr.sh
bash -n scripts/check-caddy-ghcr-image.sh
GHCR_TAG=scenario-18-check bash scripts/tag-caddy-ghcr.sh
```

## Push manual y controlado

`scripts/push-caddy-ghcr.sh` exige:

```bash
CONFIRM_PUSH=I_UNDERSTAND_PUSH_GHCR
```

Si `docker push` falla por autenticacion, ejecutar `docker login ghcr.io` manualmente y reintentar.

## Riesgos

| Riesgo | Mitigacion |
| --- | --- |
| Publicar `latest` | Scripts bloquean tags flotantes |
| Publicar imagen equivocada | Tag local explicito y check de modulo |
| GHCR privado/no accesible desde VPS | Validar pull desde entorno autorizado en escenario posterior |
| Token GitHub filtrado | Login manual, sin token en scripts ni docs |

## Pendientes para Escenario 19

Ver `docs/19-caddy-ghcr-hardening-publish.md` para el hardening previo al push real.

- Decidir si se ejecuta push real.
- Validar pull desde GHCR con tag fijo.
- Validar disponibilidad de GHCR desde la VPS sin deploy.
- Mantener TLS/ACME/deploy fuera hasta aprobacion explicita.
