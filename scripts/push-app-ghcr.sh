#!/usr/bin/env bash
set -euo pipefail

APP_IMAGE_TAG="${APP_IMAGE_TAG:-scenario-23-app-images}"
CONFIRM_PUSH="${CONFIRM_PUSH:-}"
BACKEND_GHCR_IMAGE="${BACKEND_GHCR_IMAGE:-ghcr.io/andre-101/v4nex-backend}"
FRONTEND_GHCR_IMAGE="${FRONTEND_GHCR_IMAGE:-ghcr.io/andre-101/v4nex-frontend}"
BACKEND_GHCR_FULL_IMAGE="${BACKEND_GHCR_IMAGE}:${APP_IMAGE_TAG}"
FRONTEND_GHCR_FULL_IMAGE="${FRONTEND_GHCR_IMAGE}:${APP_IMAGE_TAG}"

validate_tag() {
  local tag="$1"
  if [[ -z "$tag" || "$tag" == "latest" || "$tag" == "change-me" || "$tag" == "dev" || "$tag" == "test" || "$tag" =~ [[:space:]] ]]; then
    echo "ERROR APP_IMAGE_TAG must be fixed and must not be latest/change-me/dev/test or contain spaces."
    exit 1
  fi
}

validate_tag "$APP_IMAGE_TAG"

if [[ "$CONFIRM_PUSH" != "I_UNDERSTAND_PUSH_GHCR" ]]; then
  echo "ERROR CONFIRM_PUSH must be I_UNDERSTAND_PUSH_GHCR."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi

for image in "$BACKEND_GHCR_FULL_IMAGE" "$FRONTEND_GHCR_FULL_IMAGE"; do
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "ERROR GHCR-tagged local image not found: $image"
    echo "Run: APP_IMAGE_TAG=$APP_IMAGE_TAG bash scripts/tag-app-ghcr.sh"
    exit 1
  fi
done

echo "Pushing app images to GHCR"
echo "  backend:  $BACKEND_GHCR_FULL_IMAGE"
echo "  frontend: $FRONTEND_GHCR_FULL_IMAGE"
echo "  docker login: manual prerequisite"

if ! docker push "$BACKEND_GHCR_FULL_IMAGE"; then
  echo "ERROR backend docker push failed."
  echo "If this is an auth error, run docker login ghcr.io manually and retry."
  exit 1
fi

if ! docker push "$FRONTEND_GHCR_FULL_IMAGE"; then
  echo "ERROR frontend docker push failed."
  echo "If this is an auth error, run docker login ghcr.io manually and retry."
  exit 1
fi

echo "GHCR app image push completed."
echo "No deploy, compose up, TLS issuance, or Cloudflare API call was performed."
