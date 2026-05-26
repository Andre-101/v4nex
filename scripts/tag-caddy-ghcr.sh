#!/usr/bin/env bash
set -euo pipefail

CADDY_LOCAL_TAG="${CADDY_LOCAL_TAG:-v4nex-caddy-cloudflare:dev-check}"
GHCR_IMAGE="${GHCR_IMAGE:-ghcr.io/andre-101/v4nex-caddy-cloudflare}"
GHCR_TAG="${GHCR_TAG:-scenario-18-check}"
GHCR_FULL_IMAGE="${GHCR_IMAGE}:${GHCR_TAG}"

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

if ! docker image inspect "$CADDY_LOCAL_TAG" >/dev/null 2>&1; then
  echo "ERROR local image not found: $CADDY_LOCAL_TAG"
  echo "Run: bash scripts/build-caddy-custom-local.sh"
  exit 1
fi

echo "Tagging local Caddy image for GHCR"
echo "  local: $CADDY_LOCAL_TAG"
echo "  ghcr:  $GHCR_FULL_IMAGE"
echo "  push:  disabled"

docker tag "$CADDY_LOCAL_TAG" "$GHCR_FULL_IMAGE"

echo "GHCR tag created locally."
echo "No push was performed."
