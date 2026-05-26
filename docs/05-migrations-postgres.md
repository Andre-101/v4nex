# 05 - Migraciones reales y PostgreSQL dev

## Resumen ejecutivo

Este escenario profesionaliza la persistencia del backend de v4nex: agrega Alembic, una migración inicial para el esquema mínimo y configuración explícita para PostgreSQL de desarrollo.

La app deja de depender de `Base.metadata.create_all()` como mecanismo operativo en desarrollo. La creación automática de tablas queda limitada al entorno de test con SQLite in-memory.

## Qué se implementó

- Alembic dentro de `apps/backend`.
- Migración inicial para:
  - `users`
  - `bridges`
  - `bridge_events`
- Configuración por entorno con `APP_ENV`.
- `DATABASE_URL` alineado a `postgresql+psycopg://...` para usar `psycopg` v3.
- Variables JWT documentadas en `.env.example`.
- Tests backend conservando SQLite in-memory para rapidez y aislamiento.

## Fuera de alcance

- Validación TCP real.
- Caddy dinámico.
- Reload de Caddy.
- TLS real.
- Frontend funcional.
- CI/CD.
- Deploy.
- Billing.
- Rate limiting real.
- Heartbeat real.
- Métricas avanzadas.
- Endpoints `validate`, `activate` o `disable`.

## Variables de entorno

Desarrollo local esperado:

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg://v4nex:devpassword@db:5432/v4nex
JWT_SECRET_KEY=dev-only-change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

`JWT_SECRET_KEY=dev-only-change-me` es inseguro y existe solo para desarrollo. Producción debe inyectar un secreto real por variable de entorno. No se debe crear `.env.production` con secretos.

## Comandos Alembic

Desde `apps/backend`:

```bash
python -m pip install -r requirements.txt
alembic upgrade head
alembic revision --autogenerate -m "message"
python -m pytest -p no:cacheprovider
```

## Tests

La suite de tests usa:

- `APP_ENV=test`
- `DATABASE_URL=sqlite:///:memory:`

En ese modo, la app puede crear tablas automáticamente para mantener tests rápidos y aislados. En desarrollo con PostgreSQL se deben ejecutar migraciones Alembic.

## Smoke test con PostgreSQL Docker

Desde la raíz del repo:

```bash
cp .env.example .env
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose up --build
```

Luego probar:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/_v4nex/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"strong-password"}'
curl -X POST http://localhost:8000/_v4nex/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"strong-password"}'
curl -X POST http://localhost:8000/_v4nex/bridges \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"subdomain":"demo","target_ipv6":"2606:4700:4700::1111","target_port":80}'
```

Reemplazar `TOKEN` por el `access_token` obtenido en login.

Si ya existe un `.env` local de escenarios anteriores, actualizar `DATABASE_URL` a `postgresql+psycopg://v4nex:devpassword@db:5432/v4nex`; el formato antiguo `postgresql://...` intenta usar `psycopg2` y no corresponde a este escenario.

## Riesgos y pendientes

- Agregar Alembic a la disciplina normal del proyecto: todo cambio de modelo debe tener migración.
- Validar el flujo completo contra PostgreSQL en Docker antes de escenarios con más lógica.
- Evaluar constraints adicionales a nivel DB para estados y resultados.
- Preparar el siguiente escenario sin introducir aún efectos externos de red.
