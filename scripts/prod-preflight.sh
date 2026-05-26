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

postgres_password_line="$(grep -E '^POSTGRES_PASSWORD=' "$ENV_FILE" | tail -n 1 || true)"
if [[ -n "$postgres_password_line" ]]; then
  postgres_password_value="${postgres_password_line#*=}"
  export POSTGRES_PASSWORD="${postgres_password_value%$'\r'}"
fi

echo "Checking compose config without starting services..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config >/dev/null
echo "OK docker compose config valid"
echo "Production preflight passed. No services were started."
