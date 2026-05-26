#!/usr/bin/env bash
set -euo pipefail

APP_IMAGE_TAG="${APP_IMAGE_TAG:-scenario-23-app-images}"
BACKEND_LOCAL_IMAGE="${BACKEND_LOCAL_IMAGE:-v4nex-backend:${APP_IMAGE_TAG}}"
FRONTEND_LOCAL_IMAGE="${FRONTEND_LOCAL_IMAGE:-v4nex-frontend:${APP_IMAGE_TAG}}"
BACKEND_CONTAINER="v4nex-backend-check-$$"
FRONTEND_CONTAINER="v4nex-frontend-check-$$"
BACKEND_PORT="${BACKEND_CHECK_PORT:-18080}"
FRONTEND_PORT="${FRONTEND_CHECK_PORT:-18081}"

cleanup() {
  docker rm -f "$BACKEND_CONTAINER" "$FRONTEND_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

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
if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR curl command is required for local HTTP checks."
  exit 1
fi

for image in "$BACKEND_LOCAL_IMAGE" "$FRONTEND_LOCAL_IMAGE"; do
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "ERROR local image not found: $image"
    echo "Run: APP_IMAGE_TAG=$APP_IMAGE_TAG bash scripts/build-app-images-local.sh"
    exit 1
  fi
  if docker image inspect "$image" --format '{{join .RepoTags "\n"}}' | grep -Eq '(^|:)latest$'; then
    echo "ERROR image has a latest tag: $image"
    exit 1
  fi
done

echo "Checking backend image"
docker run -d --name "$BACKEND_CONTAINER" \
  -e APP_ENV=development \
  -e DATABASE_URL=sqlite:////tmp/v4nex-check.db \
  -e JWT_SECRET_KEY=local-check-only \
  -p "127.0.0.1:${BACKEND_PORT}:8000" \
  "$BACKEND_LOCAL_IMAGE" >/dev/null

sleep 3
curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/tmp/v4nex-backend-health.txt
if ! grep -q '"status":"ok"' /tmp/v4nex-backend-health.txt; then
  echo "ERROR backend /health did not return expected payload."
  cat /tmp/v4nex-backend-health.txt
  exit 1
fi
echo "OK backend /health"

echo "Checking frontend image"
docker run -d --name "$FRONTEND_CONTAINER" \
  -p "127.0.0.1:${FRONTEND_PORT}:80" \
  "$FRONTEND_LOCAL_IMAGE" >/dev/null

sleep 2
curl -fsS "http://127.0.0.1:${FRONTEND_PORT}/" >/tmp/v4nex-frontend-root.html
if ! grep -qi '<div id="root">' /tmp/v4nex-frontend-root.html; then
  echo "ERROR frontend did not serve expected index.html."
  exit 1
fi
echo "OK frontend static root"

echo "Local app image checks passed."
echo "No deploy, compose up, TLS, or Cloudflare API call was performed."
