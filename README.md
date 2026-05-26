# v4nex — Escenario 0 (Preparación del repo)

Este repositorio contiene la línea base de desarrollo local para **v4nex**.

## Alcance de este escenario

Incluye únicamente:
- Estructura base del repo.
- Frontend skeleton con React + Vite + Tailwind.
- Backend skeleton con FastAPI y endpoint `/health`.
- PostgreSQL 16 en Docker Compose.
- Caddy mínimo para desarrollo.
- Archivos base de configuración: `.env.example`, `.gitignore`.
- Documentación de línea base y script de verificación de secretos.

## Requisitos

- Docker + Docker Compose plugin
- Node.js 20+
- Python 3.11+

## Inicio rápido

1) Copia variables de entorno:

```bash
cp .env.example .env
```

2) Levanta infraestructura local (db + backend + frontend + caddy):

```bash
docker compose up --build
```

3) URLs:

- Frontend: `http://localhost:5173`
- Backend (directo): `http://localhost:8000/health`
- Backend por Caddy (ruta interna): `http://localhost:8080/_v4nex/health`
- Caddy (proxy dev): `http://localhost:8080`
- Postgres: `localhost:5432`

## Comandos útiles

```bash
# Verifica que no haya secretos obvios
bash scripts/check-no-secrets.sh

# Frontend local sin Docker
cd apps/frontend && npm install && npm run dev

# Backend local sin Docker
cd apps/backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload
```

## Nota

Este escenario **no** implementa registro/login real, bridges, validaciones avanzadas, CI/CD ni despliegue.

## Readiness productivo

- [Escenario 23 - App images, compose productivo propuesto y SYNC Ronda 2](docs/23-app-images-compose-sync.md)
