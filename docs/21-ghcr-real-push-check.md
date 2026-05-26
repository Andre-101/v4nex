# 21 - Push real controlado GHCR y verificacion desde registry

## Resumen ejecutivo

Este escenario publico de forma controlada la imagen Caddy custom en GHCR con tag fijo, despues de validar localmente que la imagen `scratch` estaba limpia en Docker Scout.

La secuencia real fue:

1. Validacion local OK.
2. Tag GHCR local OK.
3. Primer push fallo por `GHCR denied`.
4. Se hizo `docker login ghcr.io` manual correctamente.
5. Se reintento el push con confirmacion explicita.
6. Push exitoso.
7. Pull/check desde GHCR exitoso.
8. Docker Scout sobre GHCR limpio: `0C 0H 0M 0L`.

No se uso `latest`, no se emitio TLS, no se ejecuto ACME, no se llamo Cloudflare API, no se modifico DNS publico, no se ejecuto `docker compose up`, no hubo deploy y no se creo CI/CD.

## Tag e imagen publicada

- Tag fijo: `scenario-21-scratch-clean`
- Imagen publicada: `ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean`
- Digest: `sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6`

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

Comando ejecutado:

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

## Primer push fallido

Comando ejecutado:

```bash
CONFIRM_PUSH=I_UNDERSTAND_PUSH_GHCR GHCR_TAG=scenario-21-scratch-clean bash scripts/push-caddy-ghcr.sh
```

Resultado inicial:

```text
ERROR docker push failed.
If this is an auth error, run docker login ghcr.io manually and retry.
error from registry: denied
denied
```

No se pidio token, no se imprimio token y no se automatizo login.

## Login manual GHCR

El operador ejecuto manualmente:

```bash
docker login ghcr.io
```

El login fue exitoso fuera del flujo automatizado. No se guardaron secrets en el repositorio.

## Push exitoso

Despues del login manual, se reintento:

```bash
CONFIRM_PUSH=I_UNDERSTAND_PUSH_GHCR GHCR_TAG=scenario-21-scratch-clean bash scripts/push-caddy-ghcr.sh
```

Resultado final: push exitoso de la imagen:

```text
ghcr.io/andre-101/v4nex-caddy-cloudflare:scenario-21-scratch-clean
```

Digest publicado:

```text
sha256:5b5cad98d400e6f5ae44d45befbdf91dd00b53be429687a8e4ad086322498ed6
```

## Pull/check desde GHCR

Pull/check desde GHCR fue exitoso.

Validaciones confirmadas:

- `docker pull` exitoso.
- `caddy version`: `v2.11.3 h1:/vFbdjcs2DtzcWTIxHybf5R5TspYFFThlZffChyBFHg=`
- `caddy list-modules`: incluye `dns.providers.cloudflare`
- No se llamo Cloudflare API.
- No se emitio TLS.
- No se levantaron servicios.

## Docker Scout sobre GHCR

Docker Scout sobre la imagen publicada reporto:

```text
0C 0H 0M 0L
No vulnerable packages detected
Size: 18 MB
Packages: 195
```

## Decision Go/No-Go

**GO tecnico** para usar esta imagen en el siguiente escenario de validacion pull desde VPS, sin levantar servicios.

Esta decision no autoriza deploy, TLS, ACME, Cloudflare API, DNS publico ni `docker compose up`.

## Pendientes para Escenario 22

Ver `docs/22-vps-ghcr-pull-check.md` para la validacion de pull desde VPS.

- Validar `docker pull` desde VPS.
- Validar `caddy version` desde VPS.
- Validar `caddy list-modules` desde VPS.
- Confirmar `dns.providers.cloudflare` desde VPS.
- Ejecutar Docker Scout desde VPS si esta disponible.
- No ejecutar `docker compose up`.
- No hacer deploy.
