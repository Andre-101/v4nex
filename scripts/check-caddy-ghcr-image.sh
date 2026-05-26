#!/usr/bin/env bash
set -euo pipefail

GHCR_IMAGE="${GHCR_IMAGE:-ghcr.io/andre-101/v4nex-caddy-cloudflare}"
GHCR_TAG="${GHCR_TAG:-scenario-18-check}"
GHCR_FULL_IMAGE="${GHCR_IMAGE}:${GHCR_TAG}"
REQUIRED_MODULE="dns.providers.cloudflare"

validate_tag() {
  local tag="$1"
  if [[ -z "$tag" || "$tag" == "latest" || "$tag" == "change-me" || "$tag" == "dev" || "$tag" == "test" || "$tag" =~ [[:space:]] ]]; then
    echo "ERROR GHCR_TAG must be fixed and must not be latest/change-me/dev/test or contain spaces."
    exit 1
  fi
}

validate_tag "$GHCR_TAG"

if [[ "$GHCR_IMAGE" != ghcr.io/* ]]; then
  echo "ERROR GHCR_IMAGE must start with ghcr.io/."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi

echo "Checking Caddy image from GHCR"
echo "  image: $GHCR_FULL_IMAGE"
echo "  Cloudflare API: not called"
echo "  ACME/TLS issuance: not executed"

docker pull "$GHCR_FULL_IMAGE"
docker run --rm "$GHCR_FULL_IMAGE" caddy version
modules="$(docker run --rm "$GHCR_FULL_IMAGE" caddy list-modules)"

if ! printf '%s\n' "$modules" | grep -Fxq "$REQUIRED_MODULE"; then
  echo "ERROR required module not found: $REQUIRED_MODULE"
  exit 1
fi

echo "OK required module found: $REQUIRED_MODULE"
echo "GHCR Caddy image validation passed."
