#!/usr/bin/env bash
set -euo pipefail

APP_IMAGE_TAG="${APP_IMAGE_TAG:-scenario-23-app-images}"
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

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi

echo "Checking app images from GHCR"
echo "  backend:  $BACKEND_GHCR_FULL_IMAGE"
echo "  frontend: $FRONTEND_GHCR_FULL_IMAGE"

docker pull "$BACKEND_GHCR_FULL_IMAGE"
docker pull "$FRONTEND_GHCR_FULL_IMAGE"

docker run --rm "$BACKEND_GHCR_FULL_IMAGE" python -c "import fastapi, sqlalchemy, alembic; print('backend dependencies ok')"
docker run --rm "$FRONTEND_GHCR_FULL_IMAGE" nginx -v

echo "GHCR app image checks passed."
echo "No deploy, compose up, TLS issuance, or Cloudflare API call was performed."
