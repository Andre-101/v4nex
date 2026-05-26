#!/usr/bin/env bash
set -euo pipefail

CADDY_LOCAL_TAG="${CADDY_LOCAL_TAG:-v4nex-caddy-cloudflare:dev-check}"
REQUIRED_MODULE="dns.providers.cloudflare"

if [[ "$CADDY_LOCAL_TAG" == *":latest" || "$CADDY_LOCAL_TAG" == "latest" || "$CADDY_LOCAL_TAG" == */latest ]]; then
  echo "ERROR CADDY_LOCAL_TAG must not use latest."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi

echo "Checking local Caddy custom image"
echo "  tag: $CADDY_LOCAL_TAG"
echo "  Cloudflare API: not called"
echo "  ACME/TLS issuance: not executed"

docker run --rm "$CADDY_LOCAL_TAG" caddy version
modules="$(docker run --rm "$CADDY_LOCAL_TAG" caddy list-modules)"

if ! printf '%s\n' "$modules" | grep -Fxq "$REQUIRED_MODULE"; then
  echo "ERROR required module not found: $REQUIRED_MODULE"
  exit 1
fi

echo "OK required module found: $REQUIRED_MODULE"
echo "Local Caddy custom image validation passed."
