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
  value="${line#*=}"
  printf '%s' "${value%$'\r'}"
}

status_ok() {
  echo "OK $1"
}

status_error() {
  echo "ERROR $1"
}

placeholder_allowed() {
  [[ "$ALLOW_PLACEHOLDERS" == "true" ]]
}

has_errors="false"
required_vars=(
  APP_ENV
  DOMAIN
  IMAGE_TAG
  POSTGRES_DB
  POSTGRES_USER
  POSTGRES_PASSWORD
  JWT_SECRET
  CLOUDFLARE_API_TOKEN
  CADDY_ACME_EMAIL
  CADDY_DOMAIN
  BACKEND_PORT
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

domain="$(get_env_value DOMAIN)"
if [[ -z "$domain" || "$domain" == "example.com" ]]; then
  status_error "DOMAIN must not be empty or example.com"
  has_errors="true"
elif [[ "$domain" != "v4nex.com" ]]; then
  status_error "DOMAIN must be v4nex.com for this infrastructure baseline"
  has_errors="true"
else
  status_ok "DOMAIN v4nex.com"
fi

caddy_domain="$(get_env_value CADDY_DOMAIN)"
if [[ -z "$caddy_domain" ]]; then
  status_error "CADDY_DOMAIN must not be empty"
  has_errors="true"
elif [[ "$caddy_domain" != "$domain" ]]; then
  status_error "CADDY_DOMAIN must match DOMAIN"
  has_errors="true"
else
  status_ok "CADDY_DOMAIN matches DOMAIN"
fi

image_tag="$(get_env_value IMAGE_TAG)"
if [[ -z "$image_tag" || "$image_tag" == "latest" || "$image_tag" == "change-me" ]]; then
  if placeholder_allowed && [[ "$image_tag" == "change-me" ]]; then
    status_ok "IMAGE_TAG placeholder allowed"
  else
    status_error "IMAGE_TAG must be pinned and must not be latest/change-me"
    has_errors="true"
  fi
else
  status_ok "IMAGE_TAG pinned"
fi

postgres_password="$(get_env_value POSTGRES_PASSWORD)"
if [[ "$postgres_password" == "change-me" ]]; then
  if placeholder_allowed; then
    status_ok "POSTGRES_PASSWORD placeholder allowed"
  else
    status_error "POSTGRES_PASSWORD must be replaced"
    has_errors="true"
  fi
else
  status_ok "POSTGRES_PASSWORD replaced"
fi

jwt_secret="$(get_env_value JWT_SECRET)"
if [[ "$jwt_secret" == "dev-only-change-me" || "$jwt_secret" == "change-me" ]]; then
  if placeholder_allowed && [[ "$jwt_secret" == "change-me" ]]; then
    status_ok "JWT_SECRET placeholder allowed"
  else
    status_error "JWT_SECRET must be replaced"
    has_errors="true"
  fi
else
  status_ok "JWT_SECRET replaced"
fi

cloudflare_token="$(get_env_value CLOUDFLARE_API_TOKEN)"
if [[ "$cloudflare_token" == "change-me" ]]; then
  if placeholder_allowed; then
    status_ok "CLOUDFLARE_API_TOKEN placeholder allowed"
  else
    status_error "CLOUDFLARE_API_TOKEN must be replaced"
    has_errors="true"
  fi
else
  status_ok "CLOUDFLARE_API_TOKEN replaced"
fi

caddy_acme_email="$(get_env_value CADDY_ACME_EMAIL)"
if [[ -z "$caddy_acme_email" || "$caddy_acme_email" == "admin@example.com" ]]; then
  if placeholder_allowed && [[ "$caddy_acme_email" == "admin@example.com" ]]; then
    status_ok "CADDY_ACME_EMAIL placeholder allowed"
  else
    status_error "CADDY_ACME_EMAIL must be replaced"
    has_errors="true"
  fi
else
  status_ok "CADDY_ACME_EMAIL replaced"
fi

backend_port="$(get_env_value BACKEND_PORT)"
if [[ -z "$backend_port" ]]; then
  status_error "BACKEND_PORT must not be empty"
  has_errors="true"
else
  status_ok "BACKEND_PORT present"
fi

if [[ "$has_errors" == "true" ]]; then
  echo "Production env check failed."
  exit 1
fi

echo "Production env check passed."
