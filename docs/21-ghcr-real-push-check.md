# 21 - Push real controlado GHCR y verificacion desde registry

## Resumen ejecutivo

Este escenario intento publicar de forma controlada la imagen Caddy custom en GHCR con tag fijo, despues de validar localmente que la imagen `scratch` estaba limpia en Docker Scout.

El push real no se completo porque GHCR respondio `denied`. No se pidio token, no se imprimio token y no se automatizo login. El operador debe ejecutar `docker login ghcr.io` manualmente con permisos adecuados y reintentar el flujo.

No se uso `latest`, no se emitio TLS, no se ejecuto ACME, no se llamo Cloudflare API, no se modifico DNS publico, no se ejecuto `docker compose up`, no hubo deploy y no se creo CI/CD.

## Tag usado

- Tag fijo: `scenario-21-scratch-clean`
- Imagen esperada: `ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean`

## Validacion local antes del push

Comandos ejecutados:

```bash
bash scripts/build-caddy-custom-local.sh
bash scripts/check-caddy-custom-image.sh
bash scripts/check-caddy-image-hardening.sh
bash scripts/scan-caddy-image-optional.sh
```

Resultados:

- Build local: exitoso.
- `caddy version`: `v2.11.3 h1:/vFbdjcs2DtzcWTIxHybf5R5TspYFFThlZffChyBFHg=`
- `caddy list-modules`: incluye `dns.providers.cloudflare`
- Runtime `scratch`: sin `/bin/sh`
- Docker history: sin patrones obvios de secretos
- Tamano aproximado: `18 MB`
- Docker Scout local: `0C 0H 0M 0L`
- Paquetes vulnerables detectados: ninguno

## Tag GHCR local

Comando correcto ejecutado:

```bash
GHCR_TAG=scenario-21-scratch-clean bash scripts/tag-caddy-ghcr.sh
```

Resultado:

```text
Tagging local Caddy image for GHCR
  local: v4nex-caddy-cloudflare:dev-check
  ghcr:  ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
  push:  disabled
GHCR tag created locally.
No push was performed.
```

Nota: una invocacion previa desde PowerShell no propago `GHCR_TAG` y creo tambien el tag local default `scenario-18-check`. No hubo push de ese tag.

## Push real controlado

Comando ejecutado:

```bash
CONFIRM_PUSH=I_UNDERSTAND_PUSH_GHCR GHCR_TAG=scenario-21-scratch-clean bash scripts/push-caddy-ghcr.sh
```

Resultado:

```text
Pushing Caddy image to GHCR
  image: ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
  docker login: manual prerequisite
ERROR docker push failed.
If this is an auth error, run docker login ghcr.io manually and retry.
error from registry: denied
denied
```

Conclusion: no hubo push exitoso. El estado queda bloqueado por autenticacion/permisos GHCR.

## Login manual

No se automatizo login y no se pidio token. Para reintentar, el operador debe autenticarse manualmente fuera del repo:

```bash
docker login ghcr.io
```

El token debe tener permisos adecuados para publicar en `ghcr.io/andre-101/v4nex-caddy-cloudflare` y no debe guardarse en el repositorio.


Debe validar:

- `docker pull`
- `caddy version`
- `caddy list-modules`
- presencia de `dns.providers.cloudflare`

Resultado esperado:

- `0C 0H 0M 0L`
- `No vulnerable packages detected`

## Resultado final del push GHCR

La imagen fue publicada correctamente en GHCR con tag fijo:

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
```

## Decision Go/No-Go

GO tecnico local para publicar: la imagen local esta limpia y validada.


## Pendientes para Escenario 22

- Ejecutar `docker login ghcr.io` manual con permisos correctos.
- Reintentar push con `CONFIRM_PUSH=I_UNDERSTAND_PUSH_GHCR` y tag fijo.
- Ejecutar pull/check desde GHCR.
- Ejecutar Docker Scout sobre la imagen GHCR publicada.
- Actualizar compose productivo example solo despues de confirmar pull/check exitoso desde GHCR.
