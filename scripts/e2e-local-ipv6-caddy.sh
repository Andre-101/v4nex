#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[e2e] Missing required command: $1" >&2
    exit 1
  fi
}

json_get() {
  "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"
}

request() {
  local response
  response="$(curl -sS -w $'\n%{http_code}' "$@")"
  RESPONSE_STATUS="${response##*$'\n'}"
  RESPONSE_BODY="${response%$'\n'*}"
}

assert_status() {
  local expected="$1"
  local label="$2"
  if [[ "$RESPONSE_STATUS" != "$expected" ]]; then
    echo "[e2e] $label failed: expected HTTP $expected, got $RESPONSE_STATUS" >&2
    echo "$RESPONSE_BODY" >&2
    exit 1
  fi
}

assert_json_value() {
  local key="$1"
  local expected="$2"
  local label="$3"
  local actual
  actual="$(printf '%s' "$RESPONSE_BODY" | json_get "$key")"
  if [[ "$actual" != "$expected" ]]; then
    echo "[e2e] $label failed: expected $key=$expected, got $actual" >&2
    echo "$RESPONSE_BODY" >&2
    exit 1
  fi
}

require_command docker
require_command curl

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v py >/dev/null 2>&1; then
  PYTHON_BIN="py"
else
  echo "[e2e] Missing required command: python3, python, or py" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[e2e] Created .env from .env.example"
fi

export APP_ENV="${APP_ENV:-development}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://v4nex:devpassword@db:5432/v4nex}"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-dev-only-change-me}"
export JWT_ALGORITHM="${JWT_ALGORITHM:-HS256}"
export ACCESS_TOKEN_EXPIRE_MINUTES="${ACCESS_TOKEN_EXPIRE_MINUTES:-60}"
export CADDY_ADMIN_URL="${CADDY_ADMIN_URL:-http://caddy:2019}"
export CADDY_ADMIN_TIMEOUT_SECONDS="${CADDY_ADMIN_TIMEOUT_SECONDS:-3}"
export V4NEX_DEV_IPV6_SUBNET="${V4NEX_DEV_IPV6_SUBNET:-fd00:4:6::/64}"
export DEMO_IPV6="${DEMO_IPV6:-fd00:4:6::80}"

BACKEND_URL="${BACKEND_URL:-http://localhost:${BACKEND_PORT:-8000}}"
CADDY_URL="${CADDY_URL:-http://localhost:${CADDY_PORT:-8080}}"
SUBDOMAIN="${E2E_SUBDOMAIN:-demo-e2e-$(date +%s)}"
EMAIL="${E2E_EMAIL:-e2e-$(date +%s)-$RANDOM@example.com}"
PASSWORD="${E2E_PASSWORD:-strong-password}"

echo "[e2e] Recreating Compose services/network without deleting volumes"
docker compose down --remove-orphans

echo "[e2e] Building backend image"
docker compose build backend

echo "[e2e] Starting PostgreSQL and IPv6 demo service"
if ! docker compose up -d db demo-ipv6; then
  cat >&2 <<MSG
[e2e] Failed to start db/demo-ipv6.
[e2e] If the error mentions IPv6, your Docker daemon may not support IPv6 networks yet.
[e2e] Check Docker daemon IPv6 settings, then retry.
MSG
  exit 1
fi

echo "[e2e] Running Alembic migrations"
docker compose run --rm backend alembic upgrade head

echo "[e2e] Starting backend, frontend, and Caddy"
docker compose up -d --build backend frontend caddy
docker compose restart caddy >/dev/null

echo "[e2e] Waiting for backend health"
for _ in $(seq 1 30); do
  if curl -fsS "$BACKEND_URL/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS "$BACKEND_URL/health" >/dev/null

echo "[e2e] Checking demo IPv6 TCP reachability from backend container"
if ! docker compose exec -T backend python - "$DEMO_IPV6" <<'PY'
import socket
import sys

host = sys.argv[1]
sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
sock.settimeout(3)
try:
    sock.connect((host, 80, 0, 0))
finally:
    sock.close()
PY
then
  cat >&2 <<MSG
[e2e] Backend could not connect to demo-ipv6 at [$DEMO_IPV6]:80.
[e2e] This usually means Docker IPv6 networking is unavailable or the demo service failed to bind IPv6.
MSG
  exit 1
fi

echo "[e2e] Registering user $EMAIL"
request -X POST "$BACKEND_URL/_v4nex/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
assert_status 201 "register"

echo "[e2e] Logging in"
request -X POST "$BACKEND_URL/_v4nex/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
assert_status 200 "login"
TOKEN="$(printf '%s' "$RESPONSE_BODY" | json_get access_token)"

echo "[e2e] Creating bridge $SUBDOMAIN -> [$DEMO_IPV6]:80"
request -X POST "$BACKEND_URL/_v4nex/bridges" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"subdomain\":\"$SUBDOMAIN\",\"target_ipv6\":\"$DEMO_IPV6\",\"target_port\":80}"
assert_status 201 "create bridge"
BRIDGE_ID="$(printf '%s' "$RESPONSE_BODY" | json_get id)"

echo "[e2e] Validating TCP connectivity"
request -X POST "$BACKEND_URL/_v4nex/bridges/$BRIDGE_ID/validate" \
  -H "Authorization: Bearer $TOKEN"
assert_status 200 "validate bridge"
assert_json_value status READY "validate bridge"

echo "[e2e] Activating bridge"
request -X POST "$BACKEND_URL/_v4nex/bridges/$BRIDGE_ID/activate" \
  -H "Authorization: Bearer $TOKEN"
assert_status 200 "activate bridge"
assert_json_value status ACTIVE "activate bridge"

echo "[e2e] Checking Caddy reverse proxy with Host: $SUBDOMAIN.v4nex.com"
PROXY_BODY="$(curl -fsS -H "Host: $SUBDOMAIN.v4nex.com" "$CADDY_URL/")"
if [[ "$PROXY_BODY" != *"Directory listing"* && "$PROXY_BODY" != *"Python"* ]]; then
  echo "[e2e] Proxy response did not look like Python http.server output" >&2
  echo "$PROXY_BODY" >&2
  exit 1
fi

echo "[e2e] Disabling bridge"
request -X POST "$BACKEND_URL/_v4nex/bridges/$BRIDGE_ID/disable" \
  -H "Authorization: Bearer $TOKEN"
assert_status 200 "disable bridge"
assert_json_value status DISABLED "disable bridge"

echo "[e2e] Checking Caddy route after disable"
POST_DISABLE_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' -H "Host: $SUBDOMAIN.v4nex.com" "$CADDY_URL/")"
if [[ "$POST_DISABLE_STATUS" == "000" ]]; then
  echo "[e2e] Caddy did not respond after disable" >&2
  exit 1
fi

cat <<SUMMARY
[e2e] OK
  user: $EMAIL
  bridge_id: $BRIDGE_ID
  subdomain: $SUBDOMAIN
  target: [$DEMO_IPV6]:80
  validate: READY
  activate: ACTIVE
  disable: DISABLED
  post_disable_http_status: $POST_DISABLE_STATUS
SUMMARY
