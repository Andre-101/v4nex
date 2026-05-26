# 22 - Validacion pull GHCR desde VPS sin levantar servicios

## Resumen ejecutivo

Este escenario valida que la VPS puede descargar y ejecutar comandos de inspeccion basicos sobre la imagen Caddy custom publicada en GHCR, sin levantar servicios y sin avanzar a deploy.

La validacion confirma:

- `docker pull` desde GHCR exitoso.
- Digest obtenido coincide con el digest esperado.
- Caddy mantiene version `v2.11.3`.
- El modulo `dns.providers.cloudflare` esta presente.
- El runtime final sigue siendo minimo: `/bin/sh` no existe.

No se ejecuto `docker compose up`, no se emitio TLS, no se ejecuto ACME, no se llamo Cloudflare API, no se modifico DNS publico y no hubo deploy.

## Imagen validada

Imagen:

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
```

Digest esperado:

```text
sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6
```

Digest obtenido en VPS:

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare@sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6
```

Resultado: el digest obtenido coincide con el digest esperado.

## Entorno VPS

Entorno reportado:

- Docker version: `29.5.2`
- Proveedor/SO: documentados en inventario privado y documentos previos de readiness.
- IP publica, IPv6 publica y puerto SSH: no se registran en este documento.

No se incluyen tokens, secrets, IP publica real, IPv6 real ni puerto SSH real.

## Comandos ejecutados en VPS

Los comandos se ejecutaron manualmente en la VPS para validar pull e inspeccion de imagen, sin levantar servicios:

```bash
docker pull ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
docker image inspect ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
docker run --rm ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean caddy version
docker run --rm ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean caddy list-modules
docker run --rm --entrypoint /bin/sh ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
```

## Resultado de docker pull

Resultado: exitoso.

La VPS pudo descargar:

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
```

## Resultado de docker image inspect

El digest inspeccionado fue:

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare@sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6
```

Resultado: coincide con el digest esperado.

## Resultado de caddy version

```text
v2.11.3 h1:/vFbdjcs2DtzcWTIxHybf5R5TspYFFThlZffChyBFHg=
```

## Resultado de caddy list-modules

`caddy list-modules` confirmo:

```text
dns.providers.cloudflare
```

Resultado: el modulo Cloudflare DNS esta presente.

## Runtime scratch

La comprobacion de `/bin/sh` confirmo:

```text
OK: /bin/sh is not available
```

Resultado: la imagen conserva runtime minimo tipo `scratch` y no incluye shell.

## Docker Scout en VPS

Docker Scout en VPS no se documenta como obligatorio en este escenario. La imagen ya fue validada previamente con Docker Scout sobre GHCR con resultado `0C 0H 0M 0L`.

## Confirmacion de alcance

No se ejecuto:

- `docker compose up`
- deploy
- TLS real
- ACME real
- Cloudflare API real
- cambios de DNS publico
- CI/CD

No se registraron secrets, tokens, IP publica real, IPv6 real ni puerto SSH real.

## Decision Go/No-Go

**GO tecnico** para preparar el siguiente escenario de compose/preflight productivo, sin levantar servicios todavia.

Esta decision no autoriza deploy, TLS, ACME, Cloudflare API, DNS publico ni `docker compose up`.

## Pendientes para Escenario 23

- Preparar validacion de compose/preflight productivo usando la imagen publicada.
- Verificar que el tag fijo se use sin `latest`.
- Validar render/configuracion sin levantar servicios.
- Mantener Caddy Admin API privado en red Docker.
- No ejecutar `docker compose up`.
- No hacer deploy.
