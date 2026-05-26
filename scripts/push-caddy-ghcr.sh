#!/usr/bin/env bash
set -euo pipefail

GHCR_IMAGE="${GHCR_IMAGE:-ghcr.io/andre-101/v4nex-caddy-cloudflare}"
GHCR_TAG="${GHCR_TAG:-scenario-18-check}"
CONFIRM_PUSH="${CONFIRM_PUSH:-}"
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

if [[ "$CONFIRM_PUSH" != "I_UNDERSTAND_PUSH_GHCR" ]]; then
  echo "ERROR CONFIRM_PUSH must be I_UNDERSTAND_PUSH_GHCR."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi

if ! docker image inspect "$GHCR_FULL_IMAGE" >/dev/null 2>&1; then
  echo "ERROR GHCR-tagged local image not found: $GHCR_FULL_IMAGE"
  echo "Run: GHCR_TAG=$GHCR_TAG bash scripts/tag-caddy-ghcr.sh"
  exit 1
fi

echo "Pushing Caddy image to GHCR"
echo "  image: $GHCR_FULL_IMAGE"
echo "  docker login: manual prerequisite"

if ! docker push "$GHCR_FULL_IMAGE"; then
  echo "ERROR docker push failed."
  echo "If this is an auth error, run docker login ghcr.io manually and retry."
  exit 1
fi

echo "GHCR push completed."
echo "No deploy, TLS issuance, or Cloudflare API call was performed."
