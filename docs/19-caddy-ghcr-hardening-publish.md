# 19 - Hardening de imagen Caddy y push GHCR controlado

## Resumen ejecutivo

Este escenario endurece la imagen Caddy custom antes de cualquier push real a GHCR. Se fija la version base de Caddy, se agregan labels OCI, se valida `docker history`, se confirma el modulo Cloudflare y se deja un flujo Go/No-Go para publicar con tag fijo.

No se ejecuta push real salvo confirmacion explicita del operador. No se emite TLS, no se llama Cloudflare, no se despliega y no se crea CI/CD.

## Que se valida

- Imagen local existe.
- No usa `latest`.
- Dockerfile usa base Caddy versionada.
- Labels OCI basicas existen en el Dockerfile.
- `docker history --no-trunc` no contiene patrones obvios de secretos.
- `caddy version` funciona.
- `caddy list-modules` contiene `dns.providers.cloudflare`.
- Tamano aproximado de imagen queda visible.
- Scan opcional se ejecuta si existe Trivy o Docker Scout.

## Fuera de alcance

- Push automatico.
- GitHub Actions.
- CI/CD.
- TLS real.
- ACME real.
- Cloudflare API real.
- DNS publico.
- Deploy.
- `docker compose up`.
- Secrets reales.

## Decision de seguridad antes de push

Antes de hacer push real:

1. `bash scripts/build-caddy-custom-local.sh`
2. `bash scripts/check-caddy-custom-image.sh`
3. `bash scripts/check-caddy-image-hardening.sh`
4. `bash scripts/scan-caddy-image-optional.sh`
5. Revisar salida.
6. Taggear GHCR con tag fijo.
7. Push solo con `CONFIRM_PUSH=I_UNDERSTAND_PUSH_GHCR`.

## Version base Caddy

El Dockerfile productivo example usa:

- `caddy:2.11.3-builder`
- `caddy:2.11.3`

Se eligio esta version porque el build local previo reporto Caddy `v2.11.3`. Si una tag deja de estar disponible, se debe documentar el nuevo criterio de pinning antes de cambiarla.

## Labels OCI

Labels agregadas:

- `org.opencontainers.image.title`
- `org.opencontainers.image.description`
- `org.opencontainers.image.source`
- `org.opencontainers.image.vendor`
- `org.opencontainers.image.licenses`

## Validaciones de docker history

El hardening check bloquea patrones obvios:

- `CLOUDFLARE_API_TOKEN`
- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- `change-me`
- `BEGIN PRIVATE KEY`
- `ghp_`
- `AKIA`

Esto no reemplaza un scanner de secretos formal, pero reduce errores evidentes antes del push.

## Validacion de modulo Cloudflare

El criterio funcional minimo es:

```text
dns.providers.cloudflare
```

Debe aparecer en `caddy list-modules`.

## Scan opcional

`scripts/scan-caddy-image-optional.sh`:

- usa Trivy si esta instalado
- usa Docker Scout si esta disponible
- no instala herramientas
- no falla si no hay scanner

## Flujo recomendado

```bash
bash scripts/build-caddy-custom-local.sh
bash scripts/check-caddy-custom-image.sh
bash scripts/check-caddy-image-hardening.sh
bash scripts/scan-caddy-image-optional.sh
GHCR_TAG=scenario-19-hardening bash scripts/tag-caddy-ghcr.sh
CONFIRM_PUSH=I_UNDERSTAND_PUSH_GHCR GHCR_TAG=scenario-19-hardening bash scripts/push-caddy-ghcr.sh
GHCR_TAG=scenario-19-hardening bash scripts/check-caddy-ghcr-image.sh
```

## Criterios Go/No-Go para push

Go:

- build local pasa
- check local pasa
- hardening check pasa
- tag GHCR fijo, no `latest`
- operador hizo `docker login ghcr.io` manualmente
- operador acepta `CONFIRM_PUSH=I_UNDERSTAND_PUSH_GHCR`

No-Go:

- aparece un patron secreto en history
- falta `dns.providers.cloudflare`
- tag es flotante
- no hay confirmacion explicita
- hay dudas sobre la imagen a publicar

## Riesgos pendientes

- Scanner opcional puede no estar disponible.
- GHCR puede quedar privado y no accesible desde VPS.
- Falta validar pull desde VPS.
- Falta flujo de rollback de imagen publicada.

## Pendientes para Escenario 20

Ver `docs/20-caddy-vulnerability-remediation.md` para el analisis y remediacion de CVEs antes de cualquier push final.

- Decidir si se ejecuta push real.
- Validar pull desde GHCR con tag fijo.
- Verificar acceso GHCR desde VPS sin deploy.
- Mantener TLS/ACME/deploy fuera hasta aprobacion explicita.

## Resultado de scan opcional

Durante la validación local, Docker Scout reportó:

```text
7C 6H 17M 0L 7?
```

## Resultado de Docker Scout

Docker Scout detectó vulnerabilidades en la imagen local `v4nex-caddy-cloudflare:dev-check`:

```text
37 vulnerabilities found in 6 packages
CRITICAL     7
HIGH         6
MEDIUM       17
LOW          0
UNSPECIFIED  7
```
