#!/usr/bin/env bash
set -euo pipefail

CADDY_LOCAL_TAG="${CADDY_LOCAL_TAG:-v4nex-caddy-cloudflare:dev-check}"
REQUIRED_MODULE="dns.providers.cloudflare"
SECRET_HISTORY_PATTERN="CLOUDFLARE_API_TOKEN|JWT_SECRET|POSTGRES_PASSWORD|change-me|BEGIN PRIVATE KEY|ghp_|AKIA"

if [[ "$CADDY_LOCAL_TAG" == *":latest" || "$CADDY_LOCAL_TAG" == "latest" || "$CADDY_LOCAL_TAG" == */latest ]]; then
  echo "ERROR CADDY_LOCAL_TAG must not use latest."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi

if ! docker image inspect "$CADDY_LOCAL_TAG" >/dev/null 2>&1; then
  echo "ERROR local image not found: $CADDY_LOCAL_TAG"
  echo "Run: bash scripts/build-caddy-custom-local.sh"
  exit 1
fi

repo_tags="$(docker image inspect "$CADDY_LOCAL_TAG" --format '{{join .RepoTags "\n"}}')"
if printf '%s\n' "$repo_tags" | grep -Eq '(^|:)latest$'; then
  echo "ERROR image has a latest tag."
  exit 1
fi

size_bytes="$(docker image inspect "$CADDY_LOCAL_TAG" --format '{{.Size}}')"
size_mb="$(( (size_bytes + 1048575) / 1048576 ))"

echo "Checking Caddy image hardening"
echo "  tag: $CADDY_LOCAL_TAG"
echo "  approx_size_mb: $size_mb"

docker image inspect "$CADDY_LOCAL_TAG" >/dev/null
history="$(docker history --no-trunc "$CADDY_LOCAL_TAG")"
if printf '%s\n' "$history" | grep -Eiq "$SECRET_HISTORY_PATTERN"; then
  echo "ERROR docker history contains a blocked secret-like pattern."
  exit 1
fi
echo "OK docker history has no blocked secret-like patterns"

docker run --rm "$CADDY_LOCAL_TAG" caddy version
modules="$(docker run --rm "$CADDY_LOCAL_TAG" caddy list-modules)"
if ! printf '%s\n' "$modules" | grep -Fxq "$REQUIRED_MODULE"; then
  echo "ERROR required module not found: $REQUIRED_MODULE"
  exit 1
fi

echo "OK required module found: $REQUIRED_MODULE"
echo "Caddy image hardening check passed."
echo "No Cloudflare API call, TLS issuance, or service startup was performed."
