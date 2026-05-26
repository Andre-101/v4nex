# 09 - E2E local IPv6 + Caddy dev

## Resumen ejecutivo

Este escenario agrega una prueba E2E local reproducible para validar el flujo real de v4nex con PostgreSQL, backend, frontend, Caddy dev y un servicio demo IPv6 interno en Docker Compose.

El flujo usa únicamente API:

- register
- login
- create bridge
- validate
- activate
- disable

No usa escrituras manuales en base de datos.

## Alcance

- Servicio `demo-ipv6` interno en Docker Compose.
- Red Docker dev con IPv6 habilitado.
- Script manual `scripts/e2e-local-ipv6-caddy.sh`.
- Validación TCP real contra `[DEMO_IPV6]:80`.
- Activación Caddy dev con Admin API.
- Prueba de reverse proxy usando Host header.
- Desactivación del bridge.

## Fuera de alcance

- TLS real.
- ACME.
- Cloudflare.
- DNS público.
- CI/CD.
- Deploy.
- Frontend funcional.
- Billing.
- Heartbeat real.
- Rate limiting real.
- Métricas avanzadas.

## Prerequisitos

- Docker Compose disponible.
- `curl`.
- `python`.
- Bash compatible.

En Windows se recomienda Git Bash o WSL.

## Variables relevantes

`.env.example` incluye:

```env
V4NEX_DEV_IPV6_SUBNET=fd00:4:6::/64
DEMO_IPV6=fd00:4:6::80
```

El script exporta valores de desarrollo seguros si no están definidos en el entorno.

## Comandos exactos

Desde la raíz del repo:

```bash
bash scripts/e2e-local-ipv6-caddy.sh
```

El script:

1. Copia `.env.example` a `.env` solo si `.env` no existe.
2. Construye backend.
3. Levanta `db` y `demo-ipv6`.
4. Ejecuta `alembic upgrade head`.
5. Levanta backend, frontend y Caddy.
6. Registra usuario único.
7. Hace login.
8. Crea bridge apuntando a `[DEMO_IPV6]:80`.
9. Ejecuta validate y exige `READY`.
10. Ejecuta activate y exige `ACTIVE`.
11. Prueba Caddy con Host header.
12. Ejecuta disable y exige `DISABLED`.
13. Verifica que Caddy sigue respondiendo tras remover la ruta dinámica.

## Qué valida el E2E

- PostgreSQL dev y migraciones Alembic.
- Auth básica.
- Creación de bridge persistente.
- Validación TCP real sobre IPv6.
- Activación dinámica de Caddy.
- Reverse proxy por Host header.
- Desactivación dinámica de Caddy.
- Estado final `DISABLED`.

## Host header

Como no hay DNS público ni wildcard local, la prueba de Caddy usa:

```bash
curl -H "Host: demo-e2e-xxxx.v4nex.com" http://localhost:8080/
```

El subdominio exacto cambia por corrida para evitar colisiones en base de datos.

## Limpieza

Para detener contenedores:

```bash
docker compose down
```

Para borrar volumen de PostgreSQL dev:

```bash
docker compose down -v
```

## Limitaciones

- No prueba TLS.
- No prueba DNS público.
- No prueba Cloudflare.
- No valida experiencia frontend.
- Depende de que Docker pueda crear una red dev con IPv6.
- El servicio demo no se expone al host; solo es accesible desde la red Docker.

## Riesgos y pendientes

- En algunos entornos Docker, IPv6 puede requerir configuración del daemon.
- Agregar un modo de diagnóstico si Docker no permite `enable_ipv6`.
- Formalizar un perfil Compose para E2E si el archivo dev crece demasiado.
- Preparar pruebas de concurrencia para activación/desactivación.
- Diseñar escenarios TLS/DNS reales más adelante.
