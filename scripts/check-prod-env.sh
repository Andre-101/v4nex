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

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR env_file missing"
  echo "  env_file: $ENV_FILE"
  exit 1
fi

get_env_value() {
  local name="$1"
  local line
  line="$(grep -E "^${name}=" "$ENV_FILE" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    printf ''
    return
  fi
  printf '%s' "${line#*=}"
}

status_ok() {
  echo "OK $1"
}

status_error() {
  echo "ERROR $1"
}

has_errors="false"
required_vars=(
  APP_ENV
  PUBLIC_DOMAIN
  DATABASE_URL
  POSTGRES_DB
  POSTGRES_USER
  POSTGRES_PASSWORD
  JWT_SECRET_KEY
  JWT_ALGORITHM
  ACCESS_TOKEN_EXPIRE_MINUTES
  CADDY_ADMIN_URL
  CADDY_ADMIN_TIMEOUT_SECONDS
  MAX_BRIDGES_PER_USER
  RATE_LIMIT_ENABLED
  RATE_LIMIT_WINDOW_SECONDS
  RATE_LIMIT_MAX_REQUESTS
  RATE_LIMIT_STRICT_MAX_REQUESTS
  ACME_EMAIL
  DNS_PROVIDER
  DNS_PROVIDER_API_TOKEN
)

for name in "${required_vars[@]}"; do
  value="$(get_env_value "$name")"
  if [[ -z "$value" ]]; then
    status_error "$name missing"
    has_errors="true"
  else
    status_ok "$name present"
  fi
done

app_env="$(get_env_value APP_ENV)"
if [[ "$app_env" != "production" ]]; then
  status_error "APP_ENV must be production"
  has_errors="true"
else
  status_ok "APP_ENV production"
fi

rate_limit_enabled="$(get_env_value RATE_LIMIT_ENABLED)"
if [[ "$rate_limit_enabled" != "true" ]]; then
  status_error "RATE_LIMIT_ENABLED must be true"
  has_errors="true"
else
  status_ok "RATE_LIMIT_ENABLED true"
fi

public_domain="$(get_env_value PUBLIC_DOMAIN)"
if [[ -z "$public_domain" || "$public_domain" == "example.com" ]]; then
  if [[ "$ALLOW_PLACEHOLDERS" == "true" && "$public_domain" == "example.com" ]]; then
    status_ok "PUBLIC_DOMAIN placeholder allowed"
  else
    status_error "PUBLIC_DOMAIN must not be empty or example.com"
    has_errors="true"
  fi
else
  status_ok "PUBLIC_DOMAIN non-placeholder"
fi

jwt_secret_key="$(get_env_value JWT_SECRET_KEY)"
if [[ "$jwt_secret_key" == "dev-only-change-me" || "$jwt_secret_key" == "change-me" ]]; then
  if [[ "$ALLOW_PLACEHOLDERS" == "true" && "$jwt_secret_key" == "change-me" ]]; then
    status_ok "JWT_SECRET_KEY placeholder allowed"
  else
    status_error "JWT_SECRET_KEY must be replaced"
    has_errors="true"
  fi
else
  status_ok "JWT_SECRET_KEY replaced"
fi

postgres_password="$(get_env_value POSTGRES_PASSWORD)"
if [[ "$postgres_password" == "change-me" ]]; then
  if [[ "$ALLOW_PLACEHOLDERS" == "true" ]]; then
    status_ok "POSTGRES_PASSWORD placeholder allowed"
  else
    status_error "POSTGRES_PASSWORD must be replaced"
    has_errors="true"
  fi
else
  status_ok "POSTGRES_PASSWORD replaced"
fi

dns_token="$(get_env_value DNS_PROVIDER_API_TOKEN)"
if [[ "$dns_token" == "change-me" ]]; then
  if [[ "$ALLOW_PLACEHOLDERS" == "true" ]]; then
    status_ok "DNS_PROVIDER_API_TOKEN placeholder allowed"
  else
    status_error "DNS_PROVIDER_API_TOKEN must be replaced"
    has_errors="true"
  fi
else
  status_ok "DNS_PROVIDER_API_TOKEN replaced"
fi

if [[ "$has_errors" == "true" ]]; then
  echo "Production env check failed."
  exit 1
fi

echo "Production env check passed."
