# CI/CD productivo controlado — v4nex v0.1

## Resumen ejecutivo

Este documento define la primera iteración de CI/CD productivo controlado para v4nex. El objetivo es reducir la operación manual sin habilitar despliegues automáticos ni perder control sobre producción.

La estrategia es:

- CI automático para App.
- CD semiautomático para Producción.
- Workflows manuales con `workflow_dispatch`.
- GitHub Environment `production` con aprobaciones.
- Sin deploy real en esta iteración.
- Sin ejecución automática por `push`, `pull_request` o `merge`.

## Separación CI App / CD Infra

App es responsable de pruebas, build, publicación de imágenes, scans, tags, digests, release manifest, declaración de migraciones y documentación técnica de la aplicación.

Infra es responsable de VPS, runtime productivo, Docker Compose productivo, Caddy/TLS/DNS operativo, secretos productivos, GitHub Environment `production`, workflows productivos, gating, evidencia, auditoría y rollback operativo.

Infra no necesita conocer la lógica interna de backend o frontend. Infra consume artefactos versionados y opera producción.

## Workflows disponibles

| Workflow | Ejecución | Propósito |
|---|---|---|
| `prod-preflight.yml` | manual | Ejecuta preflight productivo |
| `prod-smoke-minimal.yml` | manual | Ejecuta smoke minimal |
| `prod-deploy-dry-run.yml` | manual | Simula deploy con dry-run |
| `prod-rollback-dry-run.yml` | manual | Simula rollback con dry-run |
| `prod-audit-state.yml` | manual | Ejecuta auditoría readonly |

No existe workflow de deploy real en esta iteración.

## Variables y secretos requeridos

Los siguientes nombres deben configurarse en GitHub Environment `production`, sin valores dentro del repositorio:

- `PROD_SSH_HOST`
- `PROD_SSH_USER`
- `PROD_SSH_PRIVATE_KEY`
- `PROD_APP_PATH`
- `PROD_SSH_PORT`

Los secretos internos de la aplicación y del runtime permanecen en la VPS. No deben copiarse al repositorio ni imprimirse en logs.

## Environment production

Antes de ejecutar cualquier workflow, el Environment `production` debe tener:

- revisores requeridos;
- secretos productivos mínimos para conexión SSH;
- acceso limitado a personas autorizadas;
- revisión explícita antes de cada ejecución.

La existencia de los workflows no autoriza su ejecución.

## Aprobaciones requeridas

Cada workflow requiere:

1. Aprobación de la ronda correspondiente.
2. Ejecución manual desde GitHub Actions.
3. Confirmación escrita en el input del workflow.
4. Aprobación del Environment `production`.

## Orden recomendado de ejecución

Para una validación no destructiva, el orden recomendado es:

1. `prod-preflight.yml`.
2. `prod-smoke-minimal.yml`.
3. `prod-deploy-dry-run.yml`.
4. `prod-rollback-dry-run.yml`.
5. `prod-audit-state.yml`.

Este orden replica la secuencia validada en seco durante Fase 2.

## Dry-run vs deploy real

Dry-run significa validar el flujo sin aplicar cambios reales al runtime. En esta iteración los workflows de deploy y rollback solo ejecutan modo seco.

Deploy real significa modificar runtime, recrear servicios o aplicar cambios productivos. Deploy real queda fuera de esta iteración y requiere una fase posterior con aprobación explícita.

## Restricciones

Queda prohibido en esta iteración:

- deploy real;
- rollback real;
- smoke extended;
- ejecución automática por push;
- ejecución automática por pull request;
- ejecución automática por merge;
- cambios DNS;
- repetición ACME;
- modificación de configuración productiva fuera del alcance;
- borrado de volúmenes;
- publicación de puertos internos;
- uso de `latest` como tag operativo.

## Criterios de aceptación

La primera iteración se considera aceptable si:

- todos los workflows son manuales;
- todos usan Environment `production`;
- todos tienen timeout;
- todos validan configuración mínima;
- todos escriben resumen de ejecución;
- ninguno se ejecuta por push o pull request;
- ninguno ejecuta deploy real;
- ninguno ejecuta rollback real;
- ninguno ejecuta smoke extended;
- no se modifican backend, frontend, Docker Compose productivo, Caddyfile base ni release manifest.

## Condiciones para deploy real futuro

Un deploy real futuro requiere:

1. cambio funcional o nueva imagen que justifique despliegue;
2. release manifest actualizado;
3. tags y digests declarados;
4. preflight GO;
5. smoke minimal GO;
6. deploy dry-run GO;
7. rollback dry-run GO;
8. ventana operativa definida;
9. rollback real preparado;
10. aprobación explícita de App e Infra.

## Estado

Este documento y los workflows asociados son una entrega técnica para revisión. El merge no autoriza ejecución operativa. Cualquier ejecución futura requiere una ronda separada con aprobación explícita.
