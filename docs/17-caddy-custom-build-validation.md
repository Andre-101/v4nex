# 17 - Build local y validacion de Caddy custom

## Resumen ejecutivo

Este escenario valida localmente que la imagen Caddy custom puede construirse con el modulo DNS de Cloudflare. No se hace push a GHCR, no se ejecuta ACME, no se emiten certificados y no se levanta ningun servicio.

## Que se valida

- `infra/caddy/Dockerfile.prod.example` construye una imagen local.
- La imagen resultante ejecuta `caddy version`.
- La imagen incluye el modulo:
  - `dns.providers.cloudflare`

## Fuera de alcance

- Push a GHCR.
- Uso de `latest`.
- CI/CD.
- TLS real.
- ACME real.
- Cloudflare API real.
- DNS publico.
- Deploy.
- `docker compose up`.
- Secrets reales.

## Comandos

Build local:

```bash
bash scripts/build-caddy-custom-local.sh
```

Verificacion local:

```bash
bash scripts/check-caddy-custom-image.sh
```

## Tag local fijo

Por defecto:

```text
v4nex-caddy-cloudflare:dev-check
```

Para usar un tag local distinto:

```bash
CADDY_LOCAL_TAG="v4nex-caddy-cloudflare:scenario-17" \
bash scripts/build-caddy-custom-local.sh

CADDY_LOCAL_TAG="v4nex-caddy-cloudflare:scenario-17" \
bash scripts/check-caddy-custom-image.sh
```

## Por que no usar latest

`latest` no es reproducible y no sirve para una demo final trazable. Los scripts fallan si `CADDY_LOCAL_TAG` usa `latest`.

## Salida esperada

El build debe terminar con:

```text
Local Caddy custom image built successfully.
No push was performed.
```

El check debe encontrar:

```text
OK required module found: dns.providers.cloudflare
Local Caddy custom image validation passed.
```

## Interpretacion de dns.providers.cloudflare

Si `caddy list-modules` contiene `dns.providers.cloudflare`, la imagen incluye el plugin necesario para configurar DNS-01 con Cloudflare en un escenario posterior.

Esto no valida credenciales, no contacta Cloudflare y no emite certificados.

## Riesgos pendientes

- Falta publicar una imagen GHCR con tag fijo.
- Falta validar pull desde la VPS.
- Falta activar TLS wildcard real en una ventana controlada.
- Falta secret management real para token Cloudflare.
- Falta rollback productivo probado.

## Siguiente paso hacia GHCR

El siguiente escenario puede preparar build/tag/push controlado hacia GHCR con un tag fijo, pero todavia sin usar `latest`, sin deploy y sin emitir TLS.
