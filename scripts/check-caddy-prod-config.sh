#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=".env.production"
ALLOW_PLACEHOLDERS="false"

for arg in "$@"; do
  case "$arg" in
    --allow-placeholders)
      ALLOW_PLACEHOLDERS="true"
      ;;
    *)
      ENV_FILE="$arg"
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CADDYFILE="${REPO_ROOT}/infra/caddy/Caddyfile.prod.example"

if [[ ! -f "$CADDYFILE" ]]; then
  echo "ERROR Caddyfile.prod.example missing"
  exit 1
fi
echo "OK Caddyfile.prod.example present"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR env_file missing"
  echo "  env_file: $ENV_FILE"
  exit 1
fi
echo "OK env file present"

get_env_value() {
  local name="$1"
  local line
  line="$(grep -E "^${name}=" "$ENV_FILE" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    printf ''
    return
  fi
  value="${line#*=}"
  printf '%s' "${value%$'\r'}"
}

has_errors="false"

domain="$(get_env_value DOMAIN)"
if [[ -z "$domain" || "$domain" == "example.com" ]]; then
  echo "ERROR DOMAIN must not be empty or example.com"
  has_errors="true"
elif [[ "$domain" != "v4nex.com" ]]; then
  echo "ERROR DOMAIN must be v4nex.com for this infrastructure baseline"
  has_errors="true"
else
  echo "OK DOMAIN v4nex.com"
fi

caddy_domain="$(get_env_value CADDY_DOMAIN)"
if [[ -z "$caddy_domain" ]]; then
  echo "ERROR CADDY_DOMAIN must not be empty"
  has_errors="true"
elif [[ "$caddy_domain" != "$domain" ]]; then
  echo "ERROR CADDY_DOMAIN must match DOMAIN"
  has_errors="true"
else
  echo "OK CADDY_DOMAIN matches DOMAIN"
fi

caddy_acme_email="$(get_env_value CADDY_ACME_EMAIL)"
if [[ -z "$caddy_acme_email" || "$caddy_acme_email" == "admin@example.com" ]]; then
  if [[ "$ALLOW_PLACEHOLDERS" == "true" && "$caddy_acme_email" == "admin@example.com" ]]; then
    echo "OK CADDY_ACME_EMAIL placeholder allowed"
  else
    echo "ERROR CADDY_ACME_EMAIL must be replaced"
    has_errors="true"
  fi
else
  echo "OK CADDY_ACME_EMAIL replaced"
fi

cloudflare_token="$(get_env_value CLOUDFLARE_API_TOKEN)"
if [[ -z "$cloudflare_token" || "$cloudflare_token" == "change-me" ]]; then
  if [[ "$ALLOW_PLACEHOLDERS" == "true" && "$cloudflare_token" == "change-me" ]]; then
    echo "OK CLOUDFLARE_API_TOKEN placeholder allowed"
  else
    echo "ERROR CLOUDFLARE_API_TOKEN must be replaced"
    has_errors="true"
  fi
else
  echo "OK CLOUDFLARE_API_TOKEN replaced"
fi

backend_port="$(get_env_value BACKEND_PORT)"
if [[ -z "$backend_port" ]]; then
  echo "ERROR BACKEND_PORT must not be empty"
  has_errors="true"
else
  echo "OK BACKEND_PORT present"
fi

if [[ "$has_errors" == "true" ]]; then
  echo "Caddy production config check failed."
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  echo "Checking Caddyfile syntax with caddy:2. This does not run ACME."
  if ! docker run --rm \
    -e DOMAIN="$domain" \
    -e CADDY_DOMAIN="$caddy_domain" \
    -e CADDY_ACME_EMAIL="$caddy_acme_email" \
    -e BACKEND_PORT="$backend_port" \
    -v "$CADDYFILE:/etc/caddy/Caddyfile:ro" \
    caddy:2 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1; then
    echo "ERROR Caddyfile syntax invalid"
    exit 1
  fi
  echo "OK Caddyfile syntax valid"
else
  echo "WARN docker command not found; skipped caddy validate"
fi

echo "Caddy production config check passed."
