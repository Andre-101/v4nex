#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=".env.production"
ALLOW_PLACEHOLDERS_ARGS=()

for arg in "$@"; do
  case "$arg" in
    --allow-placeholders)
      ALLOW_PLACEHOLDERS_ARGS+=("--allow-placeholders")
      ;;
    *)
      ENV_FILE="$arg"
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.prod.example.yml"

bash "${SCRIPT_DIR}/check-prod-env.sh" "$ENV_FILE" "${ALLOW_PLACEHOLDERS_ARGS[@]}"
bash "${SCRIPT_DIR}/check-caddy-prod-config.sh" "$ENV_FILE" "${ALLOW_PLACEHOLDERS_ARGS[@]}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi
echo "OK docker command present"

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR docker compose plugin is required."
  exit 1
fi
echo "OK docker compose plugin present"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERROR docker-compose.prod.example.yml missing."
  exit 1
fi
echo "OK docker-compose.prod.example.yml present"

if grep -Eq '(^|[:/])latest($|[^A-Za-z0-9_.-])' "$COMPOSE_FILE"; then
  echo "ERROR docker-compose.prod.example.yml must not use latest"
  exit 1
fi
echo "OK compose does not use latest"

for forbidden_port in 2019 5432 8000 5173; do
  if grep -Eq "\"?${forbidden_port}:${forbidden_port}\"?" "$COMPOSE_FILE"; then
    echo "ERROR compose must not publish ${forbidden_port}"
    exit 1
  fi
  echo "OK compose does not publish ${forbidden_port}"
done

load_env_for_compose() {
  local name="$1"
  local line
  line="$(grep -E "^${name}=" "$ENV_FILE" | tail -n 1 || true)"
  if [[ -n "$line" ]]; then
    value="${line#*=}"
    export "$name=${value%$'\r'}"
  fi
}

for name in APP_ENV DOMAIN CADDY_DOMAIN IMAGE_TAG POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD JWT_SECRET CLOUDFLARE_API_TOKEN CADDY_ACME_EMAIL BACKEND_PORT; do
  load_env_for_compose "$name"
done

echo "Checking compose config without starting services..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config >/dev/null
echo "OK docker compose config valid"
echo "Production preflight passed. No services were started."
