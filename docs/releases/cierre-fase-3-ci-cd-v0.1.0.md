# Cierre de Fase 3 — CI/CD productivo controlado v0.1.0

## 1. Resumen ejecutivo

La Fase 3 de v4nex v0.1.0 cierra como validación inicial del canal de CI/CD productivo controlado desde GitHub Actions hacia la VPS de producción.

El objetivo fue reducir operación manual sin habilitar despliegues automáticos ni perder control sobre producción. La fase validó workflows manuales, GitHub Environment `production`, aprobaciones, llave SSH dedicada, ejecución remota controlada y flujos no destructivos de auditoría, preflight, smoke minimal, deploy dry-run y rollback dry-run.

Este cierre no declara producción final abierta, no autoriza deploy real, no autoriza rollback real y no autoriza smoke extended.

## 2. Alcance validado

Se validó el canal GitHub Actions → VPS únicamente en modo controlado y no destructivo.

Alcance cubierto:

* Workflows manuales con `workflow_dispatch`.
* Uso de GitHub Environment `production`.
* Deployment protection rules y aprobación previa a ejecución.
* Llave SSH dedicada para GitHub Actions.
* Conexión remota como usuario `deploy`.
* Ejecución remota de scripts productivos ya versionados.
* Separación entre dry-run y ejecución real.
* Mejora de gobernanza moviendo valores no sensibles a Environment variables.

Alcance excluido:

* Deploy real.
* Rollback real.
* Smoke extended.
* Ejecución automática por `push` o `pull_request`.
* Cambios DNS o ACME.
* Modificación de `.env.production`.
* Modificación de `docker-compose.prod.yml`.
* Modificación de `infra/caddy/Caddyfile.prod`.
* Borrado de volúmenes.
* Publicación de puertos internos.

## 3. Matriz de evidencias R42-R47

| Ronda | Workflow / cambio          | Resultado | Evidencia aceptada                                                                                                          | Alcance                     |
| ----- | -------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| R42   | `prod-audit-state`         | GO        | `audit-state-ok`, plataforma con raíz 403 esperado, usuarios y bridges observados, reporte generado en `/opt/v4nex/runtime` | Auditoría readonly          |
| R43   | `prod-preflight`           | GO        | `preflight-ok`, digests validados, seguridad de puertos OK, health público OK                                               | Preflight controlado        |
| R44   | `prod-smoke-minimal`       | GO        | `smoke-minimal-ok`, servicios healthy, platform mode respetado, raíz 403 esperado                                           | Smoke no destructivo        |
| R45   | `prod-deploy-dry-run`      | GO        | `V4NEX_DRY_RUN=1`, operaciones mutativas omitidas, servicios healthy, port security OK                                      | Deploy simulado             |
| R46   | `prod-rollback-dry-run`    | GO        | `V4NEX_DRY_RUN=1`, rollback backend simulado, servicios healthy, port security OK                                           | Rollback simulado           |
| R47   | Mejora de gobernanza CI/CD | GO        | PR #35 mergeada; valores no sensibles pasan a `vars.*`; llave privada permanece en `secrets.*`                              | Limpieza técnica/documental |

## 4. Estado del canal GitHub Actions → VPS

El canal queda validado para ejecuciones manuales controladas, no automáticas, bajo aprobación explícita.

Estado aceptado:

* Workflows productivos integrados.
* Workflows sin triggers por `push`.
* Workflows sin triggers por `pull_request`.
* GitHub Environment `production` configurado.
* Deployment protection rules aplicadas durante ejecuciones autorizadas.
* Llave SSH dedicada configurada para GitHub Actions.
* Usuario remoto validado: `deploy`.
* Scripts productivos ejecutados solo bajo alcance autorizado.

La validación fue no destructiva. No se autoriza usar este canal para cambios reales sin una ronda futura separada.

## 5. Estado de GitHub Environment production

Environment variables:

* `PROD_SSH_HOST`
* `PROD_SSH_USER`
* `PROD_APP_PATH`
* `PROD_SSH_PORT`

Environment secret:

* `PROD_SSH_PRIVATE_KEY`

Decisión de seguridad:

* Los valores no sensibles se manejan como Environment variables para evitar masking innecesario de logs.
* La llave privada SSH permanece como secret.
* Los secretos internos de runtime no se mueven a GitHub.

No deben cargarse en GitHub:

* `.env.production`
* `POSTGRES_PASSWORD`
* `JWT_SECRET`
* `CLOUDFLARE_API_TOKEN`
* secretos internos de base de datos
* secretos ACME/DNS

## 6. Decisiones tomadas

1. El CI/CD productivo será controlado, manual y con aprobación.
2. No habrá deploy automático por `push`, `pull_request` o merge.
3. La primera validación se hizo con workflows no destructivos.
4. `prod-deploy-dry-run` y `prod-rollback-dry-run` solo validan flujo en seco.
5. `PROD_SSH_PRIVATE_KEY` es el único secreto SSH requerido en GitHub.
6. Host, usuario, puerto y ruta de aplicación se manejan como Environment variables.
7. Cualquier ejecución futura requiere ronda separada y aprobación explícita.
8. El cierre de Fase 3 no habilita deploy real.

## 7. Restricciones vigentes

Siguen prohibidas las siguientes acciones sin aprobación futura separada:

* Ejecutar workflows adicionales.
* Ejecutar deploy real.
* Ejecutar rollback real.
* Ejecutar smoke extended.
* Cambiar DNS.
* Repetir o modificar ACME.
* Modificar `.env.production`.
* Modificar `docker-compose.prod.yml`.
* Modificar `infra/caddy/Caddyfile.prod`.
* Borrar volúmenes.
* Publicar puertos internos.
* Modificar runtime fuera de una autorización explícita.

## 8. Riesgos pendientes

| Riesgo                                    | Estado                          | Tratamiento recomendado                                                            |
| ----------------------------------------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| Uso accidental de workflows               | Reducido, no eliminado          | Mantener Environment `production`, approvals y confirmación manual                 |
| Dependencia de un único reviewer          | Pendiente                       | Agregar segundo reviewer cuando exista operador confiable                          |
| Self-review permitido                     | Aceptado temporalmente para MVP | Revaluar cuando exista equipo de operación                                         |
| Deploy real no probado desde Actions      | Pendiente por diseño            | Probar solo cuando exista cambio funcional, ventana operativa y rollback preparado |
| Smoke extended no ejecutado desde Actions | Pendiente por diseño            | Ejecutar solo con target IPv6 controlado y aprobación separada                     |
| Limpieza de secrets antiguos no sensibles | Pendiente si aún existen        | Eliminar después de confirmar que workflows usan `vars.*` y App lo apruebe         |

## 9. Condiciones para futuras ejecuciones

Cualquier ejecución futura debe cumplir:

1. Ronda separada con objetivo explícito.
2. Aprobación explícita de App e Infra.
3. Environment `production` activo.
4. Confirmación manual correcta en GitHub Actions.
5. Revisión del alcance del workflow a ejecutar.
6. Validación de que no se ejecutan workflows fuera del alcance.
7. Reporte posterior con resultado, evidencia y restricciones mantenidas.

Para un deploy real futuro se requiere además:

1. Cambio funcional o nueva imagen que justifique despliegue.
2. Release manifest actualizado.
3. Tags y digests declarados.
4. Preflight GO.
5. Smoke minimal GO.
6. Deploy dry-run GO.
7. Rollback dry-run GO.
8. Ventana operativa definida.
9. Rollback real preparado.
10. Aprobación explícita App + Infra.

## 10. Declaración de cierre

Fase 3 cierra como validación inicial de CI/CD productivo controlado en modo no destructivo.

No se declara producción final abierta.
No se autoriza deploy real.
No se autoriza rollback real.
No se autoriza smoke extended.
No se autoriza ejecución adicional de workflows sin una ronda separada.

La línea base resultante mejora la operación futura porque reduce comandos manuales, mantiene control explícito sobre producción y conserva trazabilidad entre release, workflows, aprobaciones, reportes y restricciones operativas.
