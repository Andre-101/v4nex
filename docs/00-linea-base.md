# 00 — Línea base

## Objetivo

Establecer una base mínima y funcional para desarrollo local de v4nex.

## Componentes incluidos

- `frontend/`: skeleton React + Vite + Tailwind.
- `backend/`: API FastAPI con endpoint `/health`.
- `db` en `docker-compose.yml`: PostgreSQL 16.
- `caddy/`: reverse proxy dev mínimo.
- `scripts/check-no-secrets.sh`: chequeo básico de secretos.

## Criterios de aceptación de Escenario 0

- El repositorio tiene estructura base.
- Existe `.env.example` con variables de desarrollo.
- `docker compose up --build` levanta servicios base.
- `GET /health` responde `{"status":"ok"}` desde backend.
- No se incluyen secretos reales en el repo.

## Fuera de alcance

Registro/login real, bridges, validaciones avanzadas, CI/CD, despliegue y producción.
