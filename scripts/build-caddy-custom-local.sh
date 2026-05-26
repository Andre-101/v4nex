#!/usr/bin/env bash
set -euo pipefail

CADDY_LOCAL_TAG="${CADDY_LOCAL_TAG:-v4nex-caddy-cloudflare:dev-check}"
DOCKERFILE="infra/caddy/Dockerfile.prod.example"

if [[ "$CADDY_LOCAL_TAG" == *":latest" || "$CADDY_LOCAL_TAG" == "latest" || "$CADDY_LOCAL_TAG" == */latest ]]; then
  echo "ERROR CADDY_LOCAL_TAG must not use latest."
  exit 1
fi

if [[ ! -f "$DOCKERFILE" ]]; then
  echo "ERROR $DOCKERFILE was not found."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR docker command is required."
  exit 1
fi

echo "Building local Caddy custom image"
echo "  tag: $CADDY_LOCAL_TAG"
echo "  dockerfile: $DOCKERFILE"
echo "  push: disabled"

docker build -f "$DOCKERFILE" -t "$CADDY_LOCAL_TAG" .

echo "Local Caddy custom image built successfully."
echo "No push was performed."
