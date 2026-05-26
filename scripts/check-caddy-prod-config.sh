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

public_domain="$(get_env_value PUBLIC_DOMAIN)"
if [[ -z "$public_domain" || "$public_domain" == "example.com" ]]; then
  if [[ "$ALLOW_PLACEHOLDERS" == "true" && "$public_domain" == "example.com" ]]; then
    echo "OK PUBLIC_DOMAIN placeholder allowed"
  else
    echo "ERROR PUBLIC_DOMAIN must not be empty or example.com"
    has_errors="true"
  fi
else
  echo "OK PUBLIC_DOMAIN non-placeholder"
fi

acme_email="$(get_env_value ACME_EMAIL)"
if [[ -z "$acme_email" || "$acme_email" == "admin@example.com" ]]; then
  if [[ "$ALLOW_PLACEHOLDERS" == "true" && "$acme_email" == "admin@example.com" ]]; then
    echo "OK ACME_EMAIL placeholder allowed"
  else
    echo "ERROR ACME_EMAIL must not be empty or admin@example.com"
    has_errors="true"
  fi
else
  echo "OK ACME_EMAIL non-placeholder"
fi

dns_token="$(get_env_value DNS_PROVIDER_API_TOKEN)"
if [[ -z "$dns_token" || "$dns_token" == "change-me" ]]; then
  if [[ "$ALLOW_PLACEHOLDERS" == "true" && "$dns_token" == "change-me" ]]; then
    echo "OK DNS_PROVIDER_API_TOKEN placeholder allowed"
  else
    echo "ERROR DNS_PROVIDER_API_TOKEN must be replaced"
    has_errors="true"
  fi
else
  echo "OK DNS_PROVIDER_API_TOKEN replaced"
fi

if [[ "$has_errors" == "true" ]]; then
  echo "Caddy production config check failed."
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  echo "Checking Caddyfile syntax with caddy:2. This does not run ACME."
  if ! docker run --rm \
    -e PUBLIC_DOMAIN="$public_domain" \
    -e ACME_EMAIL="$acme_email" \
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
