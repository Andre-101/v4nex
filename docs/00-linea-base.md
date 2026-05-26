# 00 — Línea base

## Objetivo

Establecer una base mínima y funcional para desarrollo local de v4nex.

## Componentes incluidos

- `apps/frontend/`: skeleton React + Vite + Tailwind.
- `apps/backend/`: API FastAPI con endpoints `/health` y `/_v4nex/health`.
- `db` en `docker-compose.yml`: PostgreSQL 16.
- `infra/caddy/`: reverse proxy dev mínimo.
- `scripts/check-no-secrets.sh`: chequeo básico de secretos.

## Criterios de aceptación de Escenario 0

- El repositorio tiene estructura base.
- Existe `.env.example` con variables de desarrollo.
- `docker compose up --build` levanta servicios base.
- `GET /health` y `GET /_v4nex/health` responden `{"status":"ok"}` desde backend.
- No se incluyen secretos reales en el repo.

## Fuera de alcance

Registro/login real, bridges, validaciones avanzadas, CI/CD, despliegue y producción.


## Aclaraciones de alcance

- Escenario 0 se mantiene como **skeleton** de infraestructura y aplicación base.
- La API interna de desarrollo se enruta bajo `/_v4nex/*`.
- No existe flujo funcional de bridge en este escenario.
