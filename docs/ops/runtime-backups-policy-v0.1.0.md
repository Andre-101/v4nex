# Política mínima de backups runtime — v4nex v0.1.0

## Propósito

Definir una política mínima para conservar, revisar y limpiar artefactos generados en `/opt/v4nex/runtime` durante la operación controlada de v4nex v0.1.0.

Esta política aplica a backups de configuración, reportes operativos y artefactos generados por scripts de preflight, smoke, deploy dry-run, rollback dry-run y auditoría.

## Alcance

Aplica a:

- Backups de `.env.production` generados por scripts de deploy o rollback.
- Reportes de preflight.
- Reportes de smoke.
- Reportes de deploy dry-run.
- Reportes de rollback dry-run.
- Reportes de audit-state.
- Backups de configuración viva de Caddy generados durante correcciones controladas.
- Artefactos asociados a releases cerrados.

No aplica a:

- Volúmenes Docker productivos.
- Backups de base de datos completos.
- Snapshots del proveedor VPS.
- Backups externos fuera de `/opt/v4nex/runtime`.

## Ubicación principal

La ubicación principal de runtime es:

```text
/opt/v4nex/runtime
```

Ningún archivo dentro de esta ruta debe tratarse como sustituto de un backup formal de base de datos o de infraestructura. Es una carpeta de evidencia operativa y recuperación rápida de configuración.

## Recursos protegidos

Queda prohibido borrar sin plan de recuperación documentado:

- `app_postgres_data`.
- `app_caddy_data`.
- `app_caddy_config`.
- Backups `caddy-live-before-*` cuando exista una configuración viva modificada que dependa de ellos.
- Último backup conocido válido de `.env.production`.

## Retención mínima

| Tipo de artefacto | Retención mínima |
|---|---|
| Backups de `.env.production` | Últimos 5 backups |
| Reportes operativos generales | Últimos 10 reportes |
| Reportes asociados a releases cerrados | Conservar completos |
| Backups `caddy-live-before-*` | Conservar mientras la configuración viva dependa del cambio |
| Backups previos a sincronización de artefactos | Conservar hasta cierre documental de la fase |

## Artefactos asociados a Fase 2

Los siguientes reportes deben conservarse como evidencia de cierre de Fase 2:

- `/opt/v4nex/runtime/preflight-v0.1.0-20260529_013527.txt`.
- `/opt/v4nex/runtime/smoke-v0.1.0-20260529_013852.txt`.
- `/opt/v4nex/runtime/deploy-v0.1.0-20260529_015404.txt`.
- `/opt/v4nex/runtime/rollback-v0.1.0-20260529_015846.txt`.
- `/opt/v4nex/runtime/audit-state-v0.1.0-20260529_020158.txt`.

## Limpieza manual

Toda limpieza debe ser:

1. Manual.
2. Explícita.
3. Registrada.
4. Ejecutada fuera de una ventana de despliegue.
5. Revisada antes de borrar artefactos de releases cerrados.

No se autoriza limpieza automática en v0.1.0.

## Registro mínimo de limpieza

Cada limpieza debe registrar:

- Fecha UTC.
- Responsable.
- Archivos eliminados.
- Motivo.
- Confirmación de que no se eliminaron volúmenes productivos.
- Confirmación de que no se eliminó el último backup válido de `.env.production`.

Formato recomendado:

```text
fecha_utc=<YYYY-MM-DDTHH:MM:SSZ>
responsable=<nombre o usuario operativo>
accion=runtime-cleanup
archivos_eliminados=<lista>
motivo=<motivo>
volumenes_productivos_eliminados=no
ultimo_env_backup_eliminado=no
```

## Restricciones

Queda prohibido:

- Ejecutar `rm -rf /opt/v4nex/runtime`.
- Borrar volúmenes Docker productivos como parte de limpieza de runtime.
- Borrar `app_postgres_data` sin plan de recuperación.
- Borrar `app_caddy_data` sin plan de recuperación.
- Borrar `app_caddy_config` sin plan de recuperación.
- Borrar reportes asociados a releases cerrados sin aprobación explícita.
- Automatizar limpieza sin una política aprobada y probada.

## Recomendación operativa

Para v0.1.0, la limpieza debe mantenerse conservadora. El costo de almacenar reportes de texto y backups pequeños es bajo comparado con el valor de trazabilidad durante la estabilización del MVP.

## Pendientes

- Definir backup formal de PostgreSQL.
- Definir snapshot del proveedor VPS.
- Definir retención automatizada segura para versiones posteriores.
- Definir cifrado o protección adicional para backups sensibles.
- Definir procedimiento de restauración probado para `.env.production`.
