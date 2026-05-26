#!/usr/bin/env bash
set -euo pipefail

APP_IMAGE_TAG="${APP_IMAGE_TAG:-scenario-23-app-images}"
BACKEND_LOCAL_IMAGE="${BACKEND_LOCAL_IMAGE:-v4nex-backend:${APP_IMAGE_TAG}}"
FRONTEND_LOCAL_IMAGE="${FRONTEND_LOCAL_IMAGE:-v4nex-frontend:${APP_IMAGE_TAG}}"

validate_tag() {
  local tag="$1"
  if [[ -z "$tag" || "$tag" == "latest" || "$tag" == "change-me" || "$tag" == "dev" || "$tag" == "test" || "$tag" =~ [[:space:]] ]]; then
    echo "ERROR APP_IMAGE_TAG must be fixed and must not be latest/change-me/dev/test or contain spaces."
    exit 1
  fi
}

validate_tag "$APP_IMAGE_TAG"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi

echo "Building app images locally"
echo "  backend:  $BACKEND_LOCAL_IMAGE"
echo "  frontend: $FRONTEND_LOCAL_IMAGE"
echo "  push: disabled"

docker build -f apps/backend/Dockerfile.prod -t "$BACKEND_LOCAL_IMAGE" apps/backend
docker build -f apps/frontend/Dockerfile.prod -t "$FRONTEND_LOCAL_IMAGE" apps/frontend

echo "Local app images built successfully."
echo "No push was performed."
