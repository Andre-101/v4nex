# Condiciones para autorizar deploy real — v4nex v0.1.0

## Propósito

Definir las condiciones mínimas para considerar un deploy real de v4nex v0.1.0 en la VPS productiva.

Este documento existe para evitar despliegues innecesarios o riesgosos cuando el runtime ya se encuentra alineado con los tags y digests esperados.

## Principio rector

Un deploy real solo debe ejecutarse si aporta más valor que riesgo.

No se debe ejecutar un deploy real únicamente para probar el script de despliegue cuando el flujo ya fue validado en dry-run y el runtime actual está funcionando correctamente.

## Estado actual

La línea base aceptada al cierre de Fase 2 es:

- Release: `v0.1.0`.
- Manifest: `releases/v0.1.0.json`.
- Platform mode: `closed_temporarily`.
- Backend healthy.
- Frontend healthy.
- Caddy healthy.
- DB healthy.
- Redes Docker IPv6 activas.
- Puertos públicos: 80/443 vía Caddy.
- Puertos internos no publicados al host.
- `v4nex.com/`: 403 esperado.
- `v4nex.com/health`: 200 OK.
- `v4nex.com/_v4nex/health`: 200 OK.

## Condiciones obligatorias

Un deploy real futuro solo puede considerarse si se cumplen todas las siguientes condiciones:

1. Existe un cambio funcional, corrección crítica o nueva imagen que justifique recrear servicios.
2. Existe un release manifest actualizado y aprobado por App e Infra.
3. Los tags no usan `latest`.
4. Los digests de imágenes están declarados.
5. Los digests fueron validados contra GHCR.
6. `scripts/prod/v4nex-preflight.sh` termina en GO.
7. `scripts/prod/v4nex-smoke.sh minimal` termina en GO.
8. `V4NEX_DRY_RUN=1 scripts/prod/v4nex-deploy.sh` termina en GO.
9. `V4NEX_DRY_RUN=1 scripts/prod/v4nex-rollback.sh` termina en GO.
10. Existe ventana operativa definida.
11. Existe criterio de rollback real preparado.
12. Existe aprobación explícita de App e Infra.
13. Se confirma que el deploy real aporta más valor que riesgo.

## Condiciones de bloqueo

No debe ejecutarse deploy real si ocurre cualquiera de estas condiciones:

- El runtime ya opera con los tags y digests esperados y no existe cambio funcional pendiente.
- El release manifest no fue actualizado o aprobado.
- Falta digest de alguna imagen requerida.
- Algún servicio está unhealthy.
- Alguna red IPv6 productiva no está activa.
- Falta algún volumen crítico.
- Algún puerto interno aparece publicado al host.
- `v4nex.com/health` falla.
- `v4nex.com/_v4nex/health` falla.
- No existe ventana operativa.
- No existe criterio de rollback preparado.
- No existe aprobación explícita App + Infra.

## Alcance permitido de un deploy real aprobado

Un deploy real aprobado debe limitarse al alcance declarado en el release manifest.

Para la línea base v0.1.0, la política declarada es:

- `recreate`: backend.
- `validate_only`: caddy, frontend.
- `do_not_recreate`: db.
- `requires_manual_approval`: caddy, db.

Cualquier cambio fuera de esa política requiere actualización del manifest y nueva aprobación.

## Acciones prohibidas durante deploy real

Incluso con autorización de deploy real, siguen prohibidas salvo autorización separada:

- `docker compose down -v`.
- Borrado de volúmenes.
- Modificación manual de DNS.
- Repetición manual de ACME.
- Publicación de puertos internos.
- Recreación de DB sin plan de recuperación.
- Modificación no controlada de `infra/caddy/Caddyfile.prod`.
- Modificación no controlada de `.env.production`.
- Smoke extended sin autorización explícita.
- Creación, validación o activación de bridges fuera del alcance aprobado.

## Criterios mínimos de éxito

Un deploy real aprobado solo puede considerarse exitoso si:

- El script de deploy termina en GO.
- Los servicios quedan healthy.
- `v4nex.com/health` responde 200.
- `v4nex.com/_v4nex/health` responde 200.
- La plataforma mantiene el comportamiento esperado según `platform_mode`.
- No se publican puertos internos.
- No se modifica ningún recurso protegido fuera del alcance autorizado.
- El smoke minimal posterior termina en GO.
- La auditoría posterior termina en GO.

## Criterios de rollback real

Debe ejecutarse rollback real si:

- Backend no levanta.
- Backend queda unhealthy.
- `/health` falla.
- `/_v4nex/health` falla.
- Caddy queda unhealthy.
- DB queda unhealthy.
- Aparece publicación accidental de puertos internos.
- Se detecta comportamiento de plataforma incompatible con el manifest aprobado.

El rollback real debe usar el alcance declarado en el manifest y debe validarse posteriormente con preflight, smoke minimal y audit-state.

## Decisión para Fase 2

Para el cierre de Fase 2 no se autoriza deploy real.

Justificación:

1. El runtime actual ya funciona.
2. Los tags y digests esperados ya están en operación.
3. El flujo de deploy fue validado en dry-run.
4. El flujo de rollback fue validado en dry-run.
5. Ejecutar deploy real solo para probar el script agregaría riesgo sin beneficio técnico inmediato.

## Pendientes antes de una operación pública continua

- Definir política de abuso y rate limiting.
- Definir condiciones para reabrir el panel principal.
- Definir monitoreo y alertas.
- Definir backup formal de base de datos.
- Definir retención automatizada segura.
- Definir procedimiento de soporte y respuesta ante incidentes.
- Definir criterio para smoke extended con target controlado.
