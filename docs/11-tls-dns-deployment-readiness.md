# 11 - Preparacion TLS/DNS y readiness de despliegue

## Resumen ejecutivo

El estado actual de v4nex es local/dev: backend FastAPI con auth, bridges, validacion TCP IPv6, Caddy dinamico dev con rollback, reconciliacion DB -> Caddy, diagnosticos internos, PostgreSQL dev con Alembic y E2E local con `demo-ipv6`.

Para pasar a internet faltan decisiones y controles operativos: DNS publico, TLS real, secretos productivos, firewall, roles/admin reales, rate limiting, backups, monitoreo minimo y runbook probado en VPS.

Este escenario no ejecuta deploy, no emite certificados reales y no integra APIs reales de DNS o Cloudflare. Solo documenta la preparacion tecnica y operativa.

## Supuestos

- Dominio base de ejemplo: `v4nex.com`.
- Edge con IPv4 publica en una VPS.
- Caddy actua como reverse proxy publico.
- Los servicios destino publicados por bridges usan IPv6.
- El backend/API/control plane no debe exponerse sin controles.
- Caddy Admin API nunca debe exponerse a internet.
- MVP inicial en una sola VPS.
- Docker Compose para MVP inicial; no Kubernetes.

## Diseno DNS recomendado

Registros recomendados:

- `A v4nex.com -> IPv4 publica de la VPS`, si la landing o raiz vive en el edge.
- `A panel.v4nex.com -> IPv4 publica de la VPS`, si el panel usa subdominio dedicado.
- `A *.v4nex.com -> IPv4 publica de la VPS`, para bridges de usuario.

El routing real ocurre por `Host` header en Caddy. DNS solo entrega todos los subdominios del wildcard al mismo edge IPv4; Caddy decide si el host corresponde a plataforma, frontend, API o bridge dinamico.

Subdominios reservados de plataforma:

- `www`
- `api`
- `admin`
- `panel`
- `login`
- `dashboard`
- `status`
- `mail`
- `smtp`
- `ftp`
- `ssh`
- `root`
- `support`
- `billing`
- `docs`
- `dev`
- `test`
- `_v4nex`

`_v4nex` tambien queda reservado como namespace tecnico interno de plataforma.

## Estrategia TLS

| Alternativa | Uso | Ventajas | Riesgos / limites |
| --- | --- | --- | --- |
| HTTP only dev | Solo local | Simple, sin certificados | No apto para produccion |
| ACME HTTP-01 por subdominio | Produccion pequena | Simple para pocos hosts | Puede complicarse con muchos subdominios dinamicos |
| ACME DNS-01 wildcard | MVP publico recomendado | Permite certificado wildcard para `*.v4nex.com` | Requiere token DNS y control cuidadoso de secretos |
| Cloudflare Origin Cert | Si Cloudflare proxy esta delante | Practico detras de Cloudflare | Menos portable; depende del proxy Cloudflare |

Recomendacion para MVP publico: ACME DNS-01 wildcard con proveedor DNS compatible. Si el dominio esta en Cloudflare, usar Cloudflare como proveedor DNS es una opcion natural.

Reglas para tokens DNS:

- No guardar tokens DNS en el repo.
- Usar variables de entorno o secrets del entorno de despliegue.
- Rotar tokens de forma periodica.
- Usar permisos minimos: modificar solo zona DNS necesaria.
- Revocar tokens ante sospecha de filtracion.

## Arquitectura publica propuesta

```text
Internet IPv4 user
-> DNS wildcard *.v4nex.com
-> VPS public IPv4
-> Caddy public :80/:443
-> dynamic route by Host header
-> IPv6 backend target
```

Planos operativos:

- Data plane: trafico publico cliente -> Caddy -> IPv6 target.
- Control plane: backend API, DB, Caddy Admin API.
- Admin plane: SSH/VPS/operator.

El data plane puede ser publico. El control plane debe quedar protegido por red interna, autenticacion, autorizacion y firewall. El admin plane debe estar limitado a operadores autorizados.

## Puertos y exposicion

| Puerto | Servicio | Exposicion recomendada | Nota |
| --- | --- | --- | --- |
| 80 | Caddy HTTP / ACME redirect | Publico | Redireccion a HTTPS y/o challenge ACME segun estrategia |
| 443 | Caddy HTTPS | Publico | Trafico publico de plataforma y bridges |
| 2019 | Caddy Admin API | Solo red interna Docker/localhost | Nunca publico |
| 5432 | PostgreSQL | Solo red interna Docker | Nunca publico |
| 8000 | Backend FastAPI | Idealmente interno | Si se expone, hacerlo detras de Caddy y auth |
| 22 | SSH | Restringido | Firewall, llaves, sin password si es posible |

## Secrets y variables de entorno

Variables esperadas para un despliegue futuro:

- `JWT_SECRET_KEY`
- `DATABASE_URL`
- `POSTGRES_PASSWORD`
- `CADDY_ADMIN_URL`
- `DNS_PROVIDER_API_TOKEN`
- `ACME_EMAIL`
- `PUBLIC_DOMAIN`

Reglas operativas:

- No crear ni commitear `.env.production`.
- Guardar secretos en la VPS con archivo protegido o secret manager.
- Usar permisos tipo `chmod 600` para archivos locales de secretos.
- Evitar copiar secretos a backups sin cifrado.
- No imprimir secretos en logs.
- No exponer `DATABASE_URL` completo en diagnosticos.

## Seguridad y abuso minimo

Antes de produccion:

- Auth obligatoria para operaciones de control plane.
- Endpoints admin deben ser admin-only.
- Rate limiting minimo para:
  - register
  - login
  - validate
  - activate
  - disable
- Limites por usuario:
  - numero maximo de bridges
  - frecuencia de `validate`
  - frecuencia de `activate` / `disable`
- Bloqueo estricto de subdominios reservados.
- Logs sin secretos, tokens ni passwords.
- Politica minima de abuso para servicios publicados.
- Estado futuro `SUSPENDED` para bloqueo operativo o abuso.

## Riesgos

| Riesgo | Impacto | Probabilidad | Mitigacion | Estado |
| --- | --- | --- | --- | --- |
| Caddy Admin API expuesta | Critico: control total del proxy | Media si se configura mal | Firewall, red interna Docker, no publicar 2019 | Pendiente de validar en prod |
| DNS token filtrado | Alto: control de registros DNS | Media | Secret manager, permisos minimos, rotacion | Pendiente |
| Abuso de validate como scanner | Alto: uso de backend para escaneo | Alta sin limites | Rate limiting, cuotas, auditoria | Pendiente |
| Abuso de proxy para contenido ilegal | Alto legal/operativo | Media | Politica de abuso, suspension, logs operativos | Pendiente |
| Carrera DB/Caddy en multiples procesos | Medio/alto: config inconsistente | Media al escalar | Lock distribuido o reconciler central | Pendiente |
| Caida de VPS | Alto: servicio offline | Media | Backups, monitoreo, runbook restore | Pendiente |
| Falta de backups | Alto: perdida de datos | Media | Backups cifrados y restore probado | Pendiente |
| Costos por ancho de banda | Medio/alto | Media | Limites, alertas de consumo | Pendiente |
| Proveedor bloquea trafico | Medio/alto | Baja/media | Cumplimiento, proveedor alterno, logs | Pendiente |
| IPv6 target inestable | Medio: bridges intermitentes | Alta | Heartbeat futuro, eventos, revalidacion | Pendiente |

## Runbook futuro de despliegue MVP

No ejecutar en este escenario. Runbook propuesto:

1. Comprar o configurar dominio.
2. Configurar DNS base y wildcard.
3. Crear VPS.
4. Configurar firewall:
   - abrir 80/443
   - restringir 22
   - bloquear 2019/5432/8000 publicos
5. Instalar Docker y Docker Compose plugin.
6. Subir compose productivo futuro.
7. Cargar secrets productivos fuera del repo.
8. Ejecutar migraciones Alembic.
9. Levantar servicios.
10. Emitir certificado TLS wildcard.
11. Ejecutar smoke test:
    - health
    - register/login
    - create bridge
    - validate
    - activate
    - request por `Host` header o DNS real
    - disable
12. Configurar monitoreo minimo.
13. Configurar backups.
14. Probar rollback.

## Criterios de entrada para deploy real

- Roles/admin reales para endpoints internos.
- Rate limiting minimo.
- Secrets reales cargados fuera del repo.
- Firewall validado.
- Backups configurados y restore probado.
- Smoke E2E en VPS.
- TLS wildcard validado.
- Logs revisados para evitar secretos.
- Runbook probado.
- Politica de abuso minima.

## Decision final

No se recomienda hacer deploy publico todavia.

El siguiente paso despues de este documento deberia ser una de estas rutas:

- Hardening del control plane: roles/admin, rate limiting, cuotas, auditoria y politicas de abuso.
- Preparacion de compose prod: separacion clara de dev/prod, secretos externos, firewall documentado y Caddy TLS real planeado.

El MVP local validado debe mantenerse como base tecnica antes de abrir trafico publico.
