#!/usr/bin/env bash
set -euo pipefail

APP_IMAGE_TAG="${APP_IMAGE_TAG:-scenario-23-app-images}"
BACKEND_LOCAL_IMAGE="${BACKEND_LOCAL_IMAGE:-v4nex-backend:${APP_IMAGE_TAG}}"
FRONTEND_LOCAL_IMAGE="${FRONTEND_LOCAL_IMAGE:-v4nex-frontend:${APP_IMAGE_TAG}}"
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

if [[ "$BACKEND_GHCR_IMAGE" != ghcr.io/* || "$FRONTEND_GHCR_IMAGE" != ghcr.io/* ]]; then
  echo "ERROR GHCR image names must start with ghcr.io/."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi

for image in "$BACKEND_LOCAL_IMAGE" "$FRONTEND_LOCAL_IMAGE"; do
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "ERROR local image not found: $image"
    echo "Run: APP_IMAGE_TAG=$APP_IMAGE_TAG bash scripts/build-app-images-local.sh"
    exit 1
  fi
done

echo "Tagging app images for GHCR"
echo "  backend:  $BACKEND_GHCR_FULL_IMAGE"
echo "  frontend: $FRONTEND_GHCR_FULL_IMAGE"
echo "  push: disabled"

docker tag "$BACKEND_LOCAL_IMAGE" "$BACKEND_GHCR_FULL_IMAGE"
docker tag "$FRONTEND_LOCAL_IMAGE" "$FRONTEND_GHCR_FULL_IMAGE"

echo "GHCR tags created locally."
echo "No push was performed."
